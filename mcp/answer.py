"""L5 answer contract: exactly one shape for a number and for a refusal.

A number may only be built with (a) a gate record whose verdict allows it,
(b) a provenance block naming the engine and dataset, (c) the unit the router
allows for that capability. Anything else raises ``ValueError`` - the point is
that a bad answer cannot be formatted into existence.

The refusal sentences are fixed (docs/ENGINE_ROUTER_PLAN.md section 8): the
router never improvises its wording.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import router  # noqa: E402

# unit the router promises for each capability; nothing else is accepted
UNITS = {
    "solubility.aqueous": {"logS"},
    "mixture.gamma": {"gamma"},
    "mixture.wax": {"K"},
    "alloy.phase": {"K"},
    "molecule.identity": {"g/mol", "1"},
}

# non-SI tokens: a log concentration and a dimensionless ratio
NON_SI = {"logS": "log10(mol/L)", "gamma": "ratio"}

SENTENCES = {
    "no engine": "Bunu hesaplayan dogrulanmis bir motorumuz yok; sayi uydurmuyorum.",
    "no data": "Bu madde/veri seti elimizde yok; en yakin kapsam: {closest}",
    "out of domain": "Motor var ama bu molekul onun kapsami disinda (sebep: {reason}).",
    "missing parameters": "Grup etkilesim parametresi tabloda yok; hesap yapilmiyor.",
    "ambiguous name": "Iki farkli madde buldum: {a} / {b}. Hangisi?",
    "unit mismatch": "Birim belirsiz (wt% mi at% mi?). Hangisi?",
    "model != measurement": "Bu bir tahmin; olcum degil. Hata cubugu: {error}",
}

REQUIRED = (
    "value",
    "unit",
    "method",
    "error",
    "limits",
    "verdict",
    "provenance",
    "reproduce",
    "does_not_say",
)

_UREG = None


def _ureg():
    global _UREG
    if _UREG is None:
        from pint import UnitRegistry

        _UREG = UnitRegistry()
    return _UREG


def check_unit(unit: str, capability: str) -> str:
    """Return the canonical unit, or raise if the capability cannot use it."""
    if capability not in UNITS:
        raise ValueError(f"unknown capability: {capability}")
    if unit not in UNITS[capability]:
        raise ValueError(
            f"unit {unit!r} is not allowed for {capability} "
            f"(allowed: {', '.join(sorted(UNITS[capability]))})"
        )
    if unit in NON_SI:
        return NON_SI[unit]
    return str(_ureg().Unit(unit))


def _gate_allows(gate) -> bool:
    return isinstance(gate, dict) and gate.get("verdict") in {"PASS", "YELLOW"}


def build(
    *,
    capability: str,
    value,
    unit: str,
    method: str,
    verdict: str,
    provenance: dict,
    reproduce: str,
    does_not_say: str,
    error=None,
    limits=None,
    gate=None,
) -> dict:
    """Build a numeric answer; every guard below is a refusal, not a warning."""
    canonical = check_unit(unit, capability)
    if verdict not in {"GREEN", "YELLOW"}:
        raise ValueError("a number needs verdict GREEN or YELLOW; use refusal()")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("value must be a real number")
    if not math.isfinite(float(value)):
        raise ValueError("value must be finite")
    if not _gate_allows(gate):
        raise ValueError("a number needs a PASS or YELLOW gate record")
    if verdict == "GREEN" and gate["verdict"] != "PASS":
        raise ValueError("GREEN needs a PASS gate")
    if not isinstance(provenance, dict) or not provenance.get("engine") or not provenance.get("dataset"):
        raise ValueError("provenance needs at least engine and dataset")
    if error is not None:
        if not isinstance(error, dict) or not {"kind", "lower", "upper"} <= set(error):
            raise ValueError("error must be {kind, lower, upper}")
        if not (error["lower"] <= value <= error["upper"]):
            raise ValueError("value lies outside its own error bar")
    if not isinstance(limits, list) or not limits:
        raise ValueError("limits must be a non-empty list of what the answer does not cover")
    if not reproduce:
        raise ValueError("every number needs a reproduce command")
    if not does_not_say:
        raise ValueError("every number needs a does_not_say statement")

    answer = {
        "value": float(value),
        "unit": canonical,
        "method": method,
        "error": error,
        "limits": list(limits),
        "verdict": verdict,
        "provenance": dict(provenance),
        "reproduce": reproduce,
        "does_not_say": does_not_say,
        "gate": gate,
        "capability": capability,
        "note": SENTENCES["model != measurement"].format(
            error="none given" if error is None else f"[{error['lower']}, {error['upper']}]"
        ),
    }
    validate(answer)
    return answer


def refusal(
    kind: str,
    *,
    capability=None,
    reason=None,
    closest=None,
    a=None,
    b=None,
    error=None,
    gate=None,
) -> dict:
    """Same shape as an answer, with value None and a fixed sentence."""
    if kind not in SENTENCES:
        raise ValueError(f"unknown refusal class: {kind}")
    sentence = SENTENCES[kind].format(
        capability=capability,
        reason=reason or "belirtilmedi",
        closest=closest or capability or "yok",
        a=a or "A",
        b=b or "B",
        error=error or "yok",
    )
    answer = {
        "value": None,
        "unit": None,
        "method": None,
        "error": None,
        "limits": [reason] if reason else [],
        "verdict": "RED",
        "reason": kind,
        "sentence": sentence,
        "provenance": {},
        "reproduce": None,
        "does_not_say": "anything beyond this refusal",
        "gate": gate,
        "capability": capability,
    }
    validate(answer)
    return answer


NO_DATA_HINTS = ("no hansen entry", "no melting data", "not found", "not declared", "no gate input")
NO_ENGINE_CAPS = {"mixture.wax"}


def from_plan(plan: dict) -> dict:
    """Turn a router plan into either nothing (it may proceed) or a refusal.

    Returns ``None`` when the plan is allowed to compute, otherwise a refusal
    that names what is missing. Route RED and CLARIFY never reach an engine.
    """
    route = plan.get("route") or {}
    capability = route.get("capability")
    if capability == "UNKNOWN" or route.get("verdict") == "RED" and not route.get("engines"):
        return refusal("no engine", capability=capability, gate=plan.get("gate"))
    if capability == "CLARIFY":
        tie = route.get("tie") or ["A", "B"]
        return refusal("ambiguous name", a=tie[0], b=tie[1], gate=plan.get("gate"))
    if capability in NO_ENGINE_CAPS:
        return refusal("no engine", capability=capability, gate=plan.get("gate"))
    gate = plan.get("gate")
    if gate is None and route.get("gate"):
        return refusal(
            "no data",
            capability=capability,
            reason="no identifiers were resolved for this request",
            gate=None,
        )
    if gate and gate.get("verdict") == "RED":
        reason = str(gate.get("reason", "")).lower()
        kind = "no data" if any(h in reason for h in NO_DATA_HINTS) else "out of domain"
        return refusal(kind, capability=capability, reason=gate.get("reason"), gate=gate)
    return None


def validate(answer: dict) -> None:
    """Schema check shared by answers and refusals; raises on any deviation."""
    missing = [k for k in REQUIRED if k not in answer]
    if missing:
        raise ValueError(f"answer misses required fields: {', '.join(missing)}")
    if answer["verdict"] not in {"GREEN", "YELLOW", "RED"}:
        raise ValueError("verdict must be GREEN, YELLOW or RED")
    if answer["verdict"] == "RED":
        if answer["value"] is not None:
            raise ValueError("RED must not carry a value")
        if not answer.get("sentence"):
            raise ValueError("RED needs a fixed sentence")
        return
    if answer["value"] is None:
        raise ValueError("GREEN/YELLOW needs a value")
    if not _gate_allows(answer.get("gate")):
        raise ValueError("GREEN/YELLOW needs a gate record")
    if not isinstance(answer["limits"], list) or not answer["limits"]:
        raise ValueError("limits must be a non-empty list")


def allowed_capabilities():
    """Capabilities that can carry a number (used by the contract tests)."""
    return {cid for cid, _w, engines, _g, _u in router.CAPS if engines}
