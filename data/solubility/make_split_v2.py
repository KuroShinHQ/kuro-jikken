"""Molecule-level tune/locked split for the solubility + sigma-feature study (v2).

Plan section 7: 50/50, seed 20261027, rows sorted by InChIKey, seeded Fisher-Yates
with Python `random.Random(20261027)`, first half tune, second half locked. The
locked set is hashed here; Freeze-2 only publishes that hash.

No label is read here beyond carrying the pool columns through.

Usage:
  python data/solubility/make_split_v2.py [--pool PATH] [--seed 20261027] [--outdir DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
MIN_LOCKED = 800


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fisher_yates(items, seed):
    """Explicit seeded Fisher-Yates (in place), as written in the plan."""
    rng = random.Random(seed)
    for i in range(len(items) - 1, 0, -1):
        j = rng.randrange(i + 1)
        items[i], items[j] = items[j], items[i]
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", default=str(REPO / "data/solubility/pool_v2.csv"))
    parser.add_argument("--seed", type=int, default=20261027)
    parser.add_argument("--outdir", default=str(REPO / "data/solubility"))
    args = parser.parse_args()

    pool_path = Path(args.pool)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    pool_sha = sha256(pool_path)
    pool = pd.read_csv(pool_path)
    if pool["inchikey"].duplicated().any():
        raise SystemExit("pool has duplicate InChIKeys; the one-profile rule must run first")

    rows = pool.to_dict("records")
    rows.sort(key=lambda row: row["inchikey"].encode("utf-8"))
    shuffled = fisher_yates(list(rows), args.seed)

    n = len(shuffled)
    cut = n // 2
    tune = pd.DataFrame.from_records(shuffled[:cut])
    locked = pd.DataFrame.from_records(shuffled[cut:])

    tune_path = outdir / "split_tune_v2.csv"
    locked_path = outdir / "split_locked_v2.csv"
    tune.to_csv(tune_path, index=False, lineterminator="\n")
    locked.to_csv(locked_path, index=False, lineterminator="\n")

    locked_sha = sha256(locked_path)
    (outdir / "LOCKED_V2.sha256").write_text(
        f"{locked_sha}  {locked_path.name}\n", encoding="utf-8", newline="\n"
    )

    gate = "PASS" if len(locked) >= MIN_LOCKED else "STOP"
    meta = {
        "pool_file": pool_path.name,
        "pool_sha256": pool_sha,
        "seed": args.seed,
        "split": "50/50 molecule-level; first half tune, second half locked",
        "algorithm": "sorted by InChIKey (UTF-8 bytes), explicit seeded Fisher-Yates",
        "pool_rows": n,
        "tune_rows": int(len(tune)),
        "locked_rows": int(len(locked)),
        "locked_sha256": locked_sha,
        "min_locked": MIN_LOCKED,
        "gate": gate,
    }
    (outdir / "SPLIT_V2_META.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    print(json.dumps(meta, indent=2))
    if gate == "STOP":
        print(f"GATE STOP: locked half has {len(locked)} molecules (< {MIN_LOCKED}); do not proceed.")
        return 2
    print(f"GATE {gate}: locked half has {len(locked)} molecules (>= {MIN_LOCKED}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
