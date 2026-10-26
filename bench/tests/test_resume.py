from __future__ import annotations

import json

import pytest

from bench import resume_run
from bench.mock_server import MockLlamaServer

RECORDS = [
    {"seq": "0", "molecule_id": "BENZENE", "split": "pilot", "smiles": "c1ccccc1"},
    {"seq": "1", "molecule_id": "WATER", "split": "pilot", "smiles": "O"},
]


def patch_records(monkeypatch):
    def fake(split, limit=None):
        return RECORDS[:limit] if limit else list(RECORDS)

    monkeypatch.setattr(resume_run, "load_records", fake)


def test_resume_skips_completed_items(tmp_path, monkeypatch):
    patch_records(monkeypatch)
    out = tmp_path / "run.jsonl"
    with MockLlamaServer(['{"answer": 0}']) as server:
        first = resume_run.run("pilot", ["A"], 1, server.base_url, None,
                               out=out, require_port_8099=False)
        assert first["by_mode"]["A"]["items"] == 7
        second = resume_run.run("pilot", ["A"], None, server.base_url, None,
                               resume=out, require_port_8099=False)
    assert second["completed_before"] == 7
    assert second["by_mode"]["A"]["items"] == 7
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    items = [(r["mode"], r["item_id"]) for r in rows if r.get("event") == "item"]
    assert len(items) == 14
    assert len(set(items)) == 14


def test_server_failure_aborts_without_skipping(tmp_path, monkeypatch):
    patch_records(monkeypatch)
    calls = {"n": 0}

    def boom(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("server down")
        from bench.modes import run_item as real

        return real(*args, **kwargs)

    monkeypatch.setattr(resume_run, "run_item", boom)
    out = tmp_path / "abort.jsonl"
    with MockLlamaServer(['{"answer": 0}']) as server:
        with pytest.raises(SystemExit) as exc:
            resume_run.run("pilot", ["A"], 1, server.base_url, None,
                           out=out, require_port_8099=False)
    assert exc.value.code == 2
    assert calls["n"] == 2
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    aborted = [r for r in rows if r.get("event") == "run_aborted"]
    assert len(aborted) == 1
    assert aborted[0]["mode"] == "A"
    assert len([r for r in rows if r.get("event") == "scored"]) == 1
