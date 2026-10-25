"""Locked-set evaluation for the solubility sigma plan (v2).

Implements prereg/solubility_sigma_feature_plan_v1.md sections 2, 7, 8, 9 and
clarifications C1-C13 (section 11). Importing this module does no work and reads
no study data; that happens only after `check_guard` passes in `main`.

Guard (all must hold):
  1. git working tree clean
  2. this file's SHA-256 equals tools/solubility_eval_v2.sha256
  3. plan SHA-256 == PLAN_SHA   4. locked SHA-256 == LOCKED_SHA
  5. pool SHA-256 == POOL_SHA   6. CLI has --confirm CALISTIR
One result file is written; a second run refuses.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
PLAN = REPO / "prereg" / "solubility_sigma_feature_plan_v1.md"
POOL = REPO / "data" / "solubility" / "pool_v2.csv"
TUNE = REPO / "data" / "solubility" / "split_tune_v2.csv"
LOCKED = REPO / "data" / "solubility" / "split_locked_v2.csv"
LOCK_IDS = REPO / "data" / "solubility" / "locked_ids.txt"
RAW = REPO / "data" / "solubility" / "raw" / "aqsoldb_20261025.tab"
SELF_SHA_FILE = REPO / "tools" / "solubility_eval_v2.sha256"
SELF = REPO / "tools" / "solubility_eval_v2.py"
RESULT = REPO / "results" / "solubility_sigma_eval_v2.json"

PLAN_SHA = "579dbfa93eaddbdbc1ca20b4380671f47516ba4a675b87f0146fedb80a45214b"
LOCKED_SHA = "6d624855e2e570e12484e7becb69d7522600ee13a14d6a49b1db6dfa6215be0c"
POOL_SHA = "1ba6d5b33e9f9dd5d168f452ab204f74ba1b31fd12f94352851b55e849c51a3f"
CONFIRM_WORD = "CALISTIR"

# C1: published Delaney 2004 coefficients (repo: validation/solubility/plan.md:7-9)
M0_COEF = {"intercept": 0.16, "logp": -0.63, "mw": -0.0062, "rb": 0.066, "ap": -0.74}

# author-fixed numbers, never recomputed here
SEED_SPLIT = 20261027
SEED_BOOT = 20261028
N_BOOT = 10_000
MARGIN = -0.10


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def section15_hashes(plan: Path) -> dict[str, str]:
    """Path -> SHA-256 rows of the section 15 table (read from the plan text)."""
    out = {}
    for line in plan.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "`" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        m_path = re.search(r"`([^`]+)`", cells[0])
        m_sha = re.search(r"\b([0-9a-f]{64})\b", cells[1])
        if m_path and m_sha:
            out[m_path.group(1)] = m_sha.group(1)
    return out


def git_clean(repo: Path = REPO) -> bool:
    out = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    return out.returncode == 0 and out.stdout.strip() == ""


def check_guard(confirm: str | None, *, self_path: Path = SELF,
                plan: Path = PLAN, locked: Path = LOCKED, pool: Path = POOL,
                sha_file: Path = SELF_SHA_FILE, repo: Path = REPO,
                expected: dict | None = None) -> None:
    """Raise RuntimeError unless every real-run condition holds."""
    exp = {"plan": PLAN_SHA, "locked": LOCKED_SHA, "pool": POOL_SHA}
    if expected:
        exp.update(expected)
    problems = []
    if confirm != CONFIRM_WORD:
        problems.append(f"missing --confirm {CONFIRM_WORD}")
    if not git_clean(repo):
        problems.append("git working tree not clean")
    if not sha_file.exists():
        problems.append(f"missing {sha_file.name}")
    else:
        pinned = sha_file.read_text(encoding="utf-8").split()[0].strip().lower()
        actual = sha256_file(self_path)
        if pinned != actual:
            problems.append(f"script SHA-256 mismatch ({actual} != pinned {pinned})")
    for key, path in (("plan", plan), ("locked", locked), ("pool", pool)):
        if not path.exists():
            problems.append(f"{key} file missing: {path}")
        elif sha256_file(path) != exp[key]:
            problems.append(f"{key} SHA-256 mismatch")
    for rel, want in section15_hashes(plan).items():
        target = repo / rel
        if not target.exists():
            problems.append(f"section 15 file missing: {rel}")
        elif sha256_file(target) != want:
            problems.append(f"section 15 SHA-256 mismatch: {rel}")
    if problems:
        raise RuntimeError("guard refused: " + "; ".join(problems))


def engine_worked(ln_gamma) -> bool:
    """Clarification C14: worked = ln gamma finite AND exp(ln gamma) finite.

    gamma = exp(.) is positive by construction, so "negative activity coefficient"
    (section 6) cannot occur; the finite checks are the operative ones. Negative
    ln gamma is normal and is not a failure.
    """
    if ln_gamma is None:
        return False
    try:
        x = float(ln_gamma)
    except (TypeError, ValueError):
        return False
    if not np.isfinite(x):
        return False
    with np.errstate(over="ignore"):
        gamma = float(np.exp(x))
    return bool(np.isfinite(gamma))


def descriptors_from_smiles(smiles: str) -> dict:
    """ESOL descriptors (section 4) + TPSA (section 2). C5: NaN -> error."""
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit cannot parse SMILES: {smiles!r}")
    heavy = mol.GetNumHeavyAtoms()
    aromatic = sum(1 for a in mol.GetAtoms() if a.GetIsAromatic())
    row = {
        "logp": float(Crippen.MolLogP(mol)),
        "mw": float(Descriptors.MolWt(mol)),
        "rb": float(rdMolDescriptors.CalcNumRotatableBonds(mol)),
        "ap": float(aromatic) / float(heavy) if heavy else float("nan"),
        "tpsa": float(rdMolDescriptors.CalcTPSA(mol)),
    }
    bad = [k for k, v in row.items() if not np.isfinite(v)]
    if bad:
        raise ValueError(f"non-finite RDKit feature(s) {bad} for {smiles!r}")
    return row


ESOL_COLS = ("logp", "mw", "rb", "ap")


def design_matrix(rows, extra=None) -> np.ndarray:
    """Intercept always first (C2); raw features, no scaling (C3)."""
    cols = [np.ones(len(rows))]
    for name in ESOL_COLS:
        cols.append(np.asarray([r[name] for r in rows], dtype=float))
    if extra is not None:
        cols.append(np.asarray(extra, dtype=float))
    return np.column_stack(cols)


def fit_ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """C4: numpy.linalg.lstsq; rank deficiency stops the run, never silent."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    if X.shape[0] <= X.shape[1]:
        raise ValueError(f"underdetermined fit: {X.shape[0]} rows, {X.shape[1]} cols")
    beta, _res, rank, _sv = np.linalg.lstsq(X, y, rcond=None)
    if rank < X.shape[1]:
        raise ValueError(f"rank deficient fit: rank {rank} < {X.shape[1]} columns")
    if not np.all(np.isfinite(beta)):
        raise ValueError("non-finite OLS coefficients")
    return beta


