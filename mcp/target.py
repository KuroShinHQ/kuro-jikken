"""S1 target schema: a goal sentence becomes an application + constraints, or CLARIFY.

A *target* is not a question. "Etanol suda ne kadar cozunur" asks for a number;
"vazelin benzeri cilt koruyucu" names what the user wants to *achieve*, and
`screen()` (S3) turns that into a ranked candidate list.

This module only understands the sentence. It never computes a property, never
ranks and never fills a gap by guessing:

* an unknown application -> ``status: CLARIFY`` (the caller must ask);
* a composition without a basis (wt / at), a vague "~" bound without a tolerance,
  or a missing engine identifier -> CLARIFY;
* a performance or toxicity claim -> ``status: RED`` (no engine can support it);
* every constraint keeps the exact span it was read from, so a later audit can
  point at the sentence instead of trusting the parser.

``status`` means "was the goal understood", not "can it be answered": a target
can be READY and still be unanswerable, and S3 must check the calibration ledger
(R5) before ranking anything.
"""
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

SCHEMA = "kj-target/1"

STATUSES = {"READY", "CLARIFY", "RED"}

# application id -> (keywords, strong keywords, required payload identifiers)
APPLICATIONS = [
    (
        "alloy.liquidus",
        ["alasim", "liquidus", "solidus", "metal", "aluminyum", "celik", "titanyum", "bakir"],
        {"alasim", "liquidus"},
        ["tdb"],
    ),
    (
        "wax.range",
        ["mum", "wax", "parafin", "erime araligi", "erime noktasi"],
        {"mum", "wax", "parafin"},
        ["casrn"],
    ),
    (
        "formulation.petrolatum_like",
        ["vazelin", "petrolatum", "cilt koruyucu", "deri koruyucu", "merhem"],
        {"vazelin", "petrolatum"},
        [],
    ),
    (
        "solvent.miscibility",
        ["karisir", "karisim", "karisabilir", "cozucu", "solvent", "hsp", "uyum"],
        {"karisir", "hsp"},
        ["components"],
    ),
    (
        "solubility.aqueous",
        ["suda cozunur", "suda cozunurluk", "logs", "sudaki cozunurluk"],
        {"suda cozunur", "suda cozunurluk", "logs"},
        ["smiles"],
    ),
    (
        "molecule.identity",
        ["molekul agirligi", "molekuler agirlik", "logp", "log p", "mw"],
        {"molekul agirligi", "logp"},
        ["smiles"],
    ),
]

# claims no engine in this repository can support: a target that asks for one is
# refused before it becomes a candidate list. Kept as a subset of router.RED on
# purpose: "hedef" (target) is an ordinary word here and must not trigger biology.
RED_CLAIMS = {
    "toksik": "biology.toxicity",
    "kanserojen": "biology.toxicity",
    "admet": "biology.toxicity",
    "ld50": "biology.toxicity",
    "docking": "biology.binding",
    "baglanir": "biology.binding",
    "tewl": "product.performance",
    "okluziv": "product.performance",
    "okluzif": "product.performance",
    "emulsiyon": "product.performance",
    "deri hissi": "product.performance",
    "azeotrop": "vle.azeotrope",
}

# symbols the alloy/composition parser accepts; anything else stays a note, never
# a constraint. Lowercase because the sentence is normalised before matching.
ELEMENTS = {
    "al": "Al", "cu": "Cu", "fe": "Fe", "ni": "Ni", "mg": "Mg", "si": "Si",
    "zn": "Zn", "ti": "Ti", "cr": "Cr", "mn": "Mn", "sn": "Sn", "pb": "Pb",
    "ag": "Ag", "au": "Au", "pt": "Pt", "co": "Co", "mo": "Mo", "na": "Na",
    "ca": "Ca", "c": "C", "k": "K",
}

FOLD = str.maketrans("çğıöşü", "cgiosu")

NUM = r"(\d+(?:[.,]\d+)?)"
SYM = r"([a-z]{1,2})"

# "5 wt% cu" / "5% cu" / "%5 cu" (Turkish puts the sign first)
PCT_AFTER = re.compile(rf"{NUM}\s*(wt|at|mol|mole)?\s*%\s*{SYM}\b")
PCT_BEFORE = re.compile(rf"%\s*{NUM}\s*(wt|at|mol|mole)?\s*{SYM}\b")
BASE = re.compile(rf"\b{SYM}\s*[- ]\s*{NUM}\s*(wt|at|mol|mole)?\s*%")

TEMP = re.compile(rf"{NUM}\s*(k|kelvin|c|celsius|c derece)\b")
CAS = re.compile(r"\b(\d{2,7}-\d{2}-\d)\b")

LESS = ("altinda", "alti", "azami", "en fazla", "max", "maksimum", "kucuk",
        "below", "under", "at most", "<=")
