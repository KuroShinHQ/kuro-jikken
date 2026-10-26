"""Deterministic router: sentence -> capability -> plan (no numbers here).

The table is the single source of truth; AGENTS.md is the human mirror.
Anything not matched is UNKNOWN and must be refused (RED).
"""
import unicodedata

CAPS = [
    ("solubility.aqueous", ["cozun", "solubility", "logS", "suda"], ["esol"], "gate.esol", "logS"),
    ("mixture.gamma", ["gamma", "aktivite", "activity", "uyum", "karisir", "karisim", "ayril"], ["unifac", "cosmo", "hsp"], "gate.unifac", "gamma"),
    ("mixture.wax", ["wax", "mum", "erime araligi"], ["wax"], "gate.wax", "K"),
    ("alloy.phase", ["alasim", "erir", "liquidus", "solidus", "tdb"], ["calphad"], "gate.calphad", "K"),
    ("molecule.identity", ["mw", "molekul agirligi", "formul", "halka", "logp"], ["rdkit"], "gate.structure", "mixed"),
]

RED = [
    ("biology.binding", ["baglanir", "docking", "hedef", "kd"]),
    ("biology.toxicity", ["toksik", "admet", "ld50", "kanserojen"]),
    ("product.performance", ["tewl", "okluziv", "emulsiyon", "deri hissi"]),
    ("vle.azeotrope", ["azeotrop", "buhar basinci", "kaynama"]),
]

FOLD = str.maketrans("çğıöşü", "cgiosu")

# words that name the capability itself beat generic context words ("suda", "erir")
STRONG = {"mum", "wax", "gamma", "azeotrop", "toksik", "baglanir", "ld50",
          "admet", "emulsiyon", "kap", "erime araligi"}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower().translate(FOLD))
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


def classify(request: str) -> dict:
    """Return {capability, engines, gate, unit, verdict} or UNKNOWN (RED)."""
    text = _norm(request)
    hits = []
    for cid, words, engines, gate, unit in CAPS:
        score = sum(3 if _norm(w) in STRONG else 1 for w in words if _norm(w) in text)
        if score:
            hits.append((score, cid, engines, gate, unit))
    for cid, words in RED:
        score = sum(3 if _norm(w) in STRONG else 1 for w in words if _norm(w) in text)
        if score:
            hits.append((score, cid, [], None, None))
    if not hits:
        return {"capability": "UNKNOWN", "engines": [], "gate": None,
                "unit": None, "verdict": "RED", "reason": "no capability matches"}
    hits.sort(key=lambda h: -h[0])
    if len(hits) > 1 and hits[0][0] == hits[1][0]:
        return {"capability": "CLARIFY", "engines": [], "gate": None, "unit": None,
                "verdict": "YELLOW", "tie": [hits[0][1], hits[1][1]]}
    score, cid, engines, gate, unit = hits[0]
    red = not engines
    return {"capability": cid, "engines": engines, "gate": gate, "unit": unit,
            "verdict": "RED" if red else "YELLOW", "matched": score}


# gates that run in addition to the primary gate when the payload carries the
# identifier they need; a mixture request names both molecules and products.
EXTRA_GATES = {"mixture.gamma": ("gate.hsp",)}


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p for p in str(value).replace(",", " ").split() if p]


def _first_cas(payload):
    if not isinstance(payload, dict):
        return []
    return _as_list(payload.get("casrn") or payload.get("cas") or payload.get("cas_list"))


def _slice(gate_id, payload):
    """Give a gate only the part of the payload it understands (never a guess)."""
    if not isinstance(payload, dict):
        return payload
    if gate_id in ("gate.structure", "gate.esol", "gate.unifac"):
        return payload.get("smiles") or payload.get("smiles_list")
    if gate_id == "gate.cosmo":
        return payload.get("inchikey") or payload.get("inchi_key")
    if gate_id == "gate.wax":
        return payload.get("casrn") or payload.get("cas")
    if gate_id == "gate.hsp":
        cas = _first_cas(payload)
        return cas[0] if cas else None
    if gate_id == "gate.calphad":
        return payload if ("tdb" in payload or "database" in payload) else None
    return payload


def gate_payloads(route, payload):
    """Every (gate, payload) pair this route must run; extras need their own ids."""
    if payload is None:
        return []
    pairs = []
    if route.get("gate"):
        pairs.append((route["gate"], _slice(route["gate"], payload)))
    for extra in EXTRA_GATES.get(route.get("capability"), ()):
        if extra == "gate.hsp":
            for cas in _first_cas(payload):
                pairs.append((extra, cas))
    return [(gid, sliced) for gid, sliced in pairs if sliced is not None]


def aggregate_gates(results) -> dict:
    """One verdict from several gates: any RED wins, then YELLOW, then PASS."""
    if not results:
        return None
    rank = {"RED": 3, "YELLOW": 2, "PASS": 1}
    worst = max(rank.get(rec.get("verdict"), 3) for _gid, rec in results)
    verdict = {3: "RED", 2: "YELLOW", 1: "PASS"}[worst]
    reasons = [f"{gid}: {rec.get('reason')}" for gid, rec in results if rec.get("verdict") == verdict]
    return {
        "verdict": verdict,
        "pass": verdict != "RED",
        "reason": "; ".join(reasons),
        "results": [{"gate": gid, "verdict": rec.get("verdict"), "reason": rec.get("reason")}
                    for gid, rec in results],
    }


def plan(request: str, payload=None) -> dict:
    """Plan-only: what would run, in what order, with which gate. No computation."""
    route = classify(request)
    steps = []
    gate_result = None
    gate_results = []
    if route["gate"] and payload is not None:
        from gates import check

        gate_results = [(gid, check(gid, sliced)) for gid, sliced in gate_payloads(route, payload)]
        gate_result = aggregate_gates(gate_results)
        if not gate_results:
            gate_result = {
                "verdict": "RED", "pass": False, "results": [],
                "reason": f"no gate input for {route['gate']} (need smiles/casrn/tdb)",
            }
    for engine in route["engines"]:
        steps.append({"engine": engine, "gate": route["gate"],
                      "gate_result": gate_result, "status": "planned"})
    return {"request": request, "route": route, "steps": steps,
            "gate": gate_result,
            "gates": [{"gate": gid, **rec} for gid, rec in gate_results],
            "note": "plan only: no number is produced here"}


if __name__ == "__main__":
    import json
    import sys

    print(json.dumps(plan(" ".join(sys.argv[1:]) or "etanol suda ne kadar cozunur"), indent=2))



