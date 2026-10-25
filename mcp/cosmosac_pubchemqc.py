"""COSMO-SAC adapter: PubChemQC sigma profiles -> NIST cCOSMO (DirectImport).

Frozen components (prereg/solubility_sigma_feature_plan_v1.md, section 3):
  engine   usnistgov/COSMOSAC @ 1b82456be38026719b16cad4076109bef3fcb309 (2026-07-03)
           built as cCOSMO 1.0.3, method COSMOSAC-2010 (COSMO3): ln(gamma) = comb + resid
  data     sigma_profiles_main.parquet, sigma_profile_index.parquet,
           sequential_final_params.json (SHA-256 recorded in the plan)
  feature  ln(gamma-infinity) of the solute in water at 298.15 K

The engine is NOT modified. Profiles are written in the engine's documented
`DirectImport` text format (51 sigma bins x 3 blocks: NHB, OH, OT) and read by
stock cCOSMO code. `DirectImport` is C++ and cannot be subclassed from Python,
so the adapter is a data bridge + constant loader around it.

No solubility label is read anywhere in this module.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from rdkit import Chem

__all__ = [
    "SIGMA_GRID",
    "WATER_CID",
    "WATER_KEY",
    "PubChemQCProfiles",
    "engine_worked",
]

# 51 sigma bins, -0.025 .. +0.025 e/A^2, step 0.001 (dataset README, Zenodo 20672192)
SIGMA_GRID = tuple(round(-0.025 + 0.001 * i, 6) for i in range(51))
N_BINS = len(SIGMA_GRID)
N_BLOCKS = 3
N_ROWS = N_BINS * N_BLOCKS  # 153
WATER_CID = 962
WATER_KEY = "XLYOFNOQVPJJNP-UHFFFAOYSA-N"

_P_COLUMNS = [f"p_{i:03d}" for i in range(N_ROWS)]
_META_COLUMNS = ["cid", "name", "cas", "area_A2", "volume_A3", "disp_flag", "disp_e_kB"]


def _formal_charge(smiles):
    """Sum of formal charges, or None when RDKit cannot parse the SMILES."""
    if not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return sum(atom.GetFormalCharge() for atom in mol.GetAtoms())


def engine_worked(ln_gamma):
    """Plan section 6: finite number and no physically impossible value."""
    if ln_gamma is None:
        return False
    value = float(ln_gamma)
    if not np.isfinite(value):
        return False
    return float(np.exp(value)) > 0.0


class PubChemQCProfiles:
    """One-profile-per-molecule resolver + DirectImport bridge.

    Parameters
    ----------
    sigma_parquet, index_parquet, params_json : path to the frozen PubChemQC files
    cache_dir : directory where the engine-format ``<cid>.sigma`` files are written
    """

    def __init__(self, sigma_parquet, index_parquet, params_json, cache_dir):
        self.sigma_parquet = Path(sigma_parquet)
        self.index_parquet = Path(index_parquet)
        self.params_json = Path(params_json)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.params = json.loads(self.params_json.read_text(encoding="utf-8"))
        self._index = None          # InChIKey -> [(cid, smiles), ...] in file order
        self._chosen = {}           # InChIKey -> cid or None
        self._rows = None           # cid -> dict of metadata + p array
        self._pos = None            # cid -> row position

    # ------------------------------------------------------------------ index
    def _load_index(self):
        if self._index is not None:
            return
        table = pq.read_table(self.index_parquet, columns=["CID", "InChIKey", "SMILES"])
        cids = table["CID"].to_pylist()
        keys = table["InChIKey"].to_pylist()
        smiles = table["SMILES"].to_pylist()
        index = {}
        for cid, key, smi in zip(cids, keys, smiles):
            if not key:
                continue
            index.setdefault(key, []).append((cid, smi))
        self._index = index

    def matched_rows(self, inchikey):
        """All sigma-DB rows for a full 27-character InChIKey (file order)."""
        self._load_index()
        return list(self._index.get(inchikey, []))

    def pick_one_profile(self, inchikey):
        """Plan section 5: neutral rows only, lowest CID, tie = lowest file row.

        Returns the CID, or None when the key is absent / has no neutral row
        (molecule is out of domain).
        """
        if inchikey in self._chosen:
            return self._chosen[inchikey]
        rows = self.matched_rows(inchikey)
        neutral = [
            (cid, order)
            for order, (cid, smi) in enumerate(rows)
            if _formal_charge(smi) == 0
        ]
        cid = min(neutral, key=lambda item: (item[0], item[1]))[0] if neutral else None
        self._chosen[inchikey] = cid
        return cid

    # ---------------------------------------------------------------- profiles
    def _load_rows(self):
        if self._rows is not None:
            return
        table = pq.read_table(
            self.sigma_parquet,
            columns=_META_COLUMNS + _P_COLUMNS,
        )
        cids = table["cid"].to_numpy()
        p = np.stack(
            [table[name].to_numpy(zero_copy_only=False) for name in _P_COLUMNS],
            axis=1,
        )
        meta = table.select(_META_COLUMNS).to_pylist()
        self._pos = {int(cid): i for i, cid in enumerate(cids)}
        self._rows = (meta, p)

    def profile(self, cid):
        """Metadata + A-weighted psigma array (length 153) for one CID."""
        self._load_rows()
        meta_rows, p = self._rows
        try:
            i = self._pos[int(cid)]
        except KeyError:
            raise KeyError(f"CID {cid} is not in {self.sigma_parquet.name}") from None
        row = dict(meta_rows[i])
        row["p"] = p[i].astype(float)
        return row

    def write_sigma(self, cid):
        """Write the engine-format ``<cid>.sigma`` file and return its path."""
        path = self.cache_dir / f"{cid}.sigma"
        if path.exists():
            return path
        row = self.profile(cid)
        p = row["p"]
        area = float(row["area_A2"])
        total = float(p.sum())
        if not np.isclose(total, area, rtol=1e-4, atol=1e-3):
            raise ValueError(
                f"area check failed for CID {cid}: sum(psigmaA)={total!r} != area_A2={area!r}"
            )
        disp_e = row["disp_e_kB"]
        meta = {
            "volume [A^3]": float(row["volume_A3"]),
            "disp. flag": row["disp_flag"],
            "disp. e/kB [K]": None if disp_e is None or not np.isfinite(disp_e) else float(disp_e),
        }
        lines = [
            f"# Name: {row['name']}",
            f"# CASn: {row['cas']}",
            "# meta: " + json.dumps(meta),
        ]
        for i in range(N_ROWS):
            lines.append(f"{SIGMA_GRID[i % N_BINS]:.6f} {p[i]:.10e}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        return path

    # ----------------------------------------------------------------- engine
    def model(self, cids, use_refit=True):
        """cCOSMO.COSMO3 for the given CIDs (order matters: index 0 = solute)."""
        import cCOSMO

        db = cCOSMO.DirectImport()
        for cid in cids:
            self.write_sigma(int(cid))
            db.add_profile(str(int(cid)), str(self.cache_dir))
        cosmo = cCOSMO.COSMO3([str(int(cid)) for cid in cids], db)
        if use_refit:
            constants = cosmo.get_mutable_COSMO_constants()
            for name, value in self.params["final_params"].items():
                setattr(constants, name, float(value))
        return cosmo

    def ln_gamma_inf(self, inchikey, temperature=298.15, mole_fraction=1e-12):
        """ln(gamma-infinity) of the solute in water, plan section 3 call."""
        cid = self.pick_one_profile(inchikey)
        if cid is None:
            return {
                "ok": False,
                "error": "no sigma-DB row with formal charge 0 (out of domain)",
                "inchikey": inchikey,
            }
        cosmo = self.model([cid, WATER_CID])
        composition = np.array([mole_fraction, 1.0 - mole_fraction], dtype=float)
        comb = float(cosmo.get_lngamma_comb(temperature, composition)[0])
        resid = float(cosmo.get_lngamma_resid(temperature, composition)[0])
        value = comb + resid
        return {
            "ok": engine_worked(value),
            "value": value,
            "comb": comb,
            "resid": resid,
            "cid": int(cid),
            "water_cid": WATER_CID,
            "temperature_K": float(temperature),
            "unit": "ln(gamma-infinity)",
            "method": "NIST cCOSMO COSMO3 (COSMOSAC-2010), comb+resid; PubChemQC refit constants",
        }
