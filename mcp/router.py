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


def plan(request: str, payload=None) -> dict:
    """Plan-only: what would run, in what order, with which gate. No computation."""
    route = classify(request)
    steps = []
    gate_result = None
    if route["gate"] and payload is not None:
        from gates import check

        gate_result = check(route["gate"], payload)
    for engine in route["engines"]:
        steps.append({"engine": engine, "gate": route["gate"],
                      "gate_result": gate_result, "status": "planned"})
    return {"request": request, "route": route, "steps": steps,
            "gate": gate_result,
            "note": "plan only: no number is produced here"}


if __name__ == "__main__":
    import json
    import sys

    print(json.dumps(plan(" ".join(sys.argv[1:]) or "etanol suda ne kadar cozunur"), indent=2))