GREATER = ("ustunde", "uzeri", "asgari", "en az", "min", "minimum", "buyuk",
           "above", "over", "at least", ">=")
AROUND = ("civarinda", "dolayinda", "around", "about", "yaklasik", "~")

BASES = {"wt": "wt", "at": "at", "mol": "at", "mole": "at"}

TEMPERATURE_KEY = {
    "alloy.liquidus": "liquidus_k",
    "wax.range": "melting_k",
    "formulation.petrolatum_like": "melting_k",
}

EXAMPLES = (
    "Al-5 wt% Cu alasimi 900 K altinda erisin",
    "Mum karisimi (8002-74-2) 330 K altinda erisin",
    "Vazelin benzeri cilt koruyucu",
    "Etanol suda cozunur olsun",
    "Kanserojen olmayan bir yag yap",
)

DOES_NOT_SAY = (
    "whether any engine can answer the target; whether a candidate performs as "
    "claimed; toxicity, stability, skin feel or cost"
)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text).lower().translate(FOLD))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9%\.\- ]", " ", text).split())


def _number(raw: str) -> float:
    return float(raw.replace(",", "."))


def _claim(norm: str):
    for word, capability in RED_CLAIMS.items():
        if _norm(word) in norm:
            return word, capability
    return None


def _application(norm: str):
    hits = []
    for cid, words, strong, needs in APPLICATIONS:
        score = sum(3 if _norm(word) in strong else 1 for word in words if _norm(word) in norm)
        if score:
            hits.append((score, cid, needs))
    hits.sort(key=lambda hit: -hit[0])
    if not hits:
        return None, [], "no application matches"
    tie = [hit[1] for hit in hits if hit[0] == hits[0][0]]
    if len(tie) > 1:
        return None, tie, "two applications match"
    return hits[0][1], [], None


def _comparator(norm: str, start: int, end: int):
    window = norm[max(0, start - 24):min(len(norm), end + 24)]
    for token in LESS:
        if token in window:
            return "<=", token
    for token in GREATER:
        if token in window:
            return ">=", token
    for token in AROUND:
        if token in window:
            return "~", token
    return "=", ""


def _temperature(norm: str, application):
    out = []
    for match in TEMP.finditer(norm):
        raw, unit = match.group(1), match.group(2)
        value = _number(raw)
        converted = unit != "k" and unit != "kelvin"
        if converted:
            value += 273.15
        op, token = _comparator(norm, match.start(), match.end())
        constraint = {
            "key": TEMPERATURE_KEY.get(application, "temperature_k"),
            "op": op,
            "value": round(value, 2),
            "unit": "K",
            "span": match.group(0).strip(),
            "comparator": token or None,
        }
        if converted:
            constraint["converted_from"] = "C"
        out.append(constraint)
    return out


def _composition(norm: str):
    """Read "Al-5 wt% Cu" style compositions; unknown symbols become notes only."""
    out, unknown = [], []
    base = BASE.search(norm)
    base_symbol = ELEMENTS.get(base.group(1)) if base else None
    seen = set()
    for pattern in (PCT_AFTER, PCT_BEFORE):
        for match in pattern.finditer(norm):
            raw, unit, symbol = match.group(1), match.group(2), match.group(3)
            element = ELEMENTS.get(symbol)
            if element is None:
                if symbol not in unknown:
                    unknown.append(symbol)
                continue
            key = (element, _number(raw))
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "key": f"composition.{element}",
                "op": "=",
                "element": element,
                "value": _number(raw),
                "basis": BASES.get(unit or ""),
                "unit": "%",
                "span": match.group(0).strip(),
                "base": base_symbol,
            })
    return out, unknown


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p for p in str(value).replace(",", " ").split() if p]


def _payload_ids(payload: dict, text: str):
    payload = payload or {}
    ids = {}
    smiles = _as_list(payload.get("smiles") or payload.get("smiles_list") or payload.get("components"))
    casrn = _as_list(payload.get("casrn") or payload.get("cas") or payload.get("cas_list"))
    if not casrn:
        casrn = CAS.findall(text or "")
    if smiles:
        ids["smiles"] = smiles
    if casrn:
        ids["casrn"] = casrn
    if payload.get("tdb") or payload.get("database"):
        ids["tdb"] = str(payload.get("tdb") or payload.get("database"))
    if len(smiles) >= 2 or len(casrn) >= 2:
        ids["components"] = smiles or casrn
    return ids


def _needs(application):
    for cid, _words, _strong, needs in APPLICATIONS:
        if cid == application:
            return list(needs)
    return []


def _missing(application, ids, constraints):
    missing = [need for need in _needs(application) if need not in ids]
    for constraint in constraints:
        if constraint.get("unit") == "%" and not constraint.get("basis") and "basis" not in missing:
            missing.append("basis")
        if constraint.get("op") == "~" and "tolerance" not in missing:
            missing.append("tolerance")
    return missing


