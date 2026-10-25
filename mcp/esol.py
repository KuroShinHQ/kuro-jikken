"""ESOL aqueous-solubility predictor (pure, deterministic)."""
from __future__ import annotations
import rdkit
from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors

V = rdkit.__version__
COEF = {"intercept": 0.16, "logp": -0.63, "mw": -0.0062, "rotb": 0.066, "ap": -0.74}
__all__ = ["esol_descriptors", "esol_from_descriptors", "esol_published", "esol_refit", "domain_classify"]

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

IN_DOMAIN_ERR = 1.2   # log units: locked-set RMSE, in-domain group (KARNE 5-6)
OUT_DOMAIN_ERR = 5.0  # log units: locked-set RMSE, salts/mixtures + metal groups (KARNE 5-6)

_METALS = Chem.MolFromSmarts("[#3,#4,#11,#12,#19,#20,#21,#22,#23,#24,#25,#26,#27,#28,#29,#30,#31,#37,#38,#39,#40,#41,#42,#43,#44,#45,#46,#47,#48,#49,#50,#55,#56,#57,#72,#73,#74,#75,#76,#77,#78,#79,#80,#81,#82,#83,#87,#88]")

def domain_classify(smiles):
    """Applicability domain for the error bar. Rules (prereg P-A/P2 groups +
    phosphorus exclusion added in the v0.1.0 amendment):
    in-domain = neutral, single-component, no metal atom, MW<=500, no phosphorus.
    Tagging aligned with validation/solubility/final_metrics.py."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"ok": False, "error": f"RDKit could not parse SMILES: {smiles!r}", "rdkit_version": V}
    reasons = []
    if "." in smiles:
        reasons.append("multi-component (salts/mixtures)")
    if any(a.GetFormalCharge() != 0 for a in mol.GetAtoms()):
        reasons.append("charged species")
    if mol.HasSubstructMatch(_METALS):
        reasons.append("contains metal atom")
    mw = Descriptors.MolWt(mol)
    if mw > 500:
        reasons.append(f"MW {mw:.1f} > 500")
    if any(a.GetSymbol() == "P" for a in mol.GetAtoms()):
        reasons.append("contains phosphorus")
    return {"ok": True, "in_domain": not reasons, "domain_reasons": reasons, "rdkit_version": V}

def esol_published(smiles):
    r = esol_descriptors(smiles)
    if not r.get("ok"):
        return r
    out = {"ok": True, "value": esol_from_descriptors(r["value"]), "unit": "logS (mol/L)", "method": "ESOL, Delaney 2004 published coefficients", "rdkit_version": V, "uncertainty_note": NOTE}
    d = domain_classify(smiles)
    if d.get("ok"):
        out["in_domain"] = d["in_domain"]
        out["domain_reasons"] = d["domain_reasons"]
        out["error_bar_logS"] = IN_DOMAIN_ERR if d["in_domain"] else OUT_DOMAIN_ERR
        out["error_bar_source"] = "locked-set single evaluation (validation/solubility/KARNE.md): in-domain RMSE ~1.2, salts/mixtures+metal groups ~5 log units"
        if not d["in_domain"]:
            out["caveat"] = "OUT OF APPLICABILITY DOMAIN (%s): this estimate is unreliable; expect error ~%s log units or worse." % (", ".join(d["domain_reasons"]), OUT_DOMAIN_ERR)
    return out

def esol_refit(smiles, coef):
    r = esol_descriptors(smiles)
    if not r.get("ok"):
        return r
    return {"ok": True, "value": esol_from_descriptors(r["value"], coef), "unit": "logS (mol/L)", "method": "ESOL form with coefficients refit on the tune split", "rdkit_version": V, "uncertainty_note": NOTE}
