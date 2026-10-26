"""Tests for mcp/ledger.py: append-only storage and honest replay."""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "mcp"))

import answer as A  # noqa: E402
import ledger as L  # noqa: E402
import router as R  # noqa: E402

PASS = {"verdict": "PASS", "pass": True, "reason": "ok"}
PROV = {"engine": "ESOL (Delaney 2004)", "dataset": "mcp/esol.py"}
VALUE = -0.1247458


def _answer(value=VALUE, verdict="GREEN", gate=PASS):
    return A.build(
        capability="solubility.aqueous",
        value=value,
        unit="logS",
        method="ESOL on RDKit descriptors",
        verdict=verdict,
        provenance=PROV,
        reproduce="python tools/esol.py CCO",
        does_not_say="that this is a measurement",
        limits=["neutral small molecules, water"],
        error={"kind": "model", "lower": value - 1.2, "upper": value + 1.2},
        gate=gate,
    )


def _plan(request="etanol suda ne kadar cozunur", payload="CCO"):
    return R.plan(request, payload)


def _append(tmp, ans=None, plan=None, request="etanol suda ne kadar cozunur", payload="CCO"):
    plan = plan or _plan(request, payload)
    ans = ans if ans is not None else _answer()
    return L.record(request, payload, plan, ans, commit="testc0de", path=tmp / "20261026.jsonl")


def test_append_is_additive_and_never_rewrites(tmp_path):
    first = _append(tmp_path)
    path = tmp_path / "20261026.jsonl"
    before = path.read_bytes()
    second = _append(tmp_path)
    after = path.read_bytes()

    assert after.startswith(before)  # append-only: the old bytes are untouched
    assert len(after) > len(before)
    assert path.read_text(encoding="utf-8").count("\n") == 2
    assert first["id"] != second["id"]
    assert len(L.read(path)) == 2


def test_record_keeps_plan_gates_answer_and_digests(tmp_path):
    entry = _append(tmp_path)
    for key in ("id", "ts", "session", "request", "capability", "plan", "gates", "answer", "commit"):
        assert key in entry
    assert entry["capability"] == "solubility.aqueous"
    assert entry["gates"][0]["verdict"] == "PASS"
    assert entry["plan_digest"] == L.digest(L.project_plan(entry["plan"]))
    assert entry["answer_digest"] == L.digest(entry["answer"])


def test_missing_field_is_refused(tmp_path):
    record = {
        "request": "x",
        "capability": "solubility.aqueous",
        "plan": _plan(),
        "gates": [],
        "answer": _answer(),
    }
    with pytest.raises(ValueError, match="commit"):
        L.append(record, path=tmp_path / "x.jsonl")


def test_ungated_answer_cannot_be_stored(tmp_path):
    bad = dict(_answer())
    bad["gate"] = None
    record = {
        "request": "etanol suda ne kadar cozunur",
        "capability": "solubility.aqueous",
        "plan": _plan(),
        "gates": [],
        "answer": bad,
        "commit": "test",
    }
    with pytest.raises(ValueError):
        L.append(record, path=tmp_path / "x.jsonl")


def test_replay_reproduces_plan_and_gate(tmp_path):
    entry = _append(tmp_path)
    out = L.replay(entry["id"], root=tmp_path)
    assert out["ok"] is True
    assert out["plan_same"] is True
    assert out["answer_intact"] is True
    assert out["value_same"] is None  # engines are not invoked by replay


def test_replay_detects_a_changed_route(tmp_path, monkeypatch):
    entry = _append(tmp_path)
    real_plan = R.plan

    def shifted(request, payload=None):
        plan = real_plan(request, payload)
        plan["route"]["capability"] = "mixture.gamma"  # pretend the router drifted
        return plan

    monkeypatch.setattr(L.router, "plan", shifted)
    out = L.replay(entry["id"], root=tmp_path)
    assert out["ok"] is False
    assert out["plan_same"] is False
    assert "capability" in out["plan_diffs"]


def test_replay_compares_the_number_only_when_asked(tmp_path):
    entry = _append(tmp_path)
    same = L.replay(entry["id"], compute=lambda e: _answer(), root=tmp_path)
    drift = L.replay(entry["id"], compute=lambda e: _answer(value=VALUE + 0.1), root=tmp_path)
    assert same["value_same"] is True and same["ok"] is True
    assert drift["value_same"] is False and drift["ok"] is False
    assert drift["answer_diffs"]["value"]["now"] == pytest.approx(VALUE + 0.1)


def test_red_entry_replays_without_a_value(tmp_path):
    request = "bu ilac toksik mi"
    plan = R.plan(request, None)
    refusal = A.from_plan(plan)
    entry = _append(tmp_path, ans=refusal, plan=plan, request=request, payload=None)
    out = L.replay(entry["id"], root=tmp_path)
    assert entry["answer"]["value"] is None
    assert out["ok"] is True


def test_tampered_answer_is_detected(tmp_path):
    entry = _append(tmp_path)
    entry["answer"]["value"] = 99.0  # digest no longer matches
    out = L.replay(entry, root=tmp_path)
    assert out["answer_intact"] is False
    assert out["ok"] is False


def test_malformed_line_is_an_error_not_a_skip(tmp_path):
    path = tmp_path / "broken.jsonl"
    path.write_text('{"id": "ok"}\nnot json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="broken.jsonl:2"):
        L.read(path)


def test_find_reports_missing_ids(tmp_path):
    _append(tmp_path)
    with pytest.raises(KeyError):
        L.find("nope", root=tmp_path)
