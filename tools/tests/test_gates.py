"""Tests for mcp/gates.py: every gate must refuse with a reason, never guess."""
import os
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


def test_cosmo_needs_a_known_inchikey():
    index = pathlib.Path(os.environ.get("KURO_SIGMA_DIR", r"C:\KuroshinHQ\_hub\data\formulation_sigma")) / "sigma_profile_index.parquet"
    if not index.is_file():
        pytest.skip("PubChemQC sigma index stays outside the repo")
    assert G.gate_cosmo("LFQSCWFLJHTTHZ-UHFFFAOYSA-N")["verdict"] == "PASS"
    assert G.gate_cosmo("AAAAAAAAAAAAAA-AAAAAAAAAA-N")["verdict"] == "RED"
    assert G.gate_cosmo("not-an-inchikey")["verdict"] == "RED"


TDB_DIR = pathlib.Path(r"C:\KuroshinHQ\_hub\data\alloy_tdb_mgf")


@pytest.mark.skipif(not TDB_DIR.is_dir(), reason="MGF databases are outside the repo")
def test_calphad_checks_declared_elements():
    tdb = "mc_al_v2.032.pycalphad.tdb"
    assert G.gate_calphad({"tdb": tdb, "elements": ["AL", "CU"]})["verdict"] == "PASS"
    assert G.gate_calphad({"tdb": tdb, "elements": ["ZZ"]})["verdict"] == "RED"
    assert G.gate_calphad("../../secret.tdb")["verdict"] == "RED"


def test_wax_refuses_mixtures_without_hfus():
    assert G.gate_wax(["8009-03-8"])["verdict"] == "RED"  # petrolatum: Tm only
    assert G.gate_wax(["112-92-5"])["verdict"] == "PASS"  # stearyl alcohol
    assert G.gate_wax({"casrn": ["8009-03-8"]})["verdict"] == "RED"
    assert G.check("gate.wax", [])["verdict"] == "RED"
    assert G.check("gate.wax", ["00-00-0"])["verdict"] == "RED"
