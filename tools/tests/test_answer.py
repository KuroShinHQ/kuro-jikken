"""Tests for mcp/answer.py: a number cannot be built without a gate and provenance."""
import math
import pathlib
import sys

import pytest

pytest.importorskip("pint")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "mcp"))

import answer as A  # noqa: E402
import router as R  # noqa: E402

PASS = {"verdict": "PASS", "pass": True, "reason": "ok"}
YELLOW = {"verdict": "YELLOW", "pass": True, "reason": "in domain, wide bar"}
PROV = {"engine": "ESOL", "dataset": "esol.py"}


def _answer(**over):
    kw = dict(
        capability="solubility.aqueous",
        value=-0.1247,
        unit="logS",
        method="ESOL (Delaney) on RDKit descriptors",
        verdict="GREEN",
        provenance=PROV,
        reproduce="python tools/esol.py CCO",
        does_not_say="that the value is a measurement",
        limits=["neutral small molecules only"],
        error={"kind": "model", "lower": -1.3247, "upper": 1.0753},
        gate=PASS,
    )
    kw.update(over)
    return A.build(**kw)


def test_every_capability_has_units():
    caps = A.allowed_capabilities()
    assert caps == set(A.UNITS)
    for _cid, _w, _engines, _gate, unit in R.CAPS:
        if unit and unit != "mixed":
            assert any(unit in s or unit == s for s in A.UNITS.values())


def test_units_are_checked_with_pint_and_allowlist():
    assert A.check_unit("K", "alloy.phase")
    assert A.check_unit("g/mol", "molecule.identity")
    assert A.check_unit("logS", "solubility.aqueous") == "log10(mol/L)"
    with pytest.raises(ValueError):
        A.check_unit("furlong", "alloy.phase")
    with pytest.raises(ValueError):
        A.check_unit("K", "solubility.aqueous")  # right unit, wrong capability
    with pytest.raises(ValueError):
        A.check_unit("K", "biology.toxicity")  # no number there at all


def test_honest_answer_passes_and_keeps_shape():
    out = _answer()
    assert out["value"] == pytest.approx(-0.1247)
    assert out["verdict"] == "GREEN"
    for key in A.REQUIRED:
        assert key in out
    A.validate(out)


def test_number_without_gate_is_refused():
    with pytest.raises(ValueError):
        _answer(gate=None)
    with pytest.raises(ValueError):
        _answer(gate={"verdict": "RED", "reason": "out"})


def test_yellow_gate_cannot_claim_green():
    with pytest.raises(ValueError):
        _answer(gate=YELLOW)
    out = _answer(gate=YELLOW, verdict="YELLOW")
    assert out["verdict"] == "YELLOW"


def test_impossible_values_and_error_bars_are_refused():
    with pytest.raises(ValueError):
        _answer(value=math.nan)
    with pytest.raises(ValueError):
        _answer(value=float("inf"))
    with pytest.raises(ValueError):
        _answer(error={"kind": "model", "lower": 0.1, "upper": 0.2})  # value outside bar
    with pytest.raises(ValueError):
        _answer(limits=[])


def test_refusal_sentence_is_the_frozen_one():
    out = A.from_plan(R.plan("bu ilac toksik mi", None))
    assert out["verdict"] == "RED"
    assert out["value"] is None
    assert out["sentence"] == A.SENTENCES["no engine"]
    A.validate(out)


def test_clarify_becomes_one_question():
    out = A.from_plan({"route": {"capability": "CLARIFY", "verdict": "YELLOW",
                                 "tie": ["mixture.gamma", "mixture.wax"]}})
    assert out["reason"] == "ambiguous name"
    assert out["sentence"].endswith("Hangisi?")


def test_missing_data_is_not_out_of_domain():
    plan = {"route": {"capability": "mixture.gamma", "verdict": "YELLOW", "engines": ["unifac"]},
            "gate": {"verdict": "RED", "reason": "no Hansen entry for CAS 8009-03-8"}}
    out = A.from_plan(plan)
    assert out["reason"] == "no data"
    assert "8009-03-8" not in out["sentence"]  # sentence stays generic, reason is separate
    assert out["limits"] == ["no Hansen entry for CAS 8009-03-8"]


def test_gate_pass_but_no_engine_is_still_a_refusal():
    out = A.from_plan(R.plan("mum 40 C'de erir mi", {"casrn": ["112-92-5"]}))
    assert out["reason"] == "no engine"


def test_allowed_plan_is_not_refused():
    plan = R.plan("etanol suda ne kadar cozunur", "CCO")
    assert plan["gate"]["verdict"] == "PASS"
    assert A.from_plan(plan) is None


def test_golden_row_4_now_reaches_the_hansen_gate():
    """P3.5a closed the gap: petrolatum is refused by gate.hsp, not by UNIFAC.

    The request still needs the CAS from a resolver (P3.5b); once it has it, the
    refusal is the honest "no data" and never a number.
    """
    import gates as G

    plan = R.plan("vazelin bu kremle uyumlu mu",
                  {"casrn": ["8009-03-8"], "smiles": ["CCO", "O"]})
    assert plan["route"]["gate"] == "gate.unifac"
    assert plan["gate"]["verdict"] == "RED"
    assert "no Hansen entry" in plan["gate"]["reason"]
    out = A.from_plan(plan)
    assert out["reason"] == "no data"
    assert G.gate_hsp("8009-03-8")["verdict"] == "RED"
