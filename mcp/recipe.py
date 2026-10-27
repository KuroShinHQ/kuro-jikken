"""P1 procedure contract: a recipe is data with a claim boundary, not a claim.

The engine lanes answer with a number that a gate allowed. A procedure cannot
answer with a number at all: it is a sequence of actions a person performs at
home. The failure mode is different and worse - an LLM-written paragraph that
sounds medical. This module is the gate for that lane:

* every ingredient and step names a source id or the literal ``design``;
* a temperature used as a **limit** (a safety threshold) must cite a source;
  a temperature used as a **setpoint** may be a design choice;
* ``claim_boundary`` and ``does_not_say`` are mandatory and are printed as-is;
* a treatment/cure/prevent verb outside those two fields is refused, unless it
  is negated ("does not cure");
* a declared reaction equation must be atom-balanced;
* every cited source must actually be used (no decoration);
* a Turkish translation, when present, must have the same shape as the English.

Nothing in this module computes chemistry. It refuses documents that cannot be
checked. ``render_markdown`` only rearranges fields; it never adds a number.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata
import urllib.request
from datetime import date

SCHEMA = "kj-recipe/1"
KINDS = {"food", "household-chemistry"}
ROLES = {"setpoint", "limit"}
DESIGN = "design"

REQUIRED = (
    "schema",
    "id",
    "kind",
    "title",
    "claim_boundary",
    "ingredients",
    "steps",
    "safety",
    "does_not_say",
    "sources",
)

# A verb only becomes a medical claim when a health noun is in the same window:
# "treats a viral infection" is a claim, "repeated treatment removes silver" is not.
CLAIM_VERBS = (
    "cure", "cures", "cured", "curing",
    "treat", "treats", "treated", "treating", "treatment",
    "heal", "heals", "healed", "healing",
    "prevent", "prevents", "prevented", "prevention",
    "iyilestir", "tedavi", "onle", "onler",
)
# nouns that are a medical claim by themselves
CLAIM_NOUNS = (
    "antiviral", "antibiotic", "medicine", "medication", "drug", "dose", "dosage",
    "ilac", "antibiyotik", "recete",
)
HEALTH_WORDS = (
    "flu", "cold", "infection", "virus", "viral", "disease", "cancer", "pain", "wound",
    "burn", "illness", "sick", "health", "medical", "immun", "symptom", "fever", "cough",
    "grip", "soguk alginligi", "enfeksiyon", "virus", "hastalik", "kanser", "agri", "yara",
    "yanik", "saglik", "ates", "oksuruk", "bagisiklik", "belirti",
)

# a negation inside this window before a claim word keeps the sentence honest
NEGATIONS = (
    "not ", "does not ", "do not ", "no ", "never ", "without ",
    "degil", "yok", "etmez", "yerine gecmez", "yerine gecmiyor",
)

ELEMENTS = frozenset(
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn "
    "Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce "
    "Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn "
    "Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl "
    "Mc Lv Ts Og".split()
)

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class RecipeError(ValueError):
    """A recipe that cannot be checked is refused, not repaired."""


# ----------------------------------------------------------------- text helpers


def _fold(text: str) -> str:
    """Lowercase and strip Turkish diacritics so claim matching is language-blind."""
    text = unicodedata.normalize("NFKD", str(text).lower().translate(str.maketrans("çğıöşü", "cgiosu")))
    return "".join(c for c in text if not unicodedata.combining(c))


def _claim_hits(text: str) -> list[str]:
    """Medical claims that are neither negated nor out of a health context.

    A verb needs a health noun within 70 characters ("treats the flu"), a noun
    such as "medicine" is a claim by itself. Either is allowed when negated
    inside the same sentence ("this drink is not a medicine").
    """
    flat = _fold(text)
    hits = []

    def negated(start: int) -> bool:
        prefix = flat[max(0, start - 48): start]
        return any(neg in prefix for neg in NEGATIONS)

    for word in CLAIM_VERBS:
        for match in re.finditer(rf"\b{re.escape(word)}\b", flat):
            window = flat[max(0, match.start() - 70): match.end() + 70]
            if not any(re.search(rf"\b{re.escape(h)}\b", window) for h in HEALTH_WORDS):
                continue
            if not negated(match.start()):
                hits.append(word)
    for word in CLAIM_NOUNS:
        for match in re.finditer(rf"\b{re.escape(word)}\b", flat):
            if not negated(match.start()):
                hits.append(word)
    return hits


# ----------------------------------------------------------------- formula parser


def _parse_term(term: str) -> tuple[float, dict[str, int]]:
    """Parse ``3 Al(OH)3`` into (3.0, {'Al': 1, 'O': 3, 'H': 3})."""
    term = term.strip()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(.*)$", term)
    factor = 1.0
    if m and m.group(2):
        factor = float(m.group(1))
        term = m.group(2).strip()
    term = re.sub(r"\((s|l|g|aq)\)$", "", term).strip()
    if not term:
        raise RecipeError("empty term in equation")

    counts: dict[str, int] = {}

    def group(s: str, mult: int) -> None:
        i, n = 0, len(s)
        while i < n:
            c = s[i]
            if c == "(":
                depth, j = 1, i + 1
                while j < n and depth:
                    depth += s[j] == "("
                    depth -= s[j] == ")"
                    j += 1
                if depth:
                    raise RecipeError(f"unbalanced parentheses in {term!r}")
                inner = s[i + 1: j - 1]
                k = j
                num = ""
                while k < n and s[k].isdigit():
                    num += s[k]
                    k += 1
                group(inner, mult * int(num or 1))
                i = k
                continue
            if c.isupper():
                symbol = c
                if i + 1 < n and s[i + 1].islower():
                    symbol += s[i + 1]
                i += len(symbol)
                num = ""
                while i < n and s[i].isdigit():
                    num += s[i]
                    i += 1
                if symbol not in ELEMENTS:
                    raise RecipeError(f"unknown element {symbol!r} in {term!r}")
                counts[symbol] = counts.get(symbol, 0) + mult * int(num or 1)
                continue
            raise RecipeError(f"unexpected character {c!r} in {term!r}")

    group(term, 1)
    return factor, counts


def equation_balance(equation: str) -> dict:
    """Return the balanced atom counts, or raise if the equation is not balanced.

    The parser accepts a coefficient, one level of parentheses and state tags:
    ``3 Ag2S(s) + 2 Al(s) + 6 H2O(l) -> 6 Ag(s) + 2 Al(OH)3(s) + 3 H2S(g)``.
    """
    if "->" in equation:
        left, right = equation.split("->", 1)
    elif "\u2192" in equation:
        left, right = equation.split("\u2192", 1)
    else:
        raise RecipeError("equation needs '->' between reactants and products")

    def side(part: str) -> dict[str, int]:
        total: dict[str, int] = {}
        for term in part.split("+"):
            factor, counts = _parse_term(term)
            for element, n in counts.items():
                total[element] = total.get(element, 0) + factor * n
        return total

    lhs, rhs = side(left), side(right)
    if lhs != rhs:
        diff = {
            e: (lhs.get(e, 0), rhs.get(e, 0))
            for e in sorted(set(lhs) | set(rhs))
            if lhs.get(e, 0) != rhs.get(e, 0)
        }
        raise RecipeError(f"equation is not balanced (element: left/right {diff})")
    return {"balanced": True, "elements": {e: int(n) if float(n).is_integer() else n for e, n in sorted(lhs.items())}}


# ------------------------------------------------------------------- validation


def load(path) -> dict:
    text = pathlib.Path(path).read_text(encoding="utf-8-sig")
    try:
        recipe = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RecipeError(f"{path}: not valid JSON ({exc})") from exc
    validate(recipe)
    return recipe


def _source_map(recipe: dict) -> dict[str, dict]:
    sources = recipe.get("sources")
    if not isinstance(sources, list) or not sources:
        raise RecipeError("sources must be a non-empty list")
    out: dict[str, dict] = {}
    for source in sources:
        if not isinstance(source, dict):
            raise RecipeError("every source must be an object")
        sid = source.get("id")
        if not isinstance(sid, str) or not SLUG.match(sid):
            raise RecipeError(f"source id {sid!r} is not a slug")
        if sid in out:
            raise RecipeError(f"duplicate source id {sid!r}")
        if not str(source.get("title") or "").strip():
            raise RecipeError(f"source {sid!r} has no title")
        url = str(source.get("url") or "")
        if not url.startswith(("http://", "https://")):
            raise RecipeError(f"source {sid!r} has no http(s) url")
        accessed = str(source.get("accessed") or "")
        if not ISO_DATE.match(accessed):
            raise RecipeError(f"source {sid!r} accessed must be YYYY-MM-DD")
        try:
            date.fromisoformat(accessed)
        except ValueError as exc:
            raise RecipeError(f"source {sid!r} accessed is not a date") from exc
        if not str(source.get("licence") or "").strip():
            raise RecipeError(f"source {sid!r} has no licence note")
        out[sid] = source
    return out


def _assert_source(value, known: dict, where: str, *, allow_design: bool = True) -> str:
    if not isinstance(value, str) or not value:
        raise RecipeError(f"{where}: source is missing")
    if value == DESIGN:
        if not allow_design:
            raise RecipeError(f"{where}: 'design' is not allowed here - cite a source")
        return value
    if value not in known:
        raise RecipeError(f"{where}: unknown source id {value!r}")
    return value


def _check_tr(recipe: dict) -> None:
    tr = recipe.get("tr")
    if tr is None:
        return
    if not isinstance(tr, dict):
        raise RecipeError("tr must be an object when present")
    for key in ("title", "summary", "claim_boundary"):
        if not isinstance(tr.get(key), str) or not tr[key].strip():
            raise RecipeError(f"tr.{key} is missing")
    for key in ("steps", "safety", "does_not_say"):
        if not isinstance(tr.get(key), list) or len(tr[key]) != len(recipe[key]):
            raise RecipeError(f"tr.{key} must have the same length as {key}")
        if not all(isinstance(x, str) and x.strip() for x in tr[key]):
            raise RecipeError(f"tr.{key} has an empty entry")


def validate(recipe: dict) -> dict:
    """Raise ``RecipeError`` on anything that cannot be checked; return a report."""
    if not isinstance(recipe, dict):
        raise RecipeError("recipe must be an object")
    missing = [key for key in REQUIRED if key not in recipe]
    if missing:
        raise RecipeError(f"missing required fields: {', '.join(missing)}")
    if recipe["schema"] != SCHEMA:
        raise RecipeError(f"schema must be {SCHEMA!r}")
    rid = recipe.get("id")
    if not isinstance(rid, str) or not SLUG.match(rid):
        raise RecipeError("id must be a slug")
    if recipe.get("kind") not in KINDS:
        raise RecipeError(f"kind must be one of {sorted(KINDS)}")
    for key in ("title", "claim_boundary"):
        if not str(recipe.get(key) or "").strip():
            raise RecipeError(f"{key} is empty")
    if len(str(recipe["claim_boundary"]).split()) < 6:
        raise RecipeError("claim_boundary must say what the procedure does not claim")

    known = _source_map(recipe)
    used: set[str] = set()

    ingredients = recipe.get("ingredients")
    if not isinstance(ingredients, list) or not ingredients:
        raise RecipeError("ingredients must be a non-empty list")
    for i, ing in enumerate(ingredients, 1):
        if not isinstance(ing, dict):
            raise RecipeError(f"ingredient {i} must be an object")
        if not str(ing.get("name") or "").strip():
            raise RecipeError(f"ingredient {i} has no name")
        amount = ing.get("amount")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
            raise RecipeError(f"ingredient {i} amount must be a positive number")
        if not str(ing.get("unit") or "").strip():
            raise RecipeError(f"ingredient {i} has no unit")
        src = _assert_source(ing.get("source"), known, f"ingredient {i}")
        if src != DESIGN:
            used.add(src)

    steps = recipe.get("steps")
    if not isinstance(steps, list) or not steps:
        raise RecipeError("steps must be a non-empty list")
    for i, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            raise RecipeError(f"step {i} must be an object")
        if step.get("n") != i:
            raise RecipeError(f"step {i} has n={step.get('n')!r}; steps are numbered 1..N in order")
        if not str(step.get("action") or "").strip():
            raise RecipeError(f"step {i} has no action")
        src = _assert_source(step.get("source"), known, f"step {i}")
        if src != DESIGN:
            used.add(src)
        temp = step.get("temperature_c")
        if temp is not None:
            if isinstance(temp, bool) or not isinstance(temp, (int, float)):
                raise RecipeError(f"step {i} temperature_c must be a number")
            role = step.get("temperature_role")
            if role not in ROLES:
                raise RecipeError(f"step {i} temperature_role must be setpoint or limit")
            if role == "limit" and src == DESIGN:
                raise RecipeError(f"step {i} uses a temperature limit without a source")
        minutes = step.get("minutes")
        if minutes is not None and (isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or minutes < 0):
            raise RecipeError(f"step {i} minutes must be a non-negative number")

    safety = recipe.get("safety")
    if not isinstance(safety, list) or not safety:
        raise RecipeError("safety must be a non-empty list")
    for i, item in enumerate(safety, 1):
        if isinstance(item, str):
            raise RecipeError(f"safety {i} must be an object with text and source")
        if not str(item.get("text") or "").strip():
            raise RecipeError(f"safety {i} has no text")
        src = _assert_source(item.get("source"), known, f"safety {i}")
        if src != DESIGN:
            used.add(src)
        flat = _fold(item["text"])
        needs_citation = any(
            token in flat
            for token in ("infant", "baby", "pregnan", "months", "carcinogen", "toxic", "sulfide", "sulphide")
        )
        if needs_citation and src == DESIGN:
            raise RecipeError(f"safety {i} makes a health claim without a source")

    dns = recipe.get("does_not_say")
    if not isinstance(dns, list) or not dns or not all(isinstance(x, str) and x.strip() for x in dns):
        raise RecipeError("does_not_say must be a non-empty list of sentences")

    equation = recipe.get("equation")
    if equation is not None:
        if not isinstance(equation, dict) or not str(equation.get("text") or "").strip():
            raise RecipeError("equation must be {text, source}")
        src = _assert_source(equation.get("source"), known, "equation", allow_design=False)
        used.add(src)
        equation_balance(equation["text"])

    unused = sorted(set(known) - used)
    if unused:
        raise RecipeError(f"sources are cited but never used: {', '.join(unused)}")

    _check_tr(recipe)

    for where, text in _claim_texts(recipe):
        hits = _claim_hits(text)
        if hits:
            raise RecipeError(
                f"{where}: medical claim {hits[0]!r} outside claim_boundary/does_not_say"
            )

    return {
        "schema": SCHEMA,
        "id": rid,
        "kind": recipe["kind"],
        "steps": len(steps),
        "ingredients": len(ingredients),
        "safety": len(safety),
        "sources": sorted(known),
        "equation": equation_balance(equation["text"]) if equation else None,
        "verdict": "PASS",
        "note": "procedure only: no engine number and no medical claim",
    }


def _claim_texts(recipe: dict):
    yield "title", recipe["title"]
    if recipe.get("summary"):
        yield "summary", recipe["summary"]
    for i, ing in enumerate(recipe["ingredients"], 1):
        yield f"ingredient {i}", ing["name"]
    for i, step in enumerate(recipe["steps"], 1):
        yield f"step {i}", step["action"]
    for i, item in enumerate(recipe["safety"], 1):
        yield f"safety {i}", item["text"]


# ----------------------------------------------------------------------- render


def render_markdown(recipe: dict, path=None) -> str:
    """Markdown for a chat answer; every number comes from the JSON."""
    validate(recipe)
    tr = recipe.get("tr") or {}
    title = tr.get("title") or recipe["title"]
    lines = [f"**{title}**", ""]
    if tr.get("summary") or recipe.get("summary"):
        lines += [tr.get("summary") or recipe["summary"], ""]
    lines += [f"> **Sinir / boundary:** {tr.get('claim_boundary') or recipe['claim_boundary']}", ""]
    lines += ["**Malzemeler / ingredients**", ""]
    for ing in recipe["ingredients"]:
        optional = " (optional)" if ing.get("optional") else ""
        lines.append(f"- {ing['amount']:g} {ing['unit']} {ing['name']}{optional} — `{ing['source']}`")
    lines += ["", "**Adimlar / steps**", ""]
    tr_steps = tr.get("steps") or []
    for i, step in enumerate(recipe["steps"]):
        text = tr_steps[i] if i < len(tr_steps) else step["action"]
        bits = []
        if step.get("temperature_c") is not None:
            bits.append(f"{step['temperature_c']:g} °C ({step['temperature_role']})")
        if step.get("minutes") is not None:
            bits.append(f"{step['minutes']:g} min")
        suffix = f" — {', '.join(bits)}" if bits else ""
        lines.append(f"{step['n']}. {text}{suffix} — `{step['source']}`")
    lines += ["", "**Guvenlik / safety**", ""]
    tr_safety = tr.get("safety") or []
    for i, item in enumerate(recipe["safety"]):
        lines.append(f"- {tr_safety[i] if i < len(tr_safety) else item['text']} — `{item['source']}`")
    if recipe.get("equation"):
        lines += ["", f"**Reaction:** `{recipe['equation']['text']}` (balanced; `{recipe['equation']['source']}`)"]
    lines += ["", "**Bu tarif NE soylemiyor / what this does not say**", ""]
    tr_dns = tr.get("does_not_say") or []
    for i, item in enumerate(recipe["does_not_say"]):
        lines.append(f"- {tr_dns[i] if i < len(tr_dns) else item}")
    lines += ["", "**Kaynaklar / sources**", ""]
    for source in recipe["sources"]:
        lines.append(f"- `{source['id']}` — {source['title']} — {source['url']} ({source['accessed']})")
    shown = str(path) if path else "data/recipes/%s.json" % recipe["id"]
    lines += ["", f"Reproduce: `python mcp/recipe.py {shown} --markdown`"]
    return "\n".join(lines)


# -------------------------------------------------------------------------- CLI


def check_urls(recipe: dict, timeout: float = 20.0) -> list[dict]:
    """Fetch every cited URL; report status without pretending a 403 is a dead page."""
    out = []
    for source in recipe["sources"]:
        req = urllib.request.Request(
            source["url"], headers={"User-Agent": "kuro-jikken/1 source-check"}
        )
        row = {"id": source["id"], "url": source["url"]}
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                response.read(2048)
                row.update(status=response.status, note="reachable")
        except urllib.error.HTTPError as exc:
            row.update(status=exc.code, note="http error (bot wall or paywall; open by hand)")
        except Exception as exc:  # noqa: BLE001 - the report is the point
            row.update(status=None, note=f"{type(exc).__name__}: {exc}")
        out.append(row)
    return out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    markdown = "--markdown" in argv
    urls = "--check-urls" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        print(__doc__)
        return 2
    failed = 0
    for path in paths:
        try:
            recipe = load(path)
        except RecipeError as exc:
            failed += 1
            print(json.dumps({"path": path, "verdict": "RED", "reason": str(exc)}, ensure_ascii=False))
            continue
        if markdown:
            print(render_markdown(recipe, path))
        else:
            report = validate(recipe)
            if urls:
                report["http"] = check_urls(recipe)
            report["path"] = str(path)
            print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