def validate(target: dict) -> None:
    """Schema check: raises rather than let a malformed target reach screen()."""
    if target.get("schema") != SCHEMA:
        raise ValueError("wrong schema")
    if target.get("status") not in STATUSES:
        raise ValueError("status must be READY, CLARIFY or RED")
    constraints = target.get("constraints")
    if not isinstance(constraints, list):
        raise ValueError("constraints must be a list")
    for constraint in constraints:
        if not {"key", "op", "value", "unit", "span"} <= set(constraint):
            raise ValueError(f"constraint misses a field: {constraint}")
        if isinstance(constraint["value"], bool) or not isinstance(constraint["value"], (int, float)):
            raise ValueError(f"constraint value must be a number: {constraint}")
        if constraint["op"] not in {"=", "<=", ">=", "~"}:
            raise ValueError(f"unknown op: {constraint['op']}")
    if target["status"] == "READY":
        if not target.get("application"):
            raise ValueError("READY needs an application")
        if target.get("missing"):
            raise ValueError("READY cannot have missing fields")
    if target["status"] == "CLARIFY" and not (target.get("missing") or target.get("candidates")):
        raise ValueError("CLARIFY needs missing fields or candidates")
    if target["status"] == "RED" and not target.get("reason"):
        raise ValueError("RED needs a reason")


def parse(text: str, payload=None) -> dict:
    """Read a goal sentence. Returns a target dict; never raises on user text."""
    payload = dict(payload or {})
    norm = _norm(text)
    target = {
        "schema": SCHEMA,
        "text": text,
        "normalised": norm,
        "status": "READY",
        "application": None,
        "constraints": [],
        "components": [],
        "missing": [],
        "candidates": [],
        "reason": None,
        "notes": [],
        "does_not_say": DOES_NOT_SAY,
    }

    claim = _claim(norm)
    if claim:
        word, capability = claim
        target.update(status="RED", reason=f"claim '{word}' has no engine ({capability})")
        validate(target)
        return target

    application, candidates, why = _application(norm)
    if application is None:
        target.update(status="CLARIFY", candidates=candidates,
                      reason=why, missing=["application"])
        validate(target)
        return target
    target["application"] = application

    temperatures = _temperature(norm, application)
    compositions, unknown = _composition(norm)
    constraints = temperatures + compositions
    target["constraints"] = constraints
    components = [c["base"] for c in compositions if c.get("base")]
    components += [c["element"] for c in compositions]
    target["components"] = list(dict.fromkeys(components))
    if unknown:
        target["notes"].append(f"unrecognised element token(s): {', '.join(unknown)}")

    ids = _payload_ids(payload, text)
    missing = _missing(application, ids, constraints)
    target["missing"] = missing
    if missing:
        target["status"] = "CLARIFY"
        target["reason"] = f"target needs {', '.join(missing)}"

    if application == "formulation.petrolatum_like":
        target["notes"].append(
            "reference is petrolatum (CAS 8009-03-8); its Hansen values are "
            "REFERENCE_ONLY in the calibration ledger, so S3 may list but not rank on Ra"
        )
    if any(c.get("op") == "~" for c in constraints):
        target["notes"].append(
            "a '~' bound has no tolerance: it stays a preference and cannot be a hard screen"
        )
    validate(target)
    return target


def engine_payload(target: dict, ids=None):
    """The engine payload this target implies, or None when the bridge is unknown.

    Only pairs the engines already accept are bridged; anything else stays None
    so S3 cannot feed a made-up payload into a validated engine.
    """
    ids = dict(ids or {})
    application = target.get("application")
    if application == "alloy.liquidus":
        compositions = [c for c in target["constraints"] if c["unit"] == "%"]
        if not compositions:
            return None
        solute = compositions[0]
        if solute.get("base") != "Al" or solute["element"] != "Cu" or not solute.get("basis"):
            return None
        payload = {"elements": ["AL", "CU"], "cu_pct": solute["value"], "basis": solute["basis"]}
        if ids.get("tdb"):
            payload["tdb"] = ids["tdb"]
        return payload
    if application == "wax.range" and ids.get("casrn"):
        return {"casrn": ids["casrn"]}
    if application in ("solubility.aqueous", "molecule.identity") and ids.get("smiles"):
        return {"smiles": ids["smiles"][0]}
    if application == "solvent.miscibility" and len(ids.get("smiles") or []) >= 2:
        return {"smiles": ids["smiles"]}
    return None


if __name__ == "__main__":
    import json

    text = " ".join(sys.argv[1:]) or EXAMPLES[0]
    print(json.dumps(parse(text), indent=2))