def rmse(y, p) -> float:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    return float(np.sqrt(np.mean((y - p) ** 2)))


def mae(y, p) -> float:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    return float(np.mean(np.abs(y - p)))


def classify(diff: float, lo: float, hi: float) -> str:
    """Section 8 decision rule with the author's margin (-0.10)."""
    if diff <= MARGIN and hi < 0.0:
        return "SUCCESS"
    if lo > MARGIN:
        return "NO GAIN"
    return "INCONCLUSIVE"


def paired_bootstrap_diff(y, p2, p3, n_boot: int = N_BOOT, seed: int = SEED_BOOT):
    """C7-C9: no refit; same resampled indices for both models; statistic
    RMSE(M2) - RMSE(M3); percentile CI 2.5/97.5 (C8)."""
    y = np.asarray(y, dtype=float)
    p2 = np.asarray(p2, dtype=float)
    p3 = np.asarray(p3, dtype=float)
    if not (y.shape == p2.shape == p3.shape):
        raise ValueError("y, p2, p3 must have the same shape")
    n = y.shape[0]
    if n < 2:
        raise ValueError("need at least 2 molecules")
    observed = rmse(y, p2) - rmse(y, p3)
    rng = np.random.default_rng(seed)
    stats = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)          # same indices for both models
        yy = y[idx]
        stats[i] = rmse(yy, p2[idx]) - rmse(yy, p3[idx])
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return {"diff": float(observed), "ci_low": float(lo), "ci_high": float(hi),
            "n_boot": int(n_boot), "seed": int(seed), "n": int(n)}


