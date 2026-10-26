"""Check UNIFAC (and optionally COSMO-SAC) against measured gamma-infinity.

Reference data: Straver & de Loos (2005), J. Chem. Eng. Data 50, 1171-1176,
doi:10.1021/je0495942. Measured at 298 K with water as the solvent; the values
below were transcribed from the NIST/TRC ThermoML record
(https://trc.nist.gov/ThermoML/10.1021/je0495942.html, dataset act record),
replicates are averaged here and the paper's combined uncertainty is kept.

What this can and cannot say:
* it tests the infinite-dilution limit in water only, not the whole composition
  range, not other solvents, not temperature dependence;
* a solute whose group pair is missing from the parameter table is reported as
  REFUSED, never as a number.

Run (inventory environment):
  .venv_inventory\\Scripts\\python.exe tools\\gamma_validation.py
  .venv_inventory\\Scripts\\python.exe tools\\gamma_validation.py --cosmo
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
import sys

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import unifac_gamma  # noqa: E402

METHOD = "UNIFAC from ugropy groups + thermo 0.6.1 matrices; Dortmund is the default"
SOURCE = {
    "citation": "Straver & de Loos 2005, J. Chem. Eng. Data 50, 1171-1176",
    "doi": "10.1021/je0495942",
    "record": "NIST/TRC ThermoML, https://trc.nist.gov/ThermoML/10.1021/je0495942.html",
    "temperature_k": 298.15,
    "solvent": "water",
}

# name, SMILES, measured replicates (gamma-infinity), combined uncertainty
LITERATURE = [
    ("ethanol", "CCO", [3.77], 0.17),
    ("1-propanol", "CCCO", [13.4, 13.3, 13.3, 13.4, 13.3], 0.6),
    ("acetone", "CC(=O)C", [7.62, 7.68, 7.64, 7.70, 7.68, 7.74, 7.70], 0.34),
    ("2-butanone", "CCC(=O)C", [25.8, 26.1], 1.1),
    ("2-pentanone", "CCCC(=O)C", [129.0, 148.0], 6.0),
    ("2-hexanone", "CCCCC(=O)C", [319.0, 265.0], 12.0),
    ("diacetyl", "CC(=O)C(=O)C", [13.3, 13.3, 13.2, 13.2, 13.1, 13.2], 0.6),
    ("dimethyl sulfide", "CSC", [175.0, 173.0, 171.0, 184.0, 185.0, 170.0, 173.0, 178.0], 12.0),
    ("acetaldehyde", "CC=O", [4.08, 4.11, 4.13, 4.18, 4.14], 0.19),
]

TOLERANCE = 0.30  # |prediction/measurement - 1| accepted by the summary gate


def _predict(smiles: str, version: int):
    try:
        return unifac_gamma.gamma_inf([smiles, "O"], version=version)[0]
    except unifac_gamma.MissingInteraction as exc:
        return f"REFUSED ({exc})"
    except unifac_gamma.UnsupportedGroup as exc:
        return f"REFUSED ({exc})"


def _cosmo_profiles():
    """PubChemQC sigma profiles + the cCOSMO build, or None when unavailable."""
    sigma_dir = pathlib.Path(
        __import__("os").environ.get(
            "KURO_SIGMA_DIR", r"C:\KuroshinHQ\_hub\data\formulation_sigma"
        )
    )
    engine = sigma_dir / "engine" / "COSMOSAC"
    builds = sorted(engine.glob("build/*/Release"))
    if not builds:
        return None
    sys.path.insert(0, str(builds[0]))
    sys.path.insert(0, str(engine))
    sys.path.insert(0, str(REPO / "mcp"))
    try:
        from cosmosac_pubchemqc import PubChemQCProfiles  # noqa: PLC0415
    except Exception:
        return None
    return PubChemQCProfiles(
        sigma_parquet=sigma_dir / "sigma_profiles_main.parquet",
        index_parquet=sigma_dir / "sigma_profile_index.parquet",
        params_json=sigma_dir / "sequential_final_params.json",
        cache_dir=sigma_dir / "engine" / "_cache_validation",
    )


def _cosmo_predictions(rows):
    profiles = _cosmo_profiles()
    if profiles is None:
        return {row["name"]: "UNAVAILABLE" for row in rows}
    from rdkit import Chem  # noqa: PLC0415

    out = {}
    for row in rows:
        key = Chem.MolToInchiKey(Chem.MolFromSmiles(row["smiles"]))
        result = profiles.ln_gamma_inf(key)
        if not result.get("ok"):
            out[row["name"]] = f"REFUSED ({result.get('error')})"
            continue
        out[row["name"]] = round(math.exp(float(result["value"])), 3)
    return out


def _error(prediction, measurement):
    if not isinstance(prediction, (int, float)):
        return None
    return prediction / measurement - 1.0


def _cell(value):
    if isinstance(value, (int, float)):
        return f"{value:9.2f}" if value >= 10 else f"{value:9.3f}"
    return f"{str(value)[:28]:>28}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cosmo", action="store_true", help="also run COSMO-SAC")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    rows = []
    for name, smiles, replicates, uncertainty in LITERATURE:
        measured = statistics.fmean(replicates)
        rows.append(
            {
                "name": name,
                "smiles": smiles,
                "measured": round(measured, 4),
                "measured_sd": round(statistics.stdev(replicates), 4)
                if len(replicates) > 1
                else None,
                "uncertainty": uncertainty,
                "n_points": len(replicates),
                "unifac_original": _predict(smiles, 0),
                "unifac_dortmund": _predict(smiles, 1),
            }
        )

    if args.cosmo:
        predictions = _cosmo_predictions(rows)
        for row in rows:
            row["cosmo_sac"] = predictions[row["name"]]

    for row in rows:
        for label in ("unifac_original", "unifac_dortmund", "cosmo_sac"):
            if label in row:
                row[f"{label}_rel_err"] = _error(row[label], row["measured"])

    columns = ["unifac_original", "unifac_dortmund"] + (
        ["cosmo_sac"] if args.cosmo else []
    )
    summary = {}
    for column in columns:
        errors = [row[f"{column}_rel_err"] for row in rows if row.get(f"{column}_rel_err") is not None]
        refused = sum(1 for row in rows if not isinstance(row[column], (int, float)))
        summary[column] = {
            "predicted": len(errors),
            "refused": refused,
            "median_abs_rel_err": round(statistics.median(map(abs, errors)), 3)
            if errors
            else None,
            "max_abs_rel_err": round(max(map(abs, errors)), 3) if errors else None,
            "within_tolerance": sum(1 for error in errors if abs(error) <= TOLERANCE),
        }

    payload = {
        "method": METHOD,
        "source": SOURCE,
        "tolerance": TOLERANCE,
        "rows": rows,
        "summary": summary,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print("=" * 96)
    print("gamma-infinity in water at 298 K - measured (Straver & de Loos 2005) vs models")
    print("=" * 96)
    header = f"{'solute':<18}{'measured':>10}{'sd':>7}{'n':>3}"
    for column in columns:
        header += f"{column:>20}{'err':>9}"
    print(header)
    print("-" * 96)
    for row in rows:
        line = (
            f"{row['name']:<18}{row['measured']:>10.2f}"
            f"{(row['measured_sd'] if row['measured_sd'] is not None else 0):>7.2f}"
            f"{row['n_points']:>3}"
        )
        for column in columns:
            line += f"{_cell(row[column]):>20}"
            error = row.get(f"{column}_rel_err")
            line += f"{'n/a':>9}" if error is None else f"{error * 100:>8.0f}%"
        print(line)
    print("-" * 96)
    for column in columns:
        stats = summary[column]
        print(
            f"{column:<20} median |err| {stats['median_abs_rel_err']:.0%}"
            f"  max {stats['max_abs_rel_err']:.0%}"
            f"  within +/-{TOLERANCE:.0%}: {stats['within_tolerance']}/{stats['predicted']}"
            f"  refused: {stats['refused']}"
        )
    print("=" * 96)
    print("YELLOW: infinite-dilution limit, water only, one temperature, one data source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
