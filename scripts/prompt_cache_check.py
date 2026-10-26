"""Prompt-cache determinism check (Freeze 2, task 2 of 2026-10-26).

Runs the first five pilot molecules (pilot IDs 1-5, all seven properties, mode B)
twice: once with ``cache_prompt: false`` and once with ``cache_prompt: true``.
Everything else - seed, temperature, max tokens, template kwargs, item order,
prompt files - is identical. The two passes are then compared byte for byte on
the final answer and on the tool trace.

Accuracy is deliberately not computed or printed here: this check is about
determinism, not about whether the answers are right.

The cache flag is toggled by wrapping the requests session of the real
``bench.llama_client.LlamaClient``, so the payload the server sees is exactly
the frozen harness payload with one field changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

import requests

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:  # allow `python scripts/prompt_cache_check.py`
    sys.path.insert(0, str(REPO))

from bench.llama_client import LlamaClient  # noqa: E402
from bench.logging_jsonl import JsonlLogger  # noqa: E402
from bench.modes import MISSING, ItemResult, ModeConfig, run_item  # noqa: E402
from bench.run_pilot import build_items, load_records  # noqa: E402

RUNS = REPO / "runs"


class CacheFlagSession(requests.Session):
    """A requests session that forces one value of ``cache_prompt``."""

    def __init__(self, cache_prompt: bool) -> None:
        super().__init__()
        self.trust_env = False
        self.cache_prompt = bool(cache_prompt)
        self.payloads: list[dict] = []

    def post(self, url, *, json=None, **kwargs):  # noqa: A002 - requests signature
        payload = dict(json or {})
        if "cache_prompt" not in payload:
            raise RuntimeError("the harness payload has no cache_prompt field any more")
        payload["cache_prompt"] = self.cache_prompt
        self.payloads.append(payload)
        return super().post(url, json=payload, **kwargs)


def make_client(base_url: str, cache_prompt: bool) -> LlamaClient:
    """The real client with only the outbound cache flag changed."""
    client = LlamaClient(base_url)
    client._session = CacheFlagSession(cache_prompt)  # noqa: SLF001 - intentional
    return client


def fingerprint(result: ItemResult) -> dict:
    """Everything that must be byte-identical, as stable strings."""
    answer = (
        "MISSING"
        if result.answer is MISSING
        else json.dumps(result.answer_value, sort_keys=True, ensure_ascii=False)
    )
    trace = json.dumps(result.trace, sort_keys=True, ensure_ascii=False)
    texts = [response.get("text", "") for response in result.responses]
    blob = json.dumps(
        {"answer": answer, "trace": trace, "texts": texts},
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return {
        "item_id": result.item.item_id,
        "answer": answer,
        "trace_json": trace,
        "texts": texts,
        "sha256": hashlib.sha256(blob).hexdigest(),
    }


def run_pass(
    items,
    *,
    base_url: str,
    cache_prompt: bool,
    run_id: str,
    out: pathlib.Path,
    runtime: dict,
) -> list[dict]:
    client = make_client(base_url, cache_prompt)
    logger = JsonlLogger(out)
    logger.write(
        {
            "run_id": run_id,
            "event": "cachecheck_start",
            "cache_prompt": cache_prompt,
            "mode": "B",
            "items": len(items),
            "params": ModeConfig(mode="B").params(),
            "runtime": runtime,
            "base_url": base_url,
        }
    )
    prints = []
    for item in items:
        result = run_item(client, ModeConfig(mode="B"), item, logger, run_id, runtime)
        prints.append(fingerprint(result))
    logger.write({"run_id": run_id, "event": "cachecheck_end", "items": len(prints)})
    return prints


def compare(off: list[dict], on: list[dict]) -> dict:
    rows = []
    for left, right in zip(off, on):
        if left["item_id"] != right["item_id"]:
            raise RuntimeError(f"item order drift: {left['item_id']} vs {right['item_id']}")
        answer_equal = left["answer"] == right["answer"]
        trace_equal = left["trace_json"] == right["trace_json"]
        texts_equal = left["texts"] == right["texts"]
        differing = [
            name
            for name, equal in (
                ("answer", answer_equal),
                ("trace", trace_equal),
                ("response_texts", texts_equal),
            )
            if not equal
        ]
        rows.append(
            {
                "item_id": left["item_id"],
                "answer_equal": answer_equal,
                "trace_equal": trace_equal,
                "response_texts_equal": texts_equal,
                "differing": differing,
                "sha256_off": left["sha256"],
                "sha256_on": right["sha256"],
            }
        )
    answers = sum(1 for row in rows if row["answer_equal"])
    traces = sum(1 for row in rows if row["trace_equal"])
    texts = sum(1 for row in rows if row["response_texts_equal"])
    return {
        "items": len(rows),
        "answer_equal": answers,
        "trace_equal": traces,
        "response_texts_equal": texts,
        "all_equal": answers == traces == texts == len(rows),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="prompt-cache determinism check")
    parser.add_argument("--base-url", default="http://127.0.0.1:8099")
    parser.add_argument("--molecules", type=int, default=5)
    parser.add_argument("--mode", default="B")
    args = parser.parse_args(argv)

    if args.mode != "B":
        parser.error("this check is defined for mode B only")

    records = load_records("pilot", args.molecules)
    items = build_items(records)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runtime_client = make_client(args.base_url, False)
    from bench.modes import runtime_meta

    runtime = runtime_meta(runtime_client)

    results = {}
    for label, flag in (("off", False), ("on", True)):
        run_id = f"{stamp}_cachecheck_{label}"
        out = RUNS / f"{run_id}.jsonl"
        if out.exists():
            raise SystemExit(f"refusing to touch an existing run file: {out}")
        results[label] = run_pass(
            items,
            base_url=args.base_url,
            cache_prompt=flag,
            run_id=run_id,
            out=out,
            runtime=runtime,
        )
        print(f"[{label}] {len(results[label])} items -> {out}", flush=True)

    comparison = compare(results["off"], results["on"])
    summary = {
        "check": "prompt_cache_determinism",
        "stamp": stamp,
        "molecules": [record["molecule_id"] for record in records],
        "mode": args.mode,
        "items": comparison["items"],
        "answer_equal": comparison["answer_equal"],
        "trace_equal": comparison["trace_equal"],
        "response_texts_equal": comparison["response_texts_equal"],
        "verdict": "EQUAL" if comparison["all_equal"] else "DIFFERENT",
        "rows": comparison["rows"],
    }
    summary_path = RUNS / f"{stamp}_cachecheck_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    print(f"summary: {summary_path}")
    return 0 if comparison["all_equal"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