def m0_predict(rows) -> np.ndarray:
    """C1: published coefficients, never refit."""
    return np.asarray([
        M0_COEF["intercept"] + M0_COEF["logp"] * r["logp"] + M0_COEF["mw"] * r["mw"]
        + M0_COEF["rb"] * r["rb"] + M0_COEF["ap"] * r["ap"]
        for r in rows
    ], dtype=float)


def fit_all(tune_rows, ln_gamma) -> dict:
    """M1/M2/M3 fitted once on the engine-worked tune rows (C13, section 7:119)."""
    y = np.asarray([r["logS"] for r in tune_rows], dtype=float)
    X1 = design_matrix(tune_rows)
    return {
        "M1": fit_ols(X1, y),
        "M2": fit_ols(design_matrix(tune_rows, extra=ln_gamma), y),
        "M3": fit_ols(design_matrix(tune_rows, extra=[r["tpsa"] for r in tune_rows]), y),
    }


def predict_all(betas, rows, ln_gamma, worked, fallback_m2: bool = False) -> dict:
    """Predictions for M0-M3. With fallback_m2, M2 uses M1 where the engine failed
    (secondary analysis, section 6/7)."""
    X1 = design_matrix(rows)
    extra = list(ln_gamma)
    if fallback_m2:
        worked_arr = np.asarray(worked, dtype=bool)
        # A failed molecule carries no ln gamma. To build X2 for every row, such
        # entries get a placeholder (0.0); it can never reach a reported number
        # because M2 falls back to M1 exactly where worked is False.
        extra = [0.0 if (not w or v is None) else float(v)
                 for v, w in zip(extra, worked_arr)]
    elif any(v is None for v in extra):
        raise ValueError("engine failure without fallback: primary set must be filtered")
    X2 = design_matrix(rows, extra=extra)
    X3 = design_matrix(rows, extra=[r["tpsa"] for r in rows])
    out = {
        "M0": m0_predict(rows),
        "M1": X1 @ betas["M1"],
        "M2": X2 @ betas["M2"],
        "M3": X3 @ betas["M3"],
    }
    if fallback_m2:
        worked = np.asarray(worked, dtype=bool)
        out["M2"] = np.where(worked, out["M2"], out["M1"])
    return out


def summarize(y, preds) -> dict:
    """Section 8 output: RMSE primary, MAE secondary, per model."""
    return {name: {"rmse": rmse(y, p), "mae": mae(y, p), "n": int(len(y))}
            for name, p in preds.items()}


