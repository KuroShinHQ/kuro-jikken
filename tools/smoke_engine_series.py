"""Label-free smoke test: the REAL engine_series on the seven sanity solutes.

Disclosed in prereg/solubility_sigma_feature_plan_v1.md section 16 as a
label-free sanity run. No solubility label is read here: each row carries only
a SMILES (converted to an InChIKey) and the engine feature. The adapter is
built by `make_profiles()` from tools/solubility_eval_v2.py -- the exact
constructor and import path the real run uses in main().

Reference: C:\\KuroshinHQ\\_hub\\logs\\cosmosac_sanity_20261025.txt
Criterion: every value finite AND equal to that log within 1e-9.

Run:  .venv\\Scripts\\python.exe tools/smoke_engine_series.py   (exit 0 = PASS)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

from solubility_eval_v2 import (  # noqa: E402
    ENGINE_TEMPERATURE_K,
    SIGMA_DIR,
    engine_series,
    make_profiles,
)

SANITY_LOG = Path(r"C:\KuroshinHQ\_hub\logs\cosmosac_sanity_20261025.txt")
TOL = 1e-9
N_POOL = 3132                      # molecules in the real tune set
N_SPLIT = 4698                     # tune + locked, the full evaluation load

# structure only: no label, no solubility value anywhere in this file
SOLUTES = {
    "ethanol": "CCO",
    "benzene": "c1ccccc1",
    "toluene": "Cc1ccccc1",
    "caffeine": "Cn1cnc2c1c(=O)n(C)c(=O)n2C",
    "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
    "acetic acid": "CC(=O)O",
    "urea": "NC(=O)N",
}


def reference_values() -> dict:
    """inchikey -> ln(gamma_inf) from the earlier sanity log (JSON block)."""
    text = SANITY_LOG.read_text(encoding="utf-8")
    start = text.index("[", text.index("RESULT:"))
    payload = json.loads(text[start:])
    return {r["inchikey"]: r["ln_gamma_inf"] for r in payload[1]["rows"]}


def main() -> int:
    from rdkit import Chem

    ref = reference_values()
    rows = []
    for name, smiles in SOLUTES.items():
        inchikey = Chem.MolToInchiKey(Chem.MolFromSmiles(smiles))
        rows.append({"inchikey": inchikey, "smiles": smiles})
        if inchikey not in ref:
            print(f"FAIL {name}: derived InChIKey {inchikey} not in sanity log")
            return 1

    # same constructor + import path as main()
    profiles = make_profiles(cache_dir=SIGMA_DIR / "engine" / "_cache_smoke")

    print(f"temperature_K={ENGINE_TEMPERATURE_K}  solvent=water(CID 962)  tol={TOL:g}")
    t0 = time.perf_counter()
    values = engine_series(rows, profiles)          # label-free, real code path
    cold = time.perf_counter() - t0
    t1 = time.perf_counter()
    engine_series(rows, profiles)                   # second pass: steady state
    warm = time.perf_counter() - t1

    bad = 0
    for row, value in zip(rows, values):
        want = ref[row["inchikey"]]
        finite = value is not None and value == value and abs(value) != float("inf")
        diff = abs(value - want) if value is not None else float("inf")
        ok = bool(finite) and diff <= TOL
        bad += 0 if ok else 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {row['inchikey']}  "
              f"got={value!r}  log={want!r}  |diff|={diff:.3e}")

    n = len(rows)
    print(f"\nall_finite={all(v is not None and v == v for v in values)}  "
          f"max_tol_violations={bad}")
    print(f"timing: n={n}  cold={cold:.3f}s ({cold / n:.4f} s/molecule, includes "
          f"index+parquet load)  warm={warm:.3f}s ({warm / n:.4f} s/molecule)")
    print(f"linear estimate (warm per molecule): {N_POOL} molecules = "
          f"{warm / n * N_POOL:.1f}s   {N_SPLIT} molecules = {warm / n * N_SPLIT:.1f}s")
    print("RESULT: " + ("ALL PASS" if bad == 0 else f"FAIL ({bad})"))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
