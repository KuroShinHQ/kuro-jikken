"""ESOL aqueous-solubility predictor (pure, deterministic)."""
from __future__ import annotations
import rdkit
from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors

V = rdkit.__version__
COEF = {"intercept": 0.16, "logp": -0.63, "mw": -0.0062, "rotb": 0.066, "ap": -0.74}
__all__ = ["esol_descriptors", "esol_from_descriptors", "esol_published", "esol_refit"]

def esol_descriptors(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"ok": False, "error": f"RDKit could not parse SMILES: {smiles!r}", "rdkit_version": V}
    nh = mol.GetNumHeavyAtoms()
    ar = len(mol.GetSubstructMatches(Chem.MolFromSmarts("a")))
    ap = (ar / nh) if nh else 0.0
    d = {"clogp": Crippen.MolLogP(mol), "mw": Descriptors.MolWt(mol), "rotb": rdMolDescriptors.CalcNumRotatableBonds(mol), "ap": ap}
    return {"ok": True, "value": d, "unit": "descriptor", "method": "ESOL descriptors: Crippen.MolLogP, Descriptors.MolWt, CalcNumRotatableBonds default, aromatic heavy atoms / heavy atoms", "rdkit_version": V}

def esol_from_descriptors(d, coef=None):
    c = COEF if coef is None else coef
    return c["intercept"] + c["logp"]*d["clogp"] + c["mw"]*d["mw"] + c["rotb"]*d["rotb"] + c["ap"]*d["ap"]

NOTE = "published ESOL typical error ~1.0 log unit RMSE (Delaney 2004); measured locked-set error is reported in validation/solubility/KARNE.md after evaluation"

def esol_published(smiles):
    r = esol_descriptors(smiles)
    if not r.get("ok"):
        return r
    return {"ok": True, "value": esol_from_descriptors(r["value"]), "unit": "logS (mol/L)", "method": "ESOL, Delaney 2004 published coefficients", "rdkit_version": V, "uncertainty_note": NOTE}

def esol_refit(smiles, coef):
    r = esol_descriptors(smiles)
    if not r.get("ok"):
        return r
    return {"ok": True, "value": esol_from_descriptors(r["value"], coef), "unit": "logS (mol/L)", "method": "ESOL form with coefficients refit on the tune split", "rdkit_version": V, "uncertainty_note": NOTE}
