"""Throughput probe: the same 10 pilot questions in modes A and B.

Used before the pilot to choose the faster llama.cpp platform (Windows exe vs
the WSL binary). Writes one append-only JSONL file per platform under ``runs/``.
No accuracy is interpreted here; the pilot itself is debugging only.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import time
from datetime import datetime, timezone

from bench.llama_client import LlamaClient
from bench.logging_jsonl import JsonlLogger
from bench.modes import MISSING, ModeConfig, run_item, runtime_meta
from bench.run_pilot import build_items, load_records

REPO = pathlib.Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="10-question throughput probe")
    parser.add_argument("--base-url", default="http://127.0.0.1:8099")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--questions", type=int, default=10)
    parser.add_argument("--modes", default="A,B")
    args = parser.parse_args(argv)

    items = build_items(load_records("pilot"))[: args.questions]
    modes = [m.strip().upper() for m in args.modes.split(",") if m.strip()]
    client = LlamaClient(args.base_url)
    runtime = runtime_meta(client)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"_speed_{args.tag}"
    out = RUNS / f"{run_id}.jsonl"
    if out.exists():
        raise SystemExit(f"refusing to touch an existing file: {out}")
    logger = JsonlLogger(out)
    logger.write(
        {
            "run_id": run_id,
            "event": "speed_start",
            "tag": args.tag,
            "questions": len(items),
            "modes": modes,
            "runtime": runtime,
        }
    )

    rows = []
    for mode in modes:
        config = ModeConfig(mode=mode)
        for item in items:
            started = time.perf_counter()
            result = run_item(client, config, item, logger, run_id, runtime)
            seconds = time.perf_counter() - started
            tokens = sum(
                int(response["usage"].get("completion_tokens") or 0)
                for response in result.responses
            )
            row = {
                "mode": mode,
                "item_id": item.item_id,
                "seconds": round(seconds, 3),
                "completion_tokens": tokens,
                "tokens_per_second": round(tokens / seconds, 3) if seconds > 0 else None,
                "requests": len(result.responses),
                "answered": result.answer is not MISSING,
            }
            logger.write({"run_id": run_id, "event": "speed_item", **row})
            rows.append(row)
            print(json.dumps(row))

    summary = {
        "tag": args.tag,
        "runtime": runtime,
        "questions": len(items),
        "rows": rows,
        "by_mode": {},
        "jsonl": str(out),
    }
    for mode in modes:
        subset = [row for row in rows if row["mode"] == mode]
        summary["by_mode"][mode] = {
            "n": len(subset),
            "seconds_total": round(sum(row["seconds"] for row in subset), 3),
            "seconds_median": round(statistics.median(row["seconds"] for row in subset), 3),
            "tokens_total": sum(row["completion_tokens"] for row in subset),
            "tokens_per_second": round(
                sum(row["completion_tokens"] for row in subset)
                / sum(row["seconds"] for row in subset),
                3,
            ),
            "answered": sum(1 for row in subset if row["answered"]),
        }
    summary_path = out.with_name(out.stem + "_summary.json")
    summary_path.write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({"by_mode": summary["by_mode"], "summary": str(summary_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
