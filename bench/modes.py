"""Modes A, B and C (prereg section 4).

A: no tools.  B: tool calls from a JSON text protocol, at most 5 per question.
C: as B plus a deterministic check and exactly one retry on failure.

The protocol is deliberately plain JSON so a quantized local model is not asked
to satisfy a native tool-calling grammar:

    {"tool": "<name>", "smiles": "<SMILES>"}   -> harness replies TOOL RESULT {...}
    {"answer": <value>}                        -> final answer

Only the final JSON answer is scored; any "thinking"/reasoning text is logged
and ignored.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import time
from dataclasses import dataclass, field
from typing import Any

from bench.llama_client import LlamaClient
from bench.logging_jsonl import JsonlLogger
from bench.prompts import build_messages, question_text, system_prompt
from bench.props import Property
from bench.score import is_valid_format, score_answer
from bench.tools import UnknownTool, call_tool, canonical_smiles

MISSING = object()


@dataclass
class ModeConfig:
    mode: str
    max_tool_calls: int = 5
    max_tokens: int = 1024
    temperature: float = 0.0
    seed: int = 20261026
    max_nudges: int = 2

    def params(self) -> dict:
        return {
            "temperature": self.temperature,
            "seed": self.seed,
            "max_tokens": self.max_tokens,
            "max_tool_calls": self.max_tool_calls,
            "max_nudges": self.max_nudges,
        }


@dataclass
class Item:
    molecule_id: str
    smiles: str
    prop: Property
    item_id: str = ""
    canonical_smiles: str | None = None

    def __post_init__(self) -> None:
        if not self.item_id:
            self.item_id = f"{self.molecule_id}::{self.prop.key}"
        if self.canonical_smiles is None:
            self.canonical_smiles = canonical_smiles(self.smiles)

    def prompt_sha256(self) -> str:
        text = system_prompt("A") + "\x00" + question_text(self.prop, self.smiles)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_json_objects(text: str) -> list[dict]:
    """All top-level JSON objects in ``text``, in order (lenient scanning)."""
    decoder = json.JSONDecoder()
    objects: list[dict] = []
    index = 0
    while True:
        start = text.find("{", index)
        if start == -1:
            return objects
        try:
            value, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            index = start + 1
            continue
        if isinstance(value, dict):
            objects.append(value)
        index = end


def last_answer(text: str) -> Any:
    for obj in reversed(extract_json_objects(text)):
        if "answer" in obj:
            return obj["answer"]
    return MISSING


def last_tool_call(text: str) -> dict | None:
    for obj in reversed(extract_json_objects(text)):
        if "tool" in obj and "answer" not in obj:
            return obj
    return None


@dataclass
class ItemResult:
    item: Item
    mode: str
    answer: Any = MISSING
    format_ok: bool = False
    verified: bool = False
    verification_failed: bool = False
    responses: list[dict] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)
    nudges: int = 0
    retry_used: bool = False
    seconds: float = 0.0

    @property
    def answer_value(self) -> Any:
        return None if self.answer is MISSING else self.answer


def _tool_result_message(name: str, smiles: str, result: dict) -> str:
    payload = {"tool": name, "smiles": smiles, "result": result}
    return "TOOL RESULT " + json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _run_checks(
    item: Item, trace: list[dict], answer: Any
) -> list[str]:
    """Deterministic mode-C checks; messages never contain the correct value."""
    failures: list[str] = []
    matching = [call for call in trace if call.get("canonical_match")]
    if not matching:
        failures.append("no tool call was made with this molecule's SMILES")
    property_calls = [call for call in matching if call.get("tool") == item.prop.key]
    if matching and not property_calls:
        failures.append(f"no tool call was made for the asked property ({item.prop.key})")
    if answer is MISSING:
        failures.append("no valid JSON answer was produced")
    elif not is_valid_format(item.prop, answer):
        failures.append("the answer does not have the required JSON format")
    elif property_calls:
        tool_value = property_calls[-1].get("value")
        if not score_answer(item.prop, answer, tool_value)["correct"]:
            failures.append("the answer does not agree with the tool output you obtained")
    return failures


def run_item(
    client: LlamaClient,
    config: ModeConfig,
    item: Item,
    logger: JsonlLogger | None = None,
    run_id: str = "",
    runtime: dict | None = None,
) -> ItemResult:
    messages = build_messages(config.mode, item.prop, item.smiles)
    result = ItemResult(item=item, mode=config.mode)
    started = time.perf_counter()
    calls = 0
    retry_used = False
    pending_retry = False

    while True:
        if pending_retry:
            result.retry_used = True
            retry_used = True
            pending_retry = False

        outcome = _inner_loop(
            client,
            config,
            item,
            messages,
            result,
            logger,
            run_id,
            runtime,
            calls,
            maximum=config.max_tool_calls,
        )
        calls = outcome["calls"]

        if config.mode != "C" or result.answer is MISSING:
            break

        failures = _run_checks(item, result.trace, result.answer)
        if not failures:
            result.verified = True
            break
        if retry_used:
            result.verification_failed = True
            break

        messages.append({"role": "assistant", "content": outcome["last_text"]})
        messages.append(
            {
                "role": "user",
                "content": "VERIFICATION FAILED: " + "; ".join(failures)
                + ". Reply again with exactly one JSON object {\"answer\": <value>}."
                + f" Tool calls used: {calls}/{config.max_tool_calls}.",
            }
        )
        if logger is not None:
            logger.write(
                {
                    "run_id": run_id,
                    "event": "verification_retry",
                    "item_id": item.item_id,
                    "mode": config.mode,
                    "failures": failures,
                }
            )
        result.answer = MISSING
        pending_retry = True

    result.seconds = time.perf_counter() - started
    record = _record(result, config, runtime, run_id)
    if logger is not None:
        logger.write(record)
    return result


def _inner_loop(
    client: LlamaClient,
    config: ModeConfig,
    item: Item,
    messages: list[dict],
    result: ItemResult,
    logger: JsonlLogger | None,
    run_id: str,
    runtime: dict | None,
    calls: int,
    *,
    maximum: int,
) -> dict:
    last_text = ""
    while True:
        response = client.chat(
            messages,
            temperature=config.temperature,
            seed=config.seed,
            max_tokens=config.max_tokens,
        )
        last_text = response.text
        result.responses.append(
            {
                "text": response.text,
                "reasoning": response.reasoning,
                "usage": response.usage,
                "http_ms": round(response.http_ms, 3),
                "calls_so_far": calls,
            }
        )
        if logger is not None:
            logger.write(
                {
                    "run_id": run_id,
                    "event": "model_response",
                    "item_id": item.item_id,
                    "mode": config.mode,
                    "text": response.text,
                    "reasoning_len": len(response.reasoning),
                    "usage": response.usage,
                    "http_ms": round(response.http_ms, 3),
                    "runtime": runtime or {},
                }
            )

        answer = last_answer(response.text)
        if answer is not MISSING:
            result.answer = answer
            result.format_ok = is_valid_format(item.prop, answer)
            return {"calls": calls, "last_text": last_text}

        tool_call = last_tool_call(response.text)
        if tool_call is not None:
            if calls >= maximum:
                messages.append({"role": "assistant", "content": response.text})
                messages.append(
                    {
                        "role": "user",
                        "content": "TOOL BUDGET EXHAUSTED. Reply now with exactly one "
                        "JSON object {\"answer\": <value>}.",
                    }
                )
                result.nudges += 1
                if result.nudges > config.max_nudges:
                    return {"calls": calls, "last_text": last_text}
                continue

            calls += 1
            name = str(tool_call.get("tool", ""))
            smiles = str(tool_call.get("smiles", ""))
            try:
                tool_result = call_tool(name, smiles)
            except UnknownTool:
                tool_result = {
                    "ok": False,
                    "error": f"unknown tool {name!r}",
                    "allowed_tools": sorted(
                        ["parse_smiles", "formula", "molecular_weight", "heavy_atom_count",
                         "ring_count", "hbd_lipinski", "hbd_plain", "hba_lipinski",
                         "hba_plain", "rotatable_bonds", "esol_predict"]
                    ),
                }
            canonical = canonical_smiles(smiles) if smiles else None
            result.trace.append(
                {
                    "tool": name,
                    "smiles": smiles,
                    "canonical_smiles": canonical,
                    "canonical_match": bool(
                        canonical and item.canonical_smiles and canonical == item.canonical_smiles
                    ),
                    "value": tool_result.get("value"),
                    "ok": tool_result.get("ok", True),
                    "error": tool_result.get("error"),
                }
            )
            messages.append({"role": "assistant", "content": response.text})
            messages.append(
                {"role": "user", "content": _tool_result_message(name, smiles, tool_result)}
            )
            continue

        messages.append({"role": "assistant", "content": response.text})
        messages.append(
            {
                "role": "user",
                "content": "Your reply contained no JSON tool call and no JSON answer. "
                "Reply with exactly one JSON object: either "
                "{\"tool\": \"<name>\", \"smiles\": \"<SMILES>\"} or "
                "{\"answer\": <value>}.",
            }
        )
        result.nudges += 1
        if result.nudges > config.max_nudges:
            return {"calls": calls, "last_text": last_text}


def _record(
    result: ItemResult, config: ModeConfig, runtime: dict | None, run_id: str
) -> dict:
    return {
        "run_id": run_id,
        "event": "item",
        "item_id": result.item.item_id,
        "molecule_id": result.item.molecule_id,
        "smiles": result.item.smiles,
        "canonical_smiles": result.item.canonical_smiles,
        "property": result.item.prop.key,
        "mode": config.mode,
        "answer": result.answer_value,
        "format_ok": result.format_ok,
        "verified": result.verified,
        "verification_failed": result.verification_failed,
        "retry_used": result.retry_used,
        "nudges": result.nudges,
        "tool_calls": len(result.trace),
        "trace": result.trace,
        "prompt_sha256": result.item.prompt_sha256(),
        "params": config.params(),
        "runtime": runtime or {},
        "seconds": round(result.seconds, 3),
        "responses": result.responses,
    }


def summarise(results: list[ItemResult]) -> dict:
    total = len(results)
    with_answer = sum(1 for r in results if r.answer is not MISSING)
    return {
        "items": total,
        "answered": with_answer,
        "missing_answer": total - with_answer,
        "verification_failed": sum(1 for r in results if r.verification_failed),
        "retried": sum(1 for r in results if r.retry_used),
        "mean_tool_calls": (
            sum(len(r.trace) for r in results) / total if total else 0.0
        ),
        "mean_seconds": sum(r.seconds for r in results) / total if total else 0.0,
    }


def load_ids(path: pathlib.Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def runtime_meta(client: LlamaClient, model_path: str | None = None) -> dict:
    from bench.llama_client import runtime_fingerprint

    try:
        props = client.props()
    except Exception as exc:  # pragma: no cover - server down
        return {"error": str(exc)}
    fingerprint = runtime_fingerprint(props, model_path)
    fingerprint["base_url"] = client.base_url
    return fingerprint