def analyze_all(tune_rows, locked_rows, tune_ln, locked_ln, overlap_keys=()) -> dict:
    """Everything the report needs. Pure function: no I/O, no printing."""
    worked_tune = [engine_worked(v) for v in tune_ln]
    train = [r for r, w in zip(tune_rows, worked_tune) if w]
    train_ln = [v for v, w in zip(tune_ln, worked_tune) if w]
    if len(train) <= 5:
        raise ValueError("too few engine-worked tune molecules")
    betas = fit_all(train, train_ln)

    worked_locked = [engine_worked(v) for v in locked_ln]
    y_lock = [r["logS"] for r in locked_rows]

    prim_rows = [r for r, w in zip(locked_rows, worked_locked) if w]
    prim_ln = [v for v, w in zip(locked_ln, worked_locked) if w]
    prim_pred = predict_all(betas, prim_rows, prim_ln, [True] * len(prim_rows))
    y_prim = [r["logS"] for r in prim_rows]
    boot = paired_bootstrap_diff(y_prim, prim_pred["M2"], prim_pred["M3"])
    boot["outcome"] = classify(boot["diff"], boot["ci_low"], boot["ci_high"])

    # secondary: all in-domain, M2 falls back to M1 where the engine failed
    sec_pred = predict_all(betas, locked_rows, locked_ln, worked_locked, fallback_m2=True)

    # exploratory: same models, evaluation set without the earlier-ESOL overlap
    keep = [k not in set(overlap_keys) for k in (r["inchikey"] for r in prim_rows)]
    ex_rows = [r for r, k in zip(prim_rows, keep) if k]
    ex_ln = [v for v, k in zip(prim_ln, keep) if k]
    ex_pred = predict_all(betas, ex_rows, ex_ln, [True] * len(ex_rows))
    ex_boot = paired_bootstrap_diff([r["logS"] for r in ex_rows], ex_pred["M2"], ex_pred["M3"])

    return {
        "counts": {
            "tune_rows": len(tune_rows), "tune_engine_worked": len(train),
            "locked_rows": len(locked_rows), "locked_engine_worked": len(prim_rows),
            "engine_failures_locked": len(locked_rows) - len(prim_rows),
            "exploratory_rows": len(ex_rows), "overlap_removed": len(prim_rows) - len(ex_rows),
        },
        "primary": {"metrics": summarize(y_prim, prim_pred), "bootstrap": boot,
                    "clusters": len(set(r["inchikey"] for r in prim_rows))},
        "secondary": {"metrics": summarize(y_lock, sec_pred)},
        "exploratory": {"label": "EXPLORATORY", "metrics": summarize([r["logS"] for r in ex_rows], ex_pred),
                        "bootstrap": {**ex_boot, "outcome": classify(ex_boot["diff"], ex_boot["ci_low"], ex_boot["ci_high"])}},
        "betas": {k: [float(x) for x in v] for k, v in betas.items()},
    }


# ---- real-data layer: reached only after the guard passes -------------------

def load_split(path: Path) -> list[dict]:
    """inchikey, smiles, logS + RDKit features. Called after the guard only."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = descriptors_from_smiles(r["smiles"])
            d.update(inchikey=r["inchikey"], smiles=r["smiles"], logS=float(r["logS"]))
            rows.append(d)
    return rows


ENGINE_TEMPERATURE_K = 298.15
"""Plan section 3: ln(gamma-infinity) of the solute in water at 298.15 K.

The solvent is fixed inside the adapter (water CID 962, mole fraction 1e-12
solute); the temperature is passed explicitly here so the call site fixes both.
"""


def engine_series(rows, profiles, temperature: float = ENGINE_TEMPERATURE_K) -> list:
    """ln gamma-infinity per molecule via the committed adapter (no fitting).

    Returns one float per row, or None when that molecule failed:
      * the adapter raised (any per-molecule error) -> None, run continues;
      * the adapter reported out-of-domain (no neutral sigma row, no value)
        -> None;
      * otherwise the adapter's dict payload is unwrapped to its ``value``.
    None is an engine failure under clarification C14, never an exception.
    """
    out = []
    for r in rows:
        try:
            res = profiles.ln_gamma_inf(r["inchikey"], temperature=temperature)
        except Exception:
            out.append(None)
            continue
        if isinstance(res, dict):
            out.append(res.get("value"))       # absent for out-of-domain rows
        else:
            out.append(res)
    return out


def overlap_keys(locked_ids: Path = LOCK_IDS, raw: Path = RAW) -> set[str]:
    """ESOL locked IDs -> InChIKey, ID and InChIKey columns only.

    csv.reader + the two header indices: the Solubility column never enters a
    dict, so no label value is materialized, read or compared here.
    """
    ids = {ln.strip() for ln in locked_ids.read_text(encoding="utf-8").splitlines() if ln.strip()}
    keys = set()
    with open(raw, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        i_id, i_key = header.index("ID"), header.index("InChIKey")
        for row in reader:
            if row[i_id] in ids:
                keys.add(row[i_key])
    return keys


def column_values(path: Path, column: str, delimiter: str = ",") -> list[str]:
    """One column of a delimited file; the other columns are never stored."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=delimiter)
        header = next(reader)
        idx = header.index(column)
        return [row[idx] for row in reader]


