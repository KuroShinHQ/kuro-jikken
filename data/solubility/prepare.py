import csv, hashlib, random, sys
from pathlib import Path
from rdkit import Chem

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "aqsoldb_20261025.tab"
SEED = 20261025

rows = list(csv.DictReader(open(RAW, encoding="utf-8"), delimiter="\t"))
print("input_rows", len(rows))
kept, excl = [], {"P": 0, "unparse": 0}
pat_p = Chem.MolFromSmarts("[#15]")
for r in rows:
    smi = (r.get("SMILES") or "").strip()
    m = Chem.MolFromSmiles(smi) if smi else None
    if m is None:
        excl["unparse"] += 1; continue
    if m.HasSubstructMatch(pat_p):
        excl["P"] += 1; continue
    kept.append({"id": r["ID"], "name": r.get("Name",""), "smiles": smi, "logS": r["Solubility"]})
print("kept", len(kept), "excluded", excl)

ids = sorted(k["id"] for k in kept)
random.Random(SEED).shuffle(ids)
n = len(ids); a, b = int(n*0.5), int(n*0.75)
parts = {"tune": ids[:a], "validation": ids[a:b], "locked": ids[b:]}
by_id = {k["id"]: k for k in kept}
for part, sel in parts.items():
    with open(HERE / f"split_{part}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["id","name","smiles","logS"])
        for i in sel:
            k = by_id[i]; w.writerow([k["id"], k["name"], k["smiles"], k["logS"]])
    print(part, len(sel))

locked_txt = HERE / "locked_ids.txt"
locked_txt.write_text("\n".join(sorted(parts["locked"])) + "\n", encoding="utf-8")
h = hashlib.sha256(locked_txt.read_bytes()).hexdigest()
(HERE.parent.parent / "validation" / "solubility").mkdir(parents=True, exist_ok=True)
open(HERE.parent.parent / "validation" / "solubility" / "LOCK.sha256", "w", encoding="utf-8").write(h + "  locked_ids.txt\n")
print("LOCK_SHA256", h)
print("total", n, "seed", SEED)
