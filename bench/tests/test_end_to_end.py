from __future__ import annotations

import json

import pytest

from bench import run_pilot
from bench.logging_jsonl import JsonlLogger
from bench.mock_server import MockLlamaServer
from bench.props import PROPERTIES

LABEL_TO_KEY = {prop.label: prop.key for prop in PROPERTIES}
TOOL_FOR = {
    "formula": "formula",
    "molecular_weight": "molecular_weight",
    "heavy_atom_count": "heavy_atom_count",
    "ring_count": "ring_count",
    "hbd_lipinski": "hbd_lipinski",
    "hba_lipinski": "hba_lipinski",
    "rotatable_bonds": "rotatable_bonds",
}


def perfect_model(payload: dict) -> str:
    """A mock model that always calls the right tool and copies its value."""
    messages = payload["messages"]
    last = messages[-1]["content"]
    if last.startswith("TOOL RESULT "):
        data = json.loads(last[len("TOOL RESULT "):])
        return json.dumps({"answer": data["result"]["value"]})
    question = messages[1]["content"]
    fields = {}
    for line in question.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            fields[key.strip()] = value.strip()
    prop_key = LABEL_TO_KEY[fields["Property"]]
    return json.dumps({"tool": TOOL_FOR[prop_key], "smiles": fields["SMILES"]})


def test_end_to_end_all_seven_properties(tmp_path, monkeypatch):
    records = [
        {"seq": "0", "molecule_id": "BENZENE", "split": "pilot", "smiles": "c1ccccc1"}
    ]
    monkeypatch.setattr(run_pilot, "load_records", lambda split, limit=None: records)
    out = tmp_path / "e2e.jsonl"
    with MockLlamaServer(perfect_model) as server:
        summary = run_pilot.run(
            split="pilot",
            modes=["B"],
            limit=None,
            base_url=server.base_url,
            model_path=None,
            out=out,
            require_port_8099=False,
        )
    assert summary["by_mode"]["B"]["items"] == 7
    assert summary["by_mode"]["B"]["correct"] == 7
    assert summary["by_mode"]["B"]["error_rate"] == 0.0
    lines = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert lines[0]["event"] == "run_start"
    assert sum(1 for line in lines if line["event"] == "item") == 7
    assert sum(1 for line in lines if line["event"] == "scored") == 7
    item_lines = [line for line in lines if line["event"] == "item"]
    assert all("model_sha256" in line["runtime"] for line in item_lines)
    assert all(len(line["prompt_sha256"]) == 64 for line in item_lines)


def test_existing_run_file_is_never_overwritten(tmp_path, monkeypatch):
    records = [
        {"seq": "0", "molecule_id": "BENZENE", "split": "pilot", "smiles": "c1ccccc1"}
    ]
    monkeypatch.setattr(run_pilot, "load_records", lambda split, limit=None: records)
    out = tmp_path / "once.jsonl"
    with MockLlamaServer(perfect_model) as server:
        run_pilot.run(
            split="pilot",
            modes=["B"],
            limit=1,
            base_url=server.base_url,
            model_path=None,
            out=out,
            require_port_8099=False,
        )
        with pytest.raises(SystemExit):
            run_pilot.run(
                split="pilot",
                modes=["B"],
                limit=1,
                base_url=server.base_url,
                model_path=None,
                out=out,
                require_port_8099=False,
            )


def test_jsonl_logger_appends_and_never_truncates(tmp_path):
    path = tmp_path / "log.jsonl"
    logger = JsonlLogger(path)
    logger.write({"event": "a"})
    logger.write({"event": "b"})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["event"] for line in lines] == ["a", "b"]
    assert all("logged_at" in json.loads(line) for line in lines)
