"""L6 ledger: append-only record of every routed request, plus offline replay.

The ledger is the only place a number becomes permanent. One JSON line per
request in ``runs/router/YYYYMMDD.jsonl`` (or ``KJ_RUNS_DIR``); a line is never
rewritten, and ``replay`` re-derives the plan from the stored request so that a
changed router or gate shows up as a concrete diff instead of a silent drift.

Replay scope, stated plainly: plan and gate are recomputed; the number is only
recomputed when the caller passes a ``compute`` callable (the engines are wired
in a later phase). ``value_same`` is ``None`` in that case - never a fake True.
"""
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import router  # noqa: E402

REQUIRED = ("request", "capability", "plan", "gates", "answer", "commit")
RUNS_DIR = pathlib.Path(
    os.environ.get("KJ_RUNS_DIR", str(pathlib.Path(__file__).resolve().parents[1] / "runs" / "router"))
)


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(obj) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def project_plan(plan: dict) -> dict:
    """The stable part of a plan: what replay must reproduce exactly."""
    route = plan.get("route") or {}
    gate = plan.get("gate") or {}
    return {
        "capability": route.get("capability"),
        "engines": list(route.get("engines") or []),
        "gate": route.get("gate"),
        "gate_verdict": gate.get("verdict"),
        "gate_reason": gate.get("reason"),
    }


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(pathlib.Path(__file__).resolve().parents[1]),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def append(record: dict, path=None) -> dict:
    """Append one validated record; returns the stored entry (with id/digests)."""
    import answer as A

    missing = [k for k in REQUIRED if k not in record]
    if missing:
        raise ValueError(f"ledger record misses required fields: {', '.join(missing)}")
    A.validate(record["answer"])
    if record["answer"].get("capability") != record["capability"]:
        raise ValueError("answer capability does not match the record capability")
    if not isinstance(record["gates"], list):
        raise ValueError("gates must be a list (possibly empty for a refusal)")

    entry = {
        "id": f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}",
        "ts": record.get("ts") or _now(),
        "session": record.get("session") or os.environ.get("KJ_SESSION", "local"),
        "request": record["request"],
        "payload": record.get("payload"),
        "resolved_ids": record.get("resolved_ids") or [],
        "capability": record["capability"],
        "plan": record["plan"],
        "gates": record["gates"],
        "answer": record["answer"],
        "commit": record["commit"],
    }
    entry["plan_digest"] = digest(project_plan(record["plan"]))
    entry["answer_digest"] = digest(record["answer"])

    target = pathlib.Path(path) if path else _day_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    line = canonical(entry) + "\n"
    # append-only by construction: O_APPEND, never "w"
    with open(target, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())
    return entry


def _day_file(root=None) -> pathlib.Path:
    base = pathlib.Path(root) if root else RUNS_DIR
    return base / f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')}.jsonl"


def read(path) -> list:
    """Read every entry of one file; a malformed line is an error, not a skip."""
    entries = []
    with open(path, encoding="utf-8") as fh:
        for number, line in enumerate(fh, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                entries.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number} is not valid JSON: {exc}") from exc
    return entries


def files(root=None) -> list:
    base = pathlib.Path(root) if root else RUNS_DIR
    if not base.is_dir():
        return []
    return sorted(base.glob("*.jsonl"), reverse=True)


def find(entry_id: str, root=None) -> dict:
    """Look one entry up by id across all daily files (newest file first)."""
    for path in files(root):
        for entry in read(path):
            if entry.get("id") == entry_id:
                return entry
    raise KeyError(f"no ledger entry with id {entry_id}")


def replay(entry_id, *, compute=None, root=None) -> dict:
    """Recompute plan+gate for a stored request and compare with the ledger.

    ``compute`` is an optional callable ``entry -> answer dict``; when given, the
    number, unit and verdict are compared too. When omitted, ``value_same`` is
    None (the engines are not invoked by replay).
    """
    import answer as A

    entry = entry_id if isinstance(entry_id, dict) else find(entry_id, root)
    plan_now = router.plan(entry["request"], entry.get("payload"))
    now = project_plan(plan_now)
    old = project_plan(entry["plan"])
    diffs = {k: {"ledger": old.get(k), "now": now.get(k)} for k in set(old) | set(now) if old.get(k) != now.get(k)}
    plan_same = not diffs

    answer_intact = digest(entry["answer"]) == entry.get("answer_digest")

    value_same = None
    answer_diffs = {}
    if compute is not None:
        fresh = compute(entry)
        A.validate(fresh)
        for key in ("value", "unit", "verdict"):
            if fresh.get(key) != entry["answer"].get(key):
                answer_diffs[key] = {"ledger": entry["answer"].get(key), "now": fresh.get(key)}
        value_same = not answer_diffs

    return {
        "id": entry.get("id"),
        "request": entry["request"],
        "capability": entry["capability"],
        "plan_same": plan_same,
        "answer_intact": answer_intact,
        "value_same": value_same,
        "plan_diffs": diffs,
        "answer_diffs": answer_diffs,
        "ok": plan_same and answer_intact and value_same is not False,
    }


def record(request: str, payload, plan: dict, ans: dict, *, commit=None, session=None, path=None) -> dict:
    """Convenience: build a record from a plan and its answer, then append it."""
    gate = plan.get("gate")
    return append(
        {
            "session": session,
            "request": request,
            "payload": payload,
            "capability": (plan.get("route") or {}).get("capability"),
            "plan": plan,
            "gates": [gate] if gate else [],
            "answer": ans,
            "commit": commit or _git_commit(),
        },
        path=path,
    )
