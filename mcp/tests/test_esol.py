"""Tests for the ESOL predictor (Task 9).

Expected arithmetic comes from the PUBLISHED equation:
logS = 0.16 - 0.63*clogP - 0.0062*MW + 0.066*RB - 0.74*AP
(Delaney 2004, J. Chem. Inf. Comput. Sci. 44:1000-1005), never from our output.
Descriptor checks compare against the RDKit reference functions themselves.
"""
import sys
from pathlib import Path
import pytest
from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from esol import esol_descriptors, esol_from_descriptors, esol_published, esol_refit  # noqa: E402

def test_arithmetic_from_paper():
    d = {"clogp": 1.0, "mw": 100.0, "rotb": 2, "ap": 0.5}
    expected = 0.16 - 0.63*1.0 - 0.0062*100.0 + 0.066*2 - 0.74*0.5  # -1.328
    assert esol_from_descriptors(d) == pytest.approx(-1.328, abs=1e-9)

def test_descriptors_match_rdkit_reference():
    for smi, ap in [("CCO", 0.0), ("c1ccccc1", 1.0)]:
        mol = Chem.MolFromSmiles(smi)
        r = esol_descriptors(smi)
        assert r["ok"] is True
        assert r["value"]["mw"] == pytest.approx(Descriptors.MolWt(mol))
        assert r["value"]["clogp"] == pytest.approx(Crippen.MolLogP(mol))
        assert r["value"]["rotb"] == rdMolDescriptors.CalcNumRotatableBonds(mol)
        assert r["value"]["ap"] == pytest.approx(ap)

def test_published_envelope():
    r = esol_published("CCO")
    assert r["ok"] is True
    assert r["unit"] == "logS (mol/L)"
    assert r["uncertainty_note"] and r["rdkit_version"]

def test_refit_uses_given_coefficients():
    c = {"intercept": 0.0, "logp": -1.0, "mw": 0.0, "rotb": 0.0, "ap": 0.0}
    mol = Chem.MolFromSmiles("c1ccccc1")
    assert esol_refit("c1ccccc1", c)["value"] == pytest.approx(-Crippen.MolLogP(mol))

def test_invalid_smiles_clean_error():
    for f in (esol_descriptors, esol_published):
        r = f("not-a-smiles")
        assert r.get("ok") is False and "error" in r
