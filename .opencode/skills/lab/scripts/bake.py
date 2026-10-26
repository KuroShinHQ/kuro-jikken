#!/usr/bin/env python
"""Bake a grid of gated engine answers into one JSON file for a lab page.

Every point goes through ``mcp/pipeline.ask``, so every number carries a ledger
id: the page prints that id, and ``python tools/replay_router.py <id> --compute``
reproduces the number. The page never computes physics - it only interpolates
between these points and says so on screen.

Usage
-----
    python .opencode/skills/lab/scripts/bake.py \
        --request "Al-{cu} wt% Cu alasimi erir mi" \
        --payload '{"tdb":"mc_al_v2.032.pycalphad.tdb","elements":["AL","CU"],"cu_wt_pct":{cu}}' \
        --sweep cu=0..10:21 \
        --out data/labs/al_cu_liquidus.json

The placeholder is substituted into both the request and the payload, so one
sweep drives the sentence and the numbers together. ``--no-write`` skips the
ledger (dry run, tests): the output then carries ``ledger: null``.
"""
import argparse
import datetime
import json
import pathlib
import subprocess
import sys


def repo_root(start: pathlib.Path) -> pathlib.Path:
    for path in (start, *start.parents):
        if (path / "mcp" / "pipeline.py").exists():
            return path
    raise SystemExit("cannot find the kuro-jikken repo root (mcp/pipeline.py)")


HERE = pathlib.Path(__file__).resolve().parent
REPO = repo_root(HERE)
sys.path.insert(0, str(REPO / "mcp"))

import pipeline as P  # noqa: E402


def parse_sweep(text: str):
    """``cu=0..10:21`` -> ("cu", [0.0, 0.5, ..., 10.0])."""
    name, sep, rest = text.partition("=")
    if not sep or not name:
        raise SystemExit("--sweep must look like cu=0..10:21")
    rng, sep2, steps = rest.partition(":")
    start, sep3, end = rng.partition("..")
    if not sep3:
        raise SystemExit("--sweep range must look like 0..10")
    count = int(steps) if sep2 and steps else 11
    if count < 2:
        raise SystemExit("--sweep needs at least 2 points")
    low, high = float(start), float(end)
    if high <= low:
        raise SystemExit("--sweep end must be greater than start")
    step = (high - low) / (count - 1)
    return name, [round(low + index * step, 10) for index in range(count)]


def git_head() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=20,
        )
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def bake(request_template, payload_template, name, values, *, write=True, session="bake"):
    points = []
    engines = set()
    for value in values:
        token = repr(float(value))
        request = request_template.replace("{" + name + "}", token)
        payload = None
        if payload_template:
            payload = json.loads(payload_template.replace("{" + name + "}", token))
        if write:
            out = P.ask(request, payload, session=session)
            answer = out["answer"]
            ledger = out["ledger"]
        else:
            _plan, answer = P.compute(request, payload)
            ledger = None
        gate = (answer.get("gate") or {}).get("verdict")
        provenance = answer.get("provenance") or {}
        if provenance.get("engine"):
            engines.add(provenance["engine"])
        points.append(
            {
                "x": float(value),
                "request": request,
                "value": answer.get("value"),
                "unit": answer.get("unit"),
                "verdict": answer.get("verdict"),
                "gate": gate,
                "reason": answer.get("reason"),
                "sentence": answer.get("sentence"),
                "error": answer.get("error"),
                "provenance": provenance,
                "limits": answer.get("limits"),
                "ledger": ledger,
            }
        )
    numbers = [point for point in points if point["value"] is not None]
    return {
        "meta": {
            "created": datetime.datetime.now().isoformat(timespec="seconds"),
            "repo_head": git_head(),
            "request_template": request_template,
            "payload_template": payload_template,
            "sweep": {"name": name, "start": values[0], "end": values[-1], "steps": len(values)},
            "engines": sorted(engines),
            "points": len(points),
            "numbers": len(numbers),
            "refusals": len(points) - len(numbers),
            "ledger_written": bool(write),
            "interpolation": "linear between points; the page must label midpoints as interpolated",
        },
        "points": points,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, help="request template with {name}")
    parser.add_argument("--payload", default=None, help="JSON payload template with {name}")
    parser.add_argument(
        "--payload-file",
        default=None,
        help="read the payload template from a file (avoids shell quote mangling)",
    )
    parser.add_argument("--sweep", required=True, help="name=start..end:steps")
    parser.add_argument("--out", required=True, help="output JSON path")
    parser.add_argument("--session", default="bake")
    parser.add_argument("--no-write", action="store_true", help="do not write the ledger")
    args = parser.parse_args(argv)

    name, values = parse_sweep(args.sweep)
    payload_template = args.payload
    if args.payload_file:
        payload_template = pathlib.Path(args.payload_file).read_text(encoding="utf-8").strip()
    if payload_template and "{" + name + "}" not in payload_template:
        raise SystemExit(f"--payload carries no {{{name}}} placeholder: the sweep would not change it")
    if "{" + name + "}" not in args.request and not payload_template:
        raise SystemExit(f"neither --request nor --payload uses {{{name}}}")

    data = bake(
        args.request,
        payload_template,
        name,
        values,
        write=not args.no_write,
        session=args.session,
    )
    out = pathlib.Path(args.out)
    if not out.is_absolute():
        out = REPO / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    meta = data["meta"]
    print(
        f"{meta['points']} nokta ({meta['numbers']} sayi, {meta['refusals']} ret) -> {out}"
    )
    print(f"motor: {', '.join(meta['engines']) or 'yok'} · head {meta['repo_head']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
