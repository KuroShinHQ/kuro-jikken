import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))
import rdkit_tool as T

RAW = ROOT / "data" / "raw_pubchem"
OUT = ROOT / "validation" / "tool_vs_pubchem.md"
MOLS = json.loads((ROOT / "data" / "sample_set.json").read_text(encoding="utf-8"))["molecules"]

def props(cid):
    f = sorted(RAW.glob(f"cid_{cid}_*.json"))[-1]
    return json.loads(f.read_text(encoding="utf-8"))["PropertyTable"]["Properties"][0]

def smi(p):
    return p.get("SMILES") or p.get("ConnectivitySMILES")

def why(pair, pc):
    a, b = pair
    if a == pc and b == pc: return "both variants match PubChem"
    if a == pc: return "Lipinski/Default variant matches PubChem"
    if b == pc: return "plain/NonStrict variant matches PubChem"
    return "definition gap: neither variant equals PubChem"

MANUAL_RINGS = {"water":0,"ethanol":0,"benzene":1,"aceticacid":0,"acetone":0,"urea":0,"glycine":0,"aspirin":1,"caffeine":2,"glucose":1,"citricacid":0,"ibuprofen":1,"menthol":1,"vanillin":1}
rows = []
for m in MOLS:
    p = props(m["cid"]); s = smi(p)
    rows.append((m["name"], m["cid"], s, p,
        T.formula(s)["value"], p.get("MolecularFormula"),
        T.molecular_weight(s)["value"], p.get("MolecularWeight"),
        T.heavy_atom_count(s)["value"], p.get("HeavyAtomCount"),
        T.ring_count(s)["value"],
        T.hbd_lipinski(s)["value"], T.hbd_plain(s)["value"], p.get("HBondDonorCount"),
        T.hba_lipinski(s)["value"], T.hba_plain(s)["value"], p.get("HBondAcceptorCount"),
        T.rotatable_bonds_strict(s)["value"], T.rotatable_bonds_nonstrict(s)["value"], p.get("RotatableBondCount")))

L = []
L.append("# Tool vs PubChem - validation report (Task 6)")
L.append("")
L.append("Provenance: raw PUG REST snapshots in data/raw_pubchem/ (2026-10-24); RDKit 2026.09.1 pinned; CIDs verified via name->CID lookup.")
L.append("")
L.append("## 1) Structural identity and mass")
L.append("")
L.append("| molecule | CID | formula pc | formula rd | MW pc | MW rd | dMW | heavy pc | heavy rd |")
L.append("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    L.append(f"| {r[0]} | {r[1]} | {r[5]} | {r[4]} | {r[7]} | {r[6]:.3f} | {r[6]-float(r[7]):+.3f} | {r[9]} | {r[8]} |")
L.append("")
L.append("## 2) H-bond donors: Lipinski vs plain vs PubChem")
L.append("")
L.append("| molecule | PubChem | Lipinski (NH/OH H count) | plain (donor atoms) | cause |")
L.append("|---|---|---|---|---|")
for r in rows:
    L.append(f"| {r[0]} | {r[13]} | {r[11]} | {r[12]} | {why((r[11], r[12]), r[13])} |")
L.append("")
L.append("## 3) H-bond acceptors: Lipinski vs plain vs PubChem")
L.append("")
L.append("| molecule | PubChem | Lipinski (N+O count) | plain (acceptor atoms) | cause |")
L.append("|---|---|---|---|---|")
for r in rows:
    L.append(f"| {r[0]} | {r[16]} | {r[14]} | {r[15]} | {why((r[14], r[15]), r[16])} |")
L.append("")
L.append("## 4) Rotatable bonds: default(strict) vs NonStrict vs PubChem")
L.append("")
L.append("| molecule | PubChem | default | NonStrict | cause |")
L.append("|---|---|---|---|---|")
for r in rows:
    L.append(f"| {r[0]} | {r[19]} | {r[17]} | {r[18]} | {why((r[17], r[18]), r[19])} |")
L.append("")
L.append("## 5) Ring counts (manual count)")
L.append("")
L.append("PubChem PUG REST has no RingCount property (probe: HTTP 400). Values below are labelled manual counts from structure; RDKit CalcNumRings (SSSR) is compared against them.")
L.append("")
L.append("| molecule | rings (manual count) | rings (RDKit) |")
L.append("|---|---|---|")
for r in rows:
    L.append(f"| {r[0]} | {MANUAL_RINGS[r[0]]} | {r[10]} |")
L.append("## 6) CID 1253 - CID assignment error")
L.append("")
L.append("First seed fetch assigned CID 1253 to menthol from memory; the returned compound was C15H18N2O, not menthol (C10H20O). Name->CID resolution gives 1254. Raw cid_1253_*.json is retained as evidence; data/sample_set.json records the corrected CID.")
L.append("")
L.append("## 7) Reproduce")
L.append("")
L.append("    .venv\\Scripts\\python data/pubchem_fetch.py --verify-existing")
L.append("    .venv\\Scripts\\python validation/build_tool_vs_pubchem.py")
L.append("")
OUT.write_text("\n".join(L), encoding="utf-8")
print("WROTE", OUT, len(L), "lines")


