"""Unit tests for the PubChemQC adapter logic that do not need the real data.

The real sanity checks (engine, water-water, UD equivalence) live in
tools/cosmosac_sanity.py and need the frozen parquet files plus cCOSMO.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cosmosac_pubchemqc import SIGMA_GRID, PubChemQCProfiles  # noqa: E402

P_COLUMNS = [f"p_{i:03d}" for i in range(153)]


def _write_fixture(tmp_path):
    index = pa.table(
        {
            "CID": [500, 962, 1200, 1300],
            "InChIKey": [
                "XLYOFNOQVPJJNP-UHFFFAOYSA-N",  # 500: charged row, must be skipped
                "XLYOFNOQVPJJNP-UHFFFAOYSA-N",  # 962: neutral, lowest CID -> chosen
                "XLYOFNOQVPJJNP-UHFFFAOYSA-N",  # 1200: neutral, higher CID
                "AAAQKTZKLRYKHR-UHFFFAOYSA-N",  # 1300: only charged rows
            ],
            "SMILES": ["[OH3+]", "O", "O", "[Na+]"],
        }
    )
    pq.write_table(index, tmp_path / "index.parquet")

    rows = []
    for cid in (500, 962, 1200, 1300):
        p = np.zeros(153, dtype=np.float32)
        p[0] = 10.0  # NHB block area
        p[51] = 5.0  # OH block area
        row = {name: None for name in P_COLUMNS}
        row.update(
            {
                "cid": cid,
                "name": f"mol-{cid}",
                "cas": "",
                "area_A2": 15.0,
                "volume_A3": 30.0,
                "disp_flag": "NHB",
                "disp_e_kB": float("nan"),
            }
        )
        row.update({name: float(value) for name, value in zip(P_COLUMNS, p)})
        rows.append(row)
    pq.write_table(pa.Table.from_pylist(rows), tmp_path / "profiles.parquet")

    params = {"final_params": {"A_ES": 1.0, "B_ES": 2.0, "c_OH_OH": 3.0, "c_OH_OT": 4.0, "c_OT_OT": 5.0}}
    (tmp_path / "params.json").write_text(json.dumps(params), encoding="utf-8")

    return PubChemQCProfiles(
        sigma_parquet=tmp_path / "profiles.parquet",
        index_parquet=tmp_path / "index.parquet",
        params_json=tmp_path / "params.json",
        cache_dir=tmp_path / "cache",
    )


def test_pick_one_profile_prefers_neutral_lowest_cid(tmp_path):
    profiles = _write_fixture(tmp_path)
    assert profiles.pick_one_profile("XLYOFNOQVPJJNP-UHFFFAOYSA-N") == 962


def test_pick_one_profile_returns_none_without_neutral_row(tmp_path):
    profiles = _write_fixture(tmp_path)
    assert profiles.pick_one_profile("AAAQKTZKLRYKHR-UHFFFAOYSA-N") is None
    assert profiles.pick_one_profile("NOT-A-KEY-UHFFFAOYSA-N") is None


def test_sigma_grid_is_51_bins():
    assert len(SIGMA_GRID) == 51
    assert SIGMA_GRID[0] == -0.025 and SIGMA_GRID[-1] == 0.025


def test_write_sigma_file_format(tmp_path):
    profiles = _write_fixture(tmp_path)
    path = profiles.write_sigma(962)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 156  # 3 header + 153 data rows
    assert lines[0] == "# Name: mol-962"
    meta = json.loads(lines[2].removeprefix("# meta: "))
    assert meta["disp. e/kB [K]"] is None  # NaN becomes JSON null, as the engine expects
    first = lines[3].split(" ")
    assert len(first) == 2
    assert float(first[0]) == -0.025
    assert float(first[1]) == pytest.approx(10.0)


def test_area_check_rejects_wrong_sums(tmp_path):
    profiles = _write_fixture(tmp_path)
    profiles._load_rows()
    meta_rows, p = profiles._rows
    meta_rows[1] = dict(meta_rows[1])
    meta_rows[1]["area_A2"] = 999.0
    with pytest.raises(ValueError):
        profiles.write_sigma(962)
