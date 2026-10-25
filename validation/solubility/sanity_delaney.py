"""P-A sanity check on the original Delaney/ESOL set (PRIORITY 1)."""
import csv, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "mcp"))
import esol  # noqa: E402

rows = list(csv.DictReader(open(ROOT / "data/solubility/delaney/delaney_20261025.csv", encoding="utf-8")))
y, p, bad = [], [], 0
for r in rows:
    v = esol.esol_published(r["smiles"])
    if not v.get("ok"):
        bad += 1; continue
    y.append(float(r["measured log solubility in mols per litre"])); p.append(v["value"])
e = np.array(p) - np.array(y)
print("n", len(e), "unparse", bad)
print("rmse", round(float(np.sqrt(np.mean(e**2))), 3), "mae", round(float(np.mean(np.abs(e))), 3), "bias", round(float(np.mean(e)), 3), "w1.0", round(float(np.mean(np.abs(e)<=1.0)), 3))
