"""Evaluate ESOL predictors on AqSolDB splits (Task 10)."""
import argparse, csv, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from rdkit import Chem

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "mcp"))
import esol  # noqa: E402

CLASSES = [("acid", "[#6](=O)[OX2H1]"), ("amine", "[#7;X3;v3;!$(N-[#6]=O);!$(N=*)]"), ("alcohol", "[OX2H1;!$(O-[#6]=O)]"), ("aromatic", "a"), ("halogen", "[#9,#17,#35,#53]")]
PATS = [(n, Chem.MolFromSmarts(s)) for n, s in CLASSES]

def classify(mol):
    for n, p in PATS:
        if mol.HasSubstructMatch(p):
            return n
    return "other"

def load(split):
    with open(ROOT / "data" / "solubility" / f"split_{split}.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def metrics(y, p):
    e = np.array(p, dtype=float) - np.array(y, dtype=float)
    return {"n": int(e.size), "rmse": float(np.sqrt(np.mean(e**2))), "mae": float(np.mean(np.abs(e))), "bias": float(np.mean(e)), "within_0.5": float(np.mean(np.abs(e) <= 0.5)), "within_1.0": float(np.mean(np.abs(e) <= 1.0))}

def fit(rows):
    X, y = [], []
    for r in rows:
        d = esol.esol_descriptors(r["smiles"])["value"]
        X.append([1.0, d["clogp"], d["mw"], d["rotb"], d["ap"]])
        y.append(float(r["logS"]))
    c = np.linalg.lstsq(np.array(X), np.array(y), rcond=None)[0]
    return {"intercept": float(c[0]), "logp": float(c[1]), "mw": float(c[2]), "rotb": float(c[3]), "ap": float(c[4])}

def predict(rows, coef):
    return [(r, esol.esol_from_descriptors(esol.esol_descriptors(r["smiles"])["value"], coef)) for r in rows]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["tune", "validation"])
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    split = a.split or "tune"
    if a.final:
        lock = (HERE / "LOCK.sha256").read_text().strip().split()[0]
        cur = sha(ROOT / "data" / "solubility" / "locked_ids.txt")
        if lock != cur:
            print("LOCK MISMATCH - refusing"); return 2
        with open(HERE / "LOCK_ACCESS_LOG.md", "a", encoding="utf-8") as f:
            f.write("- %s final run\n" % datetime.now(timezone.utc).isoformat())
        split = "locked"
        coef = json.loads((HERE / "refit_coeffs.json").read_text())
    else:
        tune = load("tune")
        cf = HERE / "refit_coeffs.json"
        coef = json.loads(cf.read_text()) if (split == "validation" and cf.exists()) else fit(tune)
        cf.write_text(json.dumps(coef, indent=2))
    rows = load(split)
    res = {}
    for tag, co in [("P-A", None), ("P-B", coef)]:
        pred = [(r, esol.esol_from_descriptors(esol.esol_descriptors(r["smiles"])["value"], None if co is None else co)) for r in rows]
        y = [float(r["logS"]) for r, _ in pred]
        p = [v for _, v in pred]
        m = metrics(y, p)
        by = {}
        for (r, v), yy in zip(pred, y):
            mol = Chem.MolFromSmiles(r["smiles"]); cl = classify(mol)
            by.setdefault(cl, [[], []])
            by[cl][0].append(yy); by[cl][1].append(v)
        m["by_class"] = {k: metrics(a, b) for k, (a, b) in by.items()}
        res[tag] = m
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    with open(HERE / f"preds_{split}_{ts}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["id","name","smiles","measured","P_A","P_B"])
        for (r, va), (_, vb) in zip([(r, esol.esol_from_descriptors(esol.esol_descriptors(r["smiles"])["value"])) for r in rows], pred if False else [(r, esol.esol_from_descriptors(esol.esol_descriptors(r["smiles"])["value"], coef)) for r in rows]):
            w.writerow([r["id"], r["name"], r["smiles"], r["logS"], va, vb])
    (HERE / f"results_{split}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: {m: round(v[m], 3) for m in ("n","rmse","mae","bias","within_0.5","within_1.0")} for k, v in res.items()}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

