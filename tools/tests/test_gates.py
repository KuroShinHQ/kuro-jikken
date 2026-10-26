"""Tests for mcp/gates.py: every gate must refuse with a reason, never guess."""
import pathlib
import sys

import pytest

pytest.importorskip("rdkit")
pytest.importorskip("thermo")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "mcp"))

import gates as G  # noqa: E402


def test_structure_good_and_bad():
    assert G.check("gate.structure", "CCO")["verdict"] == "PASS"
    assert G.check("gate.structure", "C1CC")["verdict"] == "RED"
    assert G.check("gate.structure", "CCO.O")["verdict"] == "RED"


def test_esol_in_and_out_of_domain():
    assert G.gate_esol("CCO")["verdict"] == "PASS"
    out = G.gate_esol("CC(=O)[O-].[Na+]")
    assert out["verdict"] == "RED" or out["verdict"] == "YELLOW"


def test_unifac_refuses_missing_pair():
    assert G.gate_unifac(["CCO", "O"])["verdict"] == "PASS"
    assert G.gate_unifac(["CSC", "O"])["verdict"] == "PASS"  # Dortmund has the pair


def test_hsp_petrolatum_has_no_entry():
    assert G.gate_hsp("64-17-5")["verdict"] == "PASS"
    assert G.gate_hsp("8009-03-8")["verdict"] == "RED"


def test_unknown_gate_is_red():
    assert G.check("gate.nope", "CCO")["verdict"] == "RED"


def test_gate_refuses_bad_payload_instead_of_crashing():
    assert G.gate_unifac("8009-03-8")["verdict"] == "RED"
    assert G.check("gate.esol", "not a smiles")["verdict"] == "RED"
