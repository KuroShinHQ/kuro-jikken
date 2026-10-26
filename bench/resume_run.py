"""Resume-safe benchmark runner.

Appends to one JSONL file per run. Items already logged with an ``item`` event
are skipped; a server failure aborts the run (exit 2) and never skips to the
next item silently.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from datetime import datetime, timezone

from bench.llama_client import LlamaClient
from bench.logging_jsonl import JsonlLogger
from bench.modes import MISSING, ModeConfig, run_item, runtime_meta
from bench.run_pilot import RUNS, build_items, build_summary, load_records
from bench.score import classify_error, score_answer


def completed(path: pathlib.Path) -> tuple[set[tuple[str, str]], list[dict]]:
    rows = JsonlLogger(path).read_all()
    done = {
        (str(row.get("mode")), str(row.get("item_id")))
        for row in rows
        if row.get("event") == "item"
    }
    return done, rows


def run(split, modes, limit, base_url, model_path, out=None, resume=None,
        *, require_port_8099=True):
    items = build_items(load_records(split, limit))
    client = LlamaClient(base_url, require_port_8099=require_port_8099)
    runtime = runtime_meta(client, model_path)
    if resume is not None:
        path = pathlib.Path(resume)
        if not path.exists():
            raise SystemExit(f"resume file missing: {path}")
        done, rows = completed(path)
        run_id = next((r["run_id"] for r in rows if r.get("run_id")), path.stem)
    else:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"_{split}"
        path = pathlib.Path(out) if out else RUNS / f"{run_id}.jsonl"
        if path.exists():
            raise SystemExit(f"refusing to touch an existing run file: {path}")
        done = set()
    logger = JsonlLogger(path)
    logger.write({"run_id": run_id, "event": "run_resume" if resume else "run_start",
                  "split": split, "modes": modes, "completed_before": len(done),
                  "runtime": runtime})
    results = []
    mode = ""
    item_id = ""
    try:
        for mode in modes:
            config = ModeConfig(mode=mode)
            for item in items:
                item_id = item.item_id
                if (mode, item_id) in done:
                    continue
                result = run_item(client, config, item, logger, run_id, runtime)
                reference = item.prop.reference(item.smiles)
                answer = None if result.answer is MISSING else result.answer
                scored = score_answer(item.prop, answer, reference)
                category = None
                if not scored["correct"]:
                    category = classify_error(mode=mode, prop=item.prop, answer=answer,
                                              reference=reference, trace=result.trace)
                logger.write({"run_id": run_id, "event": "scored", "item_id": item_id,
                              "property": item.prop.key, "mode": mode, "answer": answer,
                              "reference": reference, "correct": scored["correct"],
                              "detail": scored["detail"], "category": category})
                results.append({"mode": mode, "property": item.prop.key,
                                "correct": scored["correct"], "category": category,
                                "seconds": result.seconds,
                                "tool_calls": len(result.trace),
                                "verification_failed": result.verification_failed})
    except Exception as exc:
        logger.write({"run_id": run_id, "event": "run_aborted", "mode": mode,
                      "item_id": item_id, "error": f"{type(exc).__name__}: {exc}"})
        raise SystemExit(2)

    summary = build_summary(results, modes, run_id, split, runtime)
    summary["jsonl"] = str(path)
    summary["resumed"] = resume is not None
    summary["completed_before"] = len(done)
    path.with_name(path.stem + "_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary["by_mode"], indent=2))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="pilot", choices=["pilot", "confirmatory"])
    ap.add_argument("--modes", default="A,B,C")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--base-url", default="http://127.0.0.1:8099")
    ap.add_argument("--model-path", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--resume", default=None)
    args = ap.parse_args(argv)
    modes = [m.strip().upper() for m in args.modes.split(",") if m.strip()]
    run(args.split, modes, args.limit, args.base_url, args.model_path,
        pathlib.Path(args.out) if args.out else None,
        pathlib.Path(args.resume) if args.resume else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
