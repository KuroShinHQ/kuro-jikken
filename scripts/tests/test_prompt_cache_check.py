"""Unit tests for scripts/prompt_cache_check.py (no model, no network)."""

from __future__ import annotations

import json

import pytest
import requests

from bench.modes import MISSING, Item, ItemResult
from bench.props import PROPERTY_BY_KEY
from scripts.prompt_cache_check import (
    CacheFlagSession,
    compare,
    fingerprint,
    make_client,
)

FORMULA = PROPERTY_BY_KEY["formula"]


def _item(molecule_id: str = "MOL1") -> Item:
    return Item(molecule_id=molecule_id, smiles="CCO", prop=FORMULA)


def _result(answer=42, traces=None, texts=None) -> ItemResult:
    result = ItemResult(item=_item(), mode="B", answer=answer)
    result.trace = traces if traces is not None else [{"tool": "formula", "value": "C2H6O"}]
    result.responses = [{"text": text} for text in (texts or ['{"answer": 42}'])]
    return result


def test_session_forces_the_flag_and_keeps_the_rest(monkeypatch):
    seen = {}

    def fake_post(self, url, json=None, **kwargs):  # noqa: A002 - requests signature
        seen["payload"] = json
        return "sentinel"

    monkeypatch.setattr(requests.Session, "post", fake_post)
    session = CacheFlagSession(False)
    payload = {
        "temperature": 0.0,
        "cache_prompt": True,
        "seed": 20261026,
        "messages": [{"role": "user", "content": "x"}],
    }
    session.post("http://127.0.0.1:8099/v1/chat/completions", json=payload)

    assert seen["payload"]["cache_prompt"] is False
    assert {k: v for k, v in seen["payload"].items() if k != "cache_prompt"} == {
        k: v for k, v in payload.items() if k != "cache_prompt"
    }
    assert session.payloads[0]["cache_prompt"] is False


def test_session_refuses_payload_without_flag(monkeypatch):
    monkeypatch.setattr(requests.Session, "post", lambda *a, **k: "sentinel")
    with pytest.raises(RuntimeError):
        CacheFlagSession(True).post("http://127.0.0.1:8099/x", json={"model": "local"})


def test_make_client_uses_the_toggle_session():
    client = make_client("http://127.0.0.1:8099", True)
    assert isinstance(client._session, CacheFlagSession)
    assert client._session.cache_prompt is True
    assert client.base_url == "http://127.0.0.1:8099"


def test_fingerprint_is_stable_and_ignores_timing():
    first = _result()
    second = _result()
    second.responses[0]["http_ms"] = 1234.5  # timing must not matter
    second.seconds = 9.9
    assert fingerprint(first)["sha256"] == fingerprint(second)["sha256"]

    different = _result(answer=7)
    assert fingerprint(first)["sha256"] != fingerprint(different)["sha256"]


def test_fingerprint_marks_a_missing_answer():
    missing = _result(answer=MISSING)
    assert fingerprint(missing)["answer"] == "MISSING"


def test_compare_all_equal():
    off = [fingerprint(_result()), fingerprint(_result())]
    on = [fingerprint(_result()), fingerprint(_result())]
    comparison = compare(off, on)
    assert comparison["all_equal"] is True
    assert comparison["answer_equal"] == 2
    assert comparison["trace_equal"] == 2


def test_compare_reports_differing_fields():
    off = [fingerprint(_result(answer=42))]
    on = [
        fingerprint(
            _result(
                answer=42,
                traces=[{"tool": "molecular_weight", "value": 46.07}],
            )
        )
    ]
    comparison = compare(off, on)
    assert comparison["all_equal"] is False
    assert comparison["answer_equal"] == 1
    assert comparison["trace_equal"] == 0
    assert comparison["rows"][0]["differing"] == ["trace"]


def test_compare_rejects_item_order_drift():
    off = [fingerprint(_result()), fingerprint(_result())]
    on = [fingerprint(_result()), fingerprint(_result())]
    on[0]["item_id"] = "OTHER"
    with pytest.raises(RuntimeError):
        compare(off, on)


def test_fingerprint_trace_is_json_serialisable_and_sorted():
    print_ = fingerprint(_result(traces=[{"b": 1, "a": 2}]))
    assert json.loads(print_["trace_json"]) == [{"b": 1, "a": 2}]
    assert print_["trace_json"].startswith('[{"a": 2')