def integrity_check(tune_rows, locked_rows, pool_path: Path = POOL) -> None:
    """Label-free identity check (no label column is opened here).

    The tune file has no hash in the guard, so this closes that gap: tune and
    locked must be disjoint and their union must be exactly the pool.
    """
    t = {r["inchikey"] for r in tune_rows}
    l = {r["inchikey"] for r in locked_rows}
    if t & l:
        raise ValueError(f"integrity: tune/locked overlap: {len(t & l)} InChIKey(s)")
    p = set(column_values(pool_path, "inchikey"))
    if (t | l) != p:
        raise ValueError(
            "integrity: tune+locked != pool "
            f"({len(p - (t | l))} pool molecule(s) missing from the split, "
            f"{len((t | l) - p)} split molecule(s) not in the pool)"
        )


SIGMA_DIR = Path(r"C:\KuroshinHQ\_hub\data\formulation_sigma")
ENGINE_DIR = SIGMA_DIR / "engine" / "COSMOSAC"
ADAPTER = REPO / "mcp" / "cosmosac_pubchemqc.py"
SPLIT_SCRIPT = REPO / "data" / "solubility" / "make_split_v2.py"


def git_head(path: Path) -> str | None:
    """HEAD commit of an arbitrary git checkout, or None when unavailable."""
    out = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=False)
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def ccosmo_version() -> str | None:
    """Installed cCOSMO distribution version, or None when not installed."""
    try:
        from importlib.metadata import PackageNotFoundError, version
        return version("cCOSMO")
    except PackageNotFoundError:
        return None


def make_profiles(cache_dir: Path | None = None):
    """Construct the committed adapter exactly as the real run uses it.

    Single construction point: `main()` and `tools/smoke_engine_series.py` both
    call this, so the smoke test exercises the real import path and the real
    argument set (the repo's mcp/ dir is not a package and the venv ships the
    official `mcp` SDK, hence the sys.path entry below).
    """
    if str(REPO / "mcp") not in sys.path:
        sys.path.insert(0, str(REPO / "mcp"))
    from cosmosac_pubchemqc import PubChemQCProfiles

    return PubChemQCProfiles(
        sigma_parquet=SIGMA_DIR / "sigma_profiles_main.parquet",
        index_parquet=SIGMA_DIR / "sigma_profile_index.parquet",
        params_json=SIGMA_DIR / "sequential_final_params.json",
        cache_dir=cache_dir or (SIGMA_DIR / "engine" / "_cache_eval"),
    )


def assert_writable(out: Path) -> None:
    """One evaluation only: never overwrite or append to an existing result."""
    if out.exists():
        raise RuntimeError(f"result file already exists (one evaluation only): {out}")



def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="locked-set evaluation (one run only)")
    ap.add_argument("--confirm", default=None, help=f"must be {CONFIRM_WORD}")
    ap.add_argument("--out", default=str(RESULT))
    args = ap.parse_args(argv)
    out = Path(args.out)

    check_guard(args.confirm)              # everything below is real data
    assert_writable(out)

    profiles = make_profiles()               # same constructor as the smoke test
    tune, locked = load_split(TUNE), load_split(LOCKED)
    integrity_check(tune, locked)            # label-free, closes the tune-hash gap
    report = analyze_all(tune, locked, engine_series(tune, profiles),
                         engine_series(locked, profiles), overlap_keys())
    report["provenance"] = {
        "plan_sha256": PLAN_SHA, "locked_sha256": LOCKED_SHA, "pool_sha256": POOL_SHA,
        "script_sha256": sha256_file(SELF), "seeds": {"split": SEED_SPLIT, "bootstrap": SEED_BOOT},
        "n_boot": N_BOOT, "margin": MARGIN, "engine_failures_are_not_exclusions": True,
        # read at run time (never hardcoded): section 15 code + engine provenance
        "adapter_sha256": sha256_file(ADAPTER),
        "split_script_sha256": sha256_file(SPLIT_SCRIPT),
        "engine_commit": git_head(ENGINE_DIR),
        "ccosmo_version": ccosmo_version(),
        "temperature_K": ENGINE_TEMPERATURE_K,
        "solvent": "water (CID 962), mole fraction 1e-12 solute",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"written: {out} sha256={sha256_file(out)}")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
















