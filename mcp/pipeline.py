"""P5a orchestration: one call from a request to a stored answer.

The order is fixed and each step can refuse:

    plan (router) -> gate -> engine adapter -> answer.build -> ledger

``compute`` is the pure part (no disk write) and is exactly what P5b's replay
needs as its ``compute`` callable; ``ask`` adds the append-only ledger record.
A refusal is a normal result here: it is stored with the same shape as a
number, so "why not" is as durable as "what value".
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import answer as A  # noqa: E402
import engines as E  # noqa: E402
import ledger as L  # noqa: E402
import router as R  # noqa: E402


def compute(request: str, payload=None):
    """Return ``(plan, answer)``; never writes the ledger, never raises on data."""
    plan = R.plan(request, payload)
    refusal = A.from_plan(plan)
    if refusal is not None:
        return plan, refusal
    capability = (plan.get("route") or {}).get("capability")
    adapter = E.ADAPTERS.get(capability)
    if adapter is None:
        return plan, A.refusal("no engine", capability=capability, gate=plan.get("gate"))
    return plan, adapter(request, plan, payload)


def ask(
    request: str,
    payload=None,
    *,
    write: bool = True,
    session=None,
    path=None,
) -> dict:
    """Plan -> gate -> engine -> build -> ledger; returns the stored answer."""
    plan, ans = compute(request, payload)
    entry = None
    if write:
        entry = L.record(request, payload, plan, ans, session=session, path=path)
    return {
        "request": request,
        "payload": payload,
        "capability": (plan.get("route") or {}).get("capability"),
        "answer": ans,
        "plan": plan,
        "ledger": entry["id"] if entry else None,
    }
