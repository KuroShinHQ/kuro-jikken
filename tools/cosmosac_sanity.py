"""Label-free sanity checks for the PubChemQC -> cCOSMO adapter (plan step 2).

Checks (no solubility label, no error metric, no AqSolDB value is read):
  1. water in water: ln(gamma-infinity) must be ~0
  2. a few solutes in water: finite value and a strictly positive activity coefficient
  3. same code path as the NIST example profiles: the stock UD database path and the
     DirectImport path (same .sigma bytes) must give the same numbers

Usage:
  python tools/cosmosac_sanity.py [--sigma-dir DIR] [--engine-dir DIR] [--cache DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "mcp"))

from cosmosac_pubchemqc import (  # noqa: E402
    WATER_CID,
    WATER_KEY,
    PubChemQCProfiles,
    engine_worked,
)

DEFAULT_SIGMA_DIR = Path(
    os.environ.get("KURO_SIGMA_DIR", r"C:\KuroshinHQ\_hub\data\formulation_sigma")
)

SOLUTES = {
    "ethanol": "LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
    "benzene": "UHOVQNZJYSORNB-UHFFFAOYSA-N",
    "toluene": "YXFVVABEGXRONW-UHFFFAOYSA-N",
    "caffeine": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
    "aspirin": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
    "acetic acid": "QTBSBXVTEAMEQO-UHFFFAOYSA-N",
    "urea": "XSQUKJJJFZCRTK-UHFFFAOYSA-N",
}


def _ud_key(complist, name):
    """Resolve a UD name to its InChIKey using the database's own index."""
    for line in complist.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 7 and parts[3].upper() == name.upper():
            return parts[6]
    raise KeyError(f"{name} not found in {complist}")


def check_same_code_path(engine_dir, cache, results):
    """Stock `easy_COSMOSAC.calc_LNAC` vs our DirectImport path, identical bytes."""
    sys.path.insert(0, str(engine_dir))
    import cCOSMO  # noqa: F401  (imported through easy_COSMOSAC as well)
    import easy_COSMOSAC

    names = ["ETHANOL", "METHANOL"]
    composition = [0.3, 0.7]
    temperature = 300.0

    stock = np.asarray(
        easy_COSMOSAC.calc_LNAC(
            method="COSMOSAC-2010",
            dbname="UD",
            names=names,
            composition=composition,
            T=temperature,
        ),
        dtype=float,
    )

    ud_sigma = engine_dir / "profiles" / "UD" / "sigma3"
    complist = engine_dir / "profiles" / "UD" / "complist.txt"
    eq_dir = cache / "ud_same_bytes"
    eq_dir.mkdir(parents=True, exist_ok=True)
    keys = []
    for name in names:
        key = _ud_key(complist, name)
        shutil.copyfile(ud_sigma / f"{key}.sigma", eq_dir / f"{key}.sigma")
        keys.append(key)

    db = cCOSMO.DirectImport()
    for key in keys:
        db.add_profile(key, str(eq_dir))
    model = cCOSMO.COSMO3(keys, db)  # default (published) constants, no refit
    comp = np.asarray(composition, dtype=float)
    ours = np.asarray(
        model.get_lngamma_comb(temperature, comp) + model.get_lngamma_resid(temperature, comp),
        dtype=float,
    )

    diff = np.abs(stock - ours)
    results.append(
        {
            "check": "same_code_path_UD_ethanol_methanol_300K",
            "stock_ln_gamma": [float(x) for x in stock],
            "direct_import_ln_gamma": [float(x) for x in ours],
            "max_abs_diff": float(diff.max()),
            "pass": bool(diff.max() <= 1e-10),
            "note": "UD profiles are BioVia-restricted (academic, non-commercial); used only locally here",
        }
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sigma-dir", default=str(DEFAULT_SIGMA_DIR))
    parser.add_argument("--engine-dir", default=None)
    parser.add_argument("--cache", default=None)
    args = parser.parse_args()

    sigma_dir = Path(args.sigma_dir)
    engine_dir = Path(args.engine_dir) if args.engine_dir else sigma_dir / "engine" / "COSMOSAC"
    cache = Path(args.cache) if args.cache else sigma_dir / "engine" / "_cache_sanity"

    profiles = PubChemQCProfiles(
        sigma_parquet=sigma_dir / "sigma_profiles_main.parquet",
        index_parquet=sigma_dir / "sigma_profile_index.parquet",
        params_json=sigma_dir / "sequential_final_params.json",
        cache_dir=cache / "profiles",
    )

    results = []

    # 1. water in water -> ln(gamma) = 0
    water = profiles.ln_gamma_inf(WATER_KEY)
    results.append(
        {
            "check": "water_in_water_298.15K",
            "value": water.get("value"),
            "cid": water.get("cid"),
            "pass": bool(water.get("ok") and abs(water["value"]) <= 1e-9),
            "note": "identical profiles: combinatorial and residual terms must cancel exactly",
        }
    )

    # 2. finite values, positive activity coefficient
    rows = []
    for label, key in SOLUTES.items():
        out = profiles.ln_gamma_inf(key)
        rows.append(
            {
                "solute": label,
                "inchikey": key,
                "cid": out.get("cid"),
                "ln_gamma_inf": out.get("value"),
                "finite": bool(out.get("ok")),
                "gamma_positive": bool(out.get("ok") and engine_worked(out.get("value"))),
            }
        )
    results.append(
        {
            "check": "finite_values_298.15K",
            "rows": rows,
            "pass": bool(all(r["finite"] and r["gamma_positive"] for r in rows)),
        }
    )

    # 3. same code path as the NIST example profiles
    check_same_code_path(engine_dir, cache, results)

    print("=" * 78)
    print("COSMO-SAC adapter - label-free sanity checks")
    print("=" * 78)
    for item in results:
        print(f"\n[{ 'PASS' if item['pass'] else 'FAIL' }] {item['check']}")
        if "rows" in item:
            for row in item["rows"]:
                value = row["ln_gamma_inf"]
                shown = "None" if value is None else f"{value:.6f}"
                print(
                    f"    {row['solute']:<12} cid={row['cid']}  ln(gamma_inf)={shown}"
                    f"  finite={row['finite']}  gamma>0={row['gamma_positive']}"
                )
        elif "stock_ln_gamma" in item:
            print(f"    stock  UD path      : {item['stock_ln_gamma']}")
            print(f"    DirectImport path   : {item['direct_import_ln_gamma']}")
            print(f"    max |diff|          : {item['max_abs_diff']:.3e}")
        else:
            print(f"    cid={item.get('cid')}  ln(gamma_inf)={item.get('value')!r}")

    ok = all(item["pass"] for item in results)
    print("\n" + "-" * 78)
    print("RESULT:", "ALL PASS" if ok else "FAILED", f"({sum(i['pass'] for i in results)}/{len(results)})")
    print("=" * 78)
    print(json.dumps(results, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
