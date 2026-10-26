"""Tests for mcp/resolver.py: names resolve offline, or the answer is a refusal."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "mcp"))

import answer as A  # noqa: E402
import resolver as RS  # noqa: E402
import router as R  # noqa: E402


def test_cas_formatting_checks_the_digit():
    assert RS.format_cas("64175") == "64-17-5"
    assert RS.format_cas("7732185") == "7732-18-5"
    assert RS.format_cas("64-17-5") == "64-17-5"
    assert RS.format_cas("64176") is None  # wrong check digit
    assert RS.format_cas("1") is None


def test_turkish_name_resolves_to_cas_and_structure():
    out = RS.resolve("etanol")
    assert out["casrn"] == "64-17-5"
    assert out["smiles"] == "CCO"
    assert out["source"]


def test_acetone_and_glycerol_resolve():
    assert RS.resolve("aseton")["casrn"] == "67-64-1"
    assert RS.resolve("gliserin")["casrn"] == "56-81-5"


def test_mixture_resolves_without_a_structure():
    out = RS.resolve("vazelin")
    assert out["casrn"] == "8009-03-8"
    assert out["smiles"] is None
    assert out["source"] == "mixture table"
    assert out["notes"]  # says why there is no structure


def test_ambiguous_name_asks_instead_of_picking():
    with pytest.raises(RS.Ambiguous) as exc:
        RS.resolve("mum")
    assert len(exc.value.candidates) >= 2
    assert "petrolatum" in exc.value.candidates


def test_unknown_name_is_a_refusal():
    with pytest.raises(RS.NotFound):
        RS.resolve("unobtainium xyz")


def test_smiles_input_resolves_to_a_key():
    out = RS.resolve("CCO")
    assert out["smiles"] == "CCO"
    assert len(out["inchikey"]) == 27
    assert out["source"].startswith("SMILES")


def test_ids_is_the_gate_payload():
    assert RS.ids("vazelin") == {"casrn": "8009-03-8"}
    ethanol = RS.ids("etanol")
    assert ethanol["smiles"] == "CCO" and ethanol["casrn"] == "64-17-5"


def test_one_word_reaches_the_hansen_gate():
    plan = R.plan("vazelin bu kremle uyumlu mu", RS.ids("vazelin"))
    assert plan["gate"]["verdict"] == "RED"
    assert "no Hansen entry" in plan["gate"]["reason"]
    out = A.from_plan(plan)
    assert out["reason"] == "no data"


def test_one_word_reaches_the_esol_gate():
    plan = R.plan("etanol suda ne kadar cozunur", RS.ids("etanol"))
    assert plan["gate"]["verdict"] == "PASS"
    assert A.from_plan(plan) is None


def test_payload_without_the_right_identifier_is_red_not_silent():
    plan = R.plan("etanol suda ne kadar cozunur", {"casrn": "64-17-5"})
    assert plan["gate"]["verdict"] == "RED"
    assert "no gate input" in plan["gate"]["reason"]


def test_no_payload_at_all_is_refused_with_the_fixed_sentence():
    plan = R.plan("etanol suda ne kadar cozunur", None)
    out = A.from_plan(plan)
    assert out["reason"] == "no data"
    assert out["value"] is None
