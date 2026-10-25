"""POST-HOC exploratory error analysis (NOT pre-registered). Tune+validation only."""
import csv
from pathlib import Path
import numpy as np
from rdkit import Chem
from rdkit.Chem import Descriptors

HERE = Path(__file__).resolve().parent
rows = []
for split in ("tune", "validation"):
    f = sorted(HERE.glob(f"preds_{split}_*.csv"))[-1]
    rows += list(csv.DictReader(open(f, encoding="utf-8")))

METALS = Chem.MolFromSmarts("[#3,#4,#11,#12,#19,#20,#21,#22,#23,#24,#25,#26,#27,#28,#29,#30,#31,#37,#38,#39,#40,#41,#42,#43,#44,#45,#46,#47,#48,#49,#50,#55,#56,#57,#72,#73,#74,#75,#76,#77,#78,#79,#80,#81,#82,#83,#87,#88]")

def tag(r):
    smi = r["smiles"]
    mol = Chem.MolFromSmiles(smi)
    mw = Descriptors.MolWt(mol) if mol else 0
    if "." in smi: return "multi-component"
    if "+" in smi or "-" in smi: return "charged"
    if mol and mol.HasSubstructMatch(METALS): return "metal-containing"
    if mw > 500: return "MW>500"
    return "neutral single-component <=500"

recs = [(r, float(r["measured"]), float(r["P_A"]), tag(r)) for r in rows]
err = np.array([p - m for _, m, p, _ in recs])
L = ["# Exploratory error analysis (POST-HOC, NOT pre-registered)", "", "Tune+validation only; locked untouched; pre-registered results unchanged.", "", "MAE %.3f, RMSE %.3f, n=%d" % (abs(err).mean(), np.sqrt((err**2).mean()), err.size), "", "| group | n | MAE | RMSE |", "|---|---|---|---|"]
groups = {}
for _, m, p, t in recs: groups.setdefault(t, []).append(p - m)
for t in sorted(groups):
    e = np.array(groups[t]); L.append("| %s | %d | %.3f | %.3f |" % (t, e.size, abs(e).mean(), np.sqrt((e**2).mean())))

L += ["", "## Top 20 worst predictions (P-A)", "", "| name | smiles | measured | predicted | error |", "|---|---|---|---|---|"]
for r, m, p, t in sorted(recs, key=lambda x: -abs(x[2] - x[1]))[:20]:
    L.append("| %s | %s | %.2f | %.2f | %+.2f |" % (r["name"], r["smiles"], m, p, p - m))
open(HERE / "exploratory.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("WROTE exploratory.md rows", len(recs))
