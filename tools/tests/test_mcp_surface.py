"""P5d: the MCP surface (kj_ask with payload, kj_replay) matches the pipeline."""
import pathlib
import sys

import pytest

pytest.importorskip("pint")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "mcp"))

import ledger as L  # noqa: E402
import tools_server as T  # noqa: E402


def _entries(tmp_path):
    return [entry for path in tmp_path.glob("*.jsonl") for entry in L.read(path)]


def test_kj_ask_computes_and_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "RUNS_DIR", tmp_path)
    out = T.kj_ask("etanol suda ne kadar cozunur", {"smiles": "CCO"})
    assert out["answer"]["verdict"] == "GREEN"
    assert out["answer"]["value"] == pytest.approx(-0.1247458, abs=1e-6)
    assert out["ledger"]
    entries = _entries(tmp_path)
    assert len(entries) == 1 and entries[0]["id"] == out["ledger"]


def test_kj_ask_plan_only_still_computes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "RUNS_DIR", tmp_path)
    out = T.kj_ask("etanol suda ne kadar cozunur", {"smiles": "CCO"}, plan_only=True)
    assert out["note"].startswith("plan only")
    assert "value" not in out
    assert _entries(tmp_path) == []


def test_kj_ask_stores_a_refusal_as_well(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "RUNS_DIR", tmp_path)
    out = T.kj_ask("sofra tuzu suda ne kadar cozunur", {"smiles": "[Na+].[Cl-]"})
    assert out["answer"]["verdict"] == "RED" and out["answer"]["value"] is None
    assert out["ledger"]
    assert _entries(tmp_path)[0]["answer"]["reason"] == "out of domain"


def test_kj_replay_recomputes_the_number(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "RUNS_DIR", tmp_path)
    out = T.kj_ask("etanol suda ne kadar cozunur", {"smiles": "CCO"})
    result = T.kj_replay(out["ledger"])
    assert result["value_same"] is True and result["ok"] is True

    plan_only = T.kj_replay(out["ledger"], recompute=False)
    assert plan_only["value_same"] is None and plan_only["ok"] is True
