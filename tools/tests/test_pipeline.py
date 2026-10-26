"""P5a orchestration tests: plan -> gate -> engine -> build -> ledger, one call."""
import pathlib
import sys

import pytest

pytest.importorskip("pint")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "mcp"))

import answer as A  # noqa: E402
import ledger as L  # noqa: E402
import pipeline as P  # noqa: E402

ESOL = ("etanol suda ne kadar cozunur", {"smiles": "CCO"})
SALT = ("sofra tuzu suda ne kadar cozunur", {"smiles": "[Na+].[Cl-]"})


def test_one_call_produces_a_number_and_stores_it(tmp_path):
    path = tmp_path / "20261026.jsonl"
    out = P.ask(*ESOL, path=path)
    assert out["answer"]["verdict"] == "GREEN"
    assert out["answer"]["value"] == pytest.approx(-0.1247458, abs=1e-6)
    assert out["ledger"]

    entries = L.read(path)
    assert len(entries) == 1
    assert entries[0]["id"] == out["ledger"]
    assert entries[0]["answer"]["value"] == pytest.approx(out["answer"]["value"])
    assert entries[0]["gates"][0]["verdict"] == "PASS"


def test_refusal_is_stored_with_the_same_shape(tmp_path):
    path = tmp_path / "20261026.jsonl"
    out = P.ask(*SALT, path=path)
    assert out["answer"]["verdict"] == "RED" and out["answer"]["value"] is None
    entry = L.read(path)[0]
    assert entry["answer"]["reason"] == "out of domain"
    assert entry["answer"]["sentence"] == A.SENTENCES["out of domain"].format(
        reason=entry["answer"]["limits"][0]
    )
    A.validate(entry["answer"])


def test_wax_never_reaches_an_engine():
    plan, ans = P.compute("mum 40 C'de erir mi", {"casrn": ["8009-03-8"]})
    assert (plan["route"]["capability"]) == "mixture.wax"
    assert ans["reason"] == "no engine" and ans["value"] is None


def test_red_capability_never_reaches_an_engine():
    plan, ans = P.compute("bu ilac toksik mi")
    assert ans["reason"] == "no engine"
    assert plan["route"]["engines"] == []


def test_unknown_request_is_refused():
    plan, ans = P.compute("merhaba nasilsin")
    assert plan["route"]["capability"] == "UNKNOWN"
    assert ans["verdict"] == "RED" and ans["value"] is None


def test_no_write_leaves_no_file(tmp_path):
    path = tmp_path / "20261026.jsonl"
    out = P.ask(*ESOL, write=False, path=path)
    assert out["ledger"] is None
    assert not path.exists()


def test_compute_is_deterministic_and_never_touches_the_ledger(tmp_path):
    path = tmp_path / "20261026.jsonl"
    first = P.compute(*ESOL)
    second = P.compute(*ESOL)
    assert first[1]["value"] == second[1]["value"]
    assert not path.exists()


def test_plan_and_answer_agree_on_capability(tmp_path):
    out = P.ask(*ESOL, path=tmp_path / "20261026.jsonl")
    assert out["capability"] == out["answer"]["capability"] == "solubility.aqueous"
    assert out["plan"]["gate"]["verdict"] == "PASS"
