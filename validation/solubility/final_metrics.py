import csv
from pathlib import Path
import numpy as np
from rdkit import Chem
from rdkit.Chem import Descriptors
HERE = Path(__file__).resolve().parent
f = sorted(HERE.glob("preds_locked_*.csv"))[-1]
rows = list(csv.DictReader(open(f, encoding="utf-8")))
METALS = Chem.MolFromSmarts("[#3,#4,#11,#12,#19,#20,#21,#22,#23,#24,#25,#26,#27,#28,#29,#30,#31,#37,#38,#39,#40,#41,#42,#43,#44,#45,#46,#47,#48,#49,#50,#55,#56,#57,#72,#73,#74,#75,#76,#77,#78,#79,#80,#81,#82,#83,#87,#88]")
def tag(r):
    smi = r["smiles"]; mol = Chem.MolFromSmiles(smi); mw = Descriptors.MolWt(mol) if mol else 0
    if "." in smi: return "multi"
    if "+" in smi or "-" in smi: return "charged"
    if mol and mol.HasSubstructMatch(METALS): return "metal"
    if mw > 500: return "heavy"
    return "in_domain"

def rmse(sel, col):
    e = np.array([float(r[col]) - float(r["measured"]) for r in sel]); return float(np.sqrt((e**2).mean()))

for t in ("in_domain", "multi", "metal"):
    sel = [r for r in rows if tag(r) == t]
    print(t, len(sel), "A=%.3f" % rmse(sel, "P_A"), "B=%.3f" % rmse(sel, "P_B"))
