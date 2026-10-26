"""Run the benchmark for one split (pilot or confirmatory).

Example (pilot, all three modes, local server on 8099):

    python -m bench.run_pilot --split pilot --modes A,B,C

Every item produces one append-only JSONL line under ``runs/``; a scored line
with the reference value follows it. Nothing in ``runs/`` is ever rewritten.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import random
import statistics
import time
from datetime import datetime, timezone

from bench.llama_client import LlamaClient
from bench.logging_jsonl import JsonlLogger
from bench.modes import (
    MISSING,
    Item,
    ModeConfig,
    run_item,
    runtime_meta,
    summarise,
)
from bench.prompts import prompt_hashes
from bench.props import PROPERTIES, PROPERTY_BY_KEY
from bench.score import classify_error, score_answer

REPO = pathlib.Path(__file__).resolve().parents[1]
DATA = REPO / "bench" / "data"
RUNS = REPO / "runs"


def load_records(split: str, limit: int | None = None) -> list[dict]:
    path = DATA / "ids_all.csv"
    with open(path, encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["split"] == split]
    rows.sort(key=lambda row: int(row["seq"]))
    if limit is not None:
        rows = rows[:limit]
    return rows


def build_items(records: list[dict], seed: int = 20261026) -> list[Item]:
    items = [
        Item(molecule_id=row["molecule_id"], smiles=row["smiles"], prop=prop)
        for row in records
        for prop in PROPERTIES
    ]
    random.Random(seed).shuffle(items)
    return items


def run(
    split: str,
    modes: list[str],
    limit: int | None,
    base_url: str,
    model_path: str | None,
    out: pathlib.Path | None,
    *,
    require_port_8099: bool = True,
) -> dict:
    records = load_records(split, limit)
    items = build_items(records)
    client = LlamaClient(base_url, require_port_8099=require_port_8099)
    runtime = runtime_meta(client, model_path)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"_{split}"
    out = out or (RUNS / f"{run_id}.jsonl")
    if out.exists():
        raise SystemExit(f"refusing to touch an existing run file: {out}")
    logger = JsonlLogger(out)
    started = time.time()
    logger.write(
        {
            "run_id": run_id,
            "event": "run_start",
            "split": split,
            "modes": modes,
            "molecules": len(records),
            "items_per_mode": len(items),
            "order_seed": 20261026,
            "prompt_hashes": prompt_hashes(),
            "runtime": runtime,
            "base_url": base_url,
        }
    )

    results = []
    for mode in modes:
        config = ModeConfig(mode=mode)
        for item in items:
            result = run_item(client, config, item, logger, run_id, runtime)
            reference = item.prop.reference(item.smiles)
            answer = None if result.answer is MISSING else result.answer
            scored = score_answer(item.prop, answer, reference)
            category = None
            if not scored["correct"]:
                category = classify_error(
                    mode=mode,
                    prop=item.prop,
                    answer=answer,
                    reference=reference,
                    trace=result.trace,
                )
            logger.write(
                {
                    "run_id": run_id,
                    "event": "scored",
                    "item_id": item.item_id,
                    "molecule_id": item.molecule_id,
                    "property": item.prop.key,
                    "mode": mode,
                    "answer": answer,
                    "reference": reference,
                    "correct": scored["correct"],
                    "detail": scored["detail"],
                    "category": category,
                }
            )
            results.append(
                {
                    "mode": mode,
                    "property": item.prop.key,
                    "correct": scored["correct"],
                    "category": category,
                    "seconds": result.seconds,
                    "tool_calls": len(result.trace),
                    "verification_failed": result.verification_failed,
                }
            )

    summary = build_summary(results, modes, run_id, split, runtime)
    summary_path = out.with_name(out.stem + "_summary.json")
    summary_path.write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    summary["wall_seconds"] = round(time.time() - started, 2)
    summary["jsonl"] = str(out)
    summary["summary_path"] = str(summary_path)
    print(json.dumps(summary, indent=2))
    return summary


def build_summary(
    results: list[dict], modes: list[str], run_id: str, split: str, runtime: dict
) -> dict:
    def aggregate(rows: list[dict]) -> dict:
        total = len(rows)
        if not total:
            return {"items": 0}
        correct = sum(1 for r in rows if r["correct"])
        categories: dict[str, int] = {}
        for row in rows:
            if row["category"]:
                categories[row["category"]] = categories.get(row["category"], 0) + 1
        return {
            "items": total,
            "correct": correct,
            "error_rate": round(1 - correct / total, 6),
            "categories": dict(sorted(categories.items())),
            "mean_seconds": round(statistics.fmean(r["seconds"] for r in rows), 3),
            "mean_tool_calls": round(statistics.fmean(r["tool_calls"] for r in rows), 3),
            "verification_failed": sum(1 for r in rows if r["verification_failed"]),
        }

    by_mode = {mode: aggregate([r for r in results if r["mode"] == mode]) for mode in modes}
    by_property = {
        prop.key: aggregate([r for r in results if r["property"] == prop.key])
        for prop in PROPERTIES
    }
    by_mode_property = {
        f"{mode}:{prop.key}": aggregate(
            [r for r in results if r["mode"] == mode and r["property"] == prop.key]
        )
        for mode in modes
        for prop in PROPERTIES
    }
    return {
        "run_id": run_id,
        "split": split,
        "runtime": runtime,
        "by_mode": by_mode,
        "by_property": by_property,
        "by_mode_property": by_mode_property,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run the A/B/C benchmark")
    parser.add_argument("--split", choices=["pilot", "confirmatory"], default="pilot")
    parser.add_argument("--modes", default="A,B,C")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--base-url", default="http://127.0.0.1:8099")
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    modes = [mode.strip().upper() for mode in args.modes.split(",") if mode.strip()]
    unknown = [mode for mode in modes if mode not in {"A", "B", "C"}]
    if unknown:
        parser.error(f"unknown modes: {unknown}")
    run(
        split=args.split,
        modes=modes,
        limit=args.limit,
        base_url=args.base_url,
        model_path=args.model_path,
        out=pathlib.Path(args.out) if args.out else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
