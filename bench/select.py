"""Select the 250 benchmark molecules from the AqSolDB data in this repository.

Implements prereg section 3.1: in-domain rule (neutral, single component, no
metal atoms, no phosphorus, MW <= 500, parseable), random sample N = 250 with
seed 20261026, first 50 = pilot, next 200 = confirmatory.

The in-domain element whitelist is the one used by the solubility study
(C, H, N, O, S, F, Cl, Br, I); it excludes every metal and phosphorus, and also
other inorganic elements, which keeps the set inside the rule's intent.
No model is called here and no answer value is read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import sys
from typing import Iterable

import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors

REPO = pathlib.Path(__file__).resolve().parents[1]
ALLOWED = frozenset({"C", "H", "N", "O", "S", "F", "Cl", "Br", "I"})
MW_LIMIT = 500.0
SEED = 20261026
N_TOTAL = 250
N_PILOT = 50


def in_domain(smiles: str) -> tuple[bool, str]:
    """Return ``(ok, reason)`` for one SMILES under the in-domain rule."""
    if not isinstance(smiles, str) or not smiles.strip():
        return False, "missing_smiles"
    if "." in smiles:
        return False, "multi_component"
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False, "smiles_unparsable"
    if len(Chem.GetMolFrags(mol)) > 1:
        return False, "multi_component"
    if any(atom.GetFormalCharge() != 0 for atom in mol.GetAtoms()):
        return False, "charged"
    symbols = {atom.GetSymbol() for atom in mol.GetAtoms()}
    if not symbols <= ALLOWED:
        return False, "element_not_allowed:" + ",".join(sorted(symbols - ALLOWED))
    if Descriptors.MolWt(mol) > MW_LIMIT:
        return False, "mw_over_500"
    return True, "in_domain"


def filter_frame(frame: pd.DataFrame) -> tuple[list[dict], dict[str, int]]:
    """Apply the rule, deduplicate by InChIKey (first file row wins)."""
    reasons: dict[str, int] = {}
    seen: set[str] = set()
    kept: list[dict] = []
    for row in frame.itertuples(index=False):
        key = getattr(row, "InChIKey", None)
        if not isinstance(key, str) or not key.strip():
            reasons["missing_inchikey"] = reasons.get("missing_inchikey", 0) + 1
            continue
        if key in seen:
            reasons["duplicate_inchikey"] = reasons.get("duplicate_inchikey", 0) + 1
            continue
        ok, reason = in_domain(getattr(row, "SMILES", ""))
        if not ok:
            reasons[reason] = reasons.get(reason, 0) + 1
            continue
        seen.add(key)
        kept.append(
            {
                "molecule_id": key.strip(),
                "smiles": getattr(row, "SMILES"),
                "aqsoldb_id": str(getattr(row, "ID", "")),
                "name": str(getattr(row, "Name", "")),
            }
        )
    return kept, reasons


def select(
    frame: pd.DataFrame,
    n_total: int = N_TOTAL,
    n_pilot: int = N_PILOT,
    seed: int = SEED,
) -> tuple[list[dict], dict]:
    """Return ``(records, report)`` with split labels assigned in sample order."""
    if n_pilot >= n_total:
        raise ValueError("n_pilot must be smaller than n_total")
    kept, reasons = filter_frame(frame)
    if len(kept) < n_total:
        raise ValueError(f"only {len(kept)} in-domain molecules, need {n_total}")
    pool = sorted(kept, key=lambda r: r["molecule_id"])
    sampled = random.Random(seed).sample(pool, n_total)
    records = []
    for seq, row in enumerate(sampled):
        record = dict(row)
        record["seq"] = seq
        record["split"] = "pilot" if seq < n_pilot else "confirmatory"
        records.append(record)
    report = {
        "source_rows": int(len(frame)),
        "in_domain_rows": len(kept),
        "dropped": dict(sorted(reasons.items())),
        "duplicates_removed": reasons.get("duplicate_inchikey", 0),
        "n_total": n_total,
        "n_pilot": n_pilot,
        "n_confirmatory": n_total - n_pilot,
        "seed": seed,
        "sample": "random.Random(seed).sample(sorted_by_molecule_id, n_total)",
        "order": "sample order = registration order; first n_pilot rows are pilot",
        "rules": {
            "neutral": "every atom has formal charge 0",
            "single_component": "no '.' in SMILES and one fragment after parsing",
            "elements": sorted(ALLOWED),
            "mw_limit_g_per_mol": MW_LIMIT,
            "mw_source": "rdkit.Chem.Descriptors.MolWt",
            "parseable": "rdkit.Chem.MolFromSmiles is not None",
        },
    }
    return records, report


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_id_lists(records: Iterable[dict], outdir: pathlib.Path) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    records = list(records)
    pilot = [r for r in records if r["split"] == "pilot"]
    confirm = [r for r in records if r["split"] == "confirmatory"]
    pilot_path = outdir / "ids_pilot.txt"
    confirm_path = outdir / "ids_confirmatory.txt"
    pilot_path.write_text(
        "".join(f"{r['molecule_id']}\n" for r in pilot), encoding="utf-8", newline="\n"
    )
    confirm_path.write_text(
        "".join(f"{r['molecule_id']}\n" for r in confirm),
        encoding="utf-8",
        newline="\n",
    )
    all_path = outdir / "ids_all.csv"
    with open(all_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("seq,molecule_id,split,aqsoldb_id,name,smiles\n")
        for r in records:
            name = (r["name"] or "").replace('"', "'").replace(",", ";")
            handle.write(
                f'{r["seq"]},{r["molecule_id"]},{r["split"]},{r["aqsoldb_id"]},'
                f'"{name}","{r["smiles"]}"\n'
            )
    hashes = {
        "ids_pilot.txt": sha256_file(pilot_path),
        "ids_confirmatory.txt": sha256_file(confirm_path),
        "ids_all.csv": sha256_file(all_path),
    }
    (outdir / "ID_LISTS.sha256").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in hashes.items()),
        encoding="utf-8",
        newline="\n",
    )
    return hashes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="select the 250 benchmark molecules")
    parser.add_argument(
        "--aqsoldb",
        default=str(REPO / "data/solubility/raw/aqsoldb_20261025.tab"),
    )
    parser.add_argument("--outdir", default=str(REPO / "bench/data"))
    parser.add_argument("--n-total", type=int, default=N_TOTAL)
    parser.add_argument("--n-pilot", type=int, default=N_PILOT)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)

    frame = pd.read_csv(args.aqsoldb, sep="\t")
    records, report = select(frame, args.n_total, args.n_pilot, args.seed)
    hashes = write_id_lists(records, pathlib.Path(args.outdir))
    report["hashes"] = hashes
    report["aqsoldb_sha256"] = sha256_file(pathlib.Path(args.aqsoldb))
    report_path = pathlib.Path(args.outdir) / "selection_report.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
