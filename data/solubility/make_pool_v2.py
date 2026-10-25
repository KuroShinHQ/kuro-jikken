"""Build the in-domain pool for the solubility + sigma-feature study (v2).

Counts only: no solubility value is compared with anything, no engine is run, no
error metric is computed. Labels are carried through as data for the later
evaluation; they are not used to decide anything here.

Rules (prereg/solubility_sigma_feature_plan_v1.md, sections 5-6):
  * match AqSolDB to the sigma DB on the exact full 27-character InChIKey
  * one profile per molecule: rows that parse to formal charge 0, lowest CID,
    tie broken by lowest file row; no neutral row -> out of domain
  * in domain: neutral, single component (no "."), elements only C,H,N,O,S,F,Cl,Br,I,
    AqSolDB logS present and numeric

Usage:
  python data/solubility/make_pool_v2.py [--aqsoldb PATH] [--index PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from rdkit import Chem

REPO = Path(__file__).resolve().parents[2]
ALLOWED = frozenset({"C", "H", "N", "O", "S", "F", "Cl", "Br", "I"})


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def formal_charge(smiles):
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return None
    return sum(atom.GetFormalCharge() for atom in mol.GetAtoms())


def in_domain(smiles):
    """Returns (ok, reason). Checks the query molecule (AqSolDB SMILES)."""
    if not smiles:
        return False, "missing_smiles"
    if "." in smiles:
        return False, "multi_component"
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False, "smiles_unparsable"
    if any(atom.GetFormalCharge() != 0 for atom in mol.GetAtoms()):
        return False, "charged"
    symbols = {atom.GetSymbol() for atom in mol.GetAtoms()}
    if not symbols <= ALLOWED:
        return False, "element_not_allowed:" + ",".join(sorted(symbols - ALLOWED))
    return True, "in_domain"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aqsoldb", default=str(REPO / "data/solubility/raw/aqsoldb_20261025.tab"))
    parser.add_argument(
        "--index",
        default=r"C:\KuroshinHQ\_hub\data\formulation_sigma\sigma_profile_index.parquet",
    )
    parser.add_argument("--out", default=str(REPO / "data/solubility/pool_v2.csv"))
    args = parser.parse_args()

    aqsoldb = pd.read_csv(args.aqsoldb, sep="\t")
    index = pq.read_table(args.index, columns=["CID", "InChIKey", "SMILES"]).to_pandas()

    # full 27-character InChIKey, file order preserved
    index = index[index["InChIKey"].notna() & (index["InChIKey"].str.len() == 27)]
    grouped = {}
    for order, row in enumerate(index.itertuples(index=False)):
        grouped.setdefault(row.InChIKey, []).append((int(row.CID), row.SMILES, order))

    aqsoldb_keys = set(aqsoldb["InChIKey"].dropna())
    matched = aqsoldb[aqsoldb["InChIKey"].isin(grouped)]
    matched_rows = int(aqsoldb["InChIKey"].isin(grouped).sum())

    reasons = {}
    records = []
    for row in matched.itertuples(index=False):
        key = row.InChIKey
        rows = grouped[key]
        neutral = [(cid, order) for cid, smi, order in rows if formal_charge(smi) == 0]
        if not neutral:
            reasons["no_neutral_row"] = reasons.get("no_neutral_row", 0) + 1
            continue
        cid = min(neutral, key=lambda item: (item[0], item[1]))[0]
        ok, reason = in_domain(row.SMILES)
        if not ok:
            reasons[reason] = reasons.get(reason, 0) + 1
            continue
        try:
            logs = float(row.Solubility)
        except (TypeError, ValueError):
            reasons["logS_not_numeric"] = reasons.get("logS_not_numeric", 0) + 1
            continue
        if logs != logs:  # NaN
            reasons["logS_not_numeric"] = reasons.get("logS_not_numeric", 0) + 1
            continue
        records.append(
            {
                "inchikey": key,
                "cid": cid,
                "smiles": row.SMILES,
                "logS": logs,
                "sigma_rows": len(rows),
                "neutral_rows": len(neutral),
            }
        )

    pool = pd.DataFrame.from_records(records).sort_values("inchikey", kind="mergesort")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pool.to_csv(out, index=False, lineterminator="\n")

    report = {
        "aqsoldb_rows": int(len(aqsoldb)),
        "matched_rows_full_inchikey": matched_rows,
        "dropped": reasons,
        "pool_rows": int(len(pool)),
        "unique_keys": int(pool["inchikey"].nunique()),
        "pool_sha256": sha256(out),
        "rules": {
            "match": "exact full 27-character InChIKey",
            "one_profile": "neutral rows only, lowest CID, tie = lowest file row",
            "in_domain": "neutral, single component, elements C,H,N,O,S,F,Cl,Br,I, logS numeric",
            "no_MW_limit": True,
        },
    }
    (out.parent / "pool_v2_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (out.parent / "pool_v2.sha256").write_text(
        f"{report['pool_sha256']}  {out.name}\n", encoding="utf-8", newline="\n"
    )

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
