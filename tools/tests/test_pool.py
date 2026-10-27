"""S2 tests: the candidate pool is sourced, licensed and engine-consistent.

Acceptance for S2 (docs/ROADMAP_20261027.md): "havuz sayimi + lisans satiri".
The pool is a generated artefact, so the tests check three things the builder
could get wrong: a count that does not match the rows, a missing licence line,
and numbers that disagree with the engine that will consume them.
"""
import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

pytest.importorskip("chemicals")

ROOT = pathlib.Path(__file__).resolve().parents[2]
POOL = ROOT / "data" / "pool"
NAMES = ("hsp", "melting", "alloy_phases")


def load(name):
    return json.loads((POOL / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", NAMES)
def test_every_pool_carries_source_licence_and_a_true_count(name):
    pool = load(name)
    assert pool["schema"] == "kj-pool/1"
    assert pool["source"] and pool["licence"] and pool["role"]
    assert pool["count"] == len(pool["entries"]) > 0
    assert all(entry.get("casrn") or entry.get("database") for entry in pool["entries"])


def test_index_matches_every_file():
    index = load("index")
    assert set(index["pools"]) == set(NAMES)
    for name, item in index["pools"].items():
        pool = load(name)
        raw = (POOL / f"{name}.json").read_bytes()
        assert item["file"] == f"data/pool/{name}.json"
        assert item["count"] == pool["count"]
        assert item["licence"] == pool["licence"]
        assert item["bytes"] == len(raw)
        assert item["sha256"] == hashlib.sha256(raw).hexdigest()
    assert "calibration.json" in index["ranking"]


def test_hsp_pool_numbers_are_the_engine_numbers():
    """The pool must not carry a second opinion: hsp_lookup divides by 1000 and
    rounds to two decimals, so the pool does exactly the same."""
    from chemicals import hansen_delta_d, hansen_delta_h, hansen_delta_p

    entries = load("hsp")["entries"]
    for entry in entries[:25] + entries[-25:]:
        casrn = entry["casrn"]
        assert entry["delta_d"] == round(hansen_delta_d(casrn) / 1000.0, 2)
        assert entry["delta_p"] == round(hansen_delta_p(casrn) / 1000.0, 2)
        assert entry["delta_h"] == round(hansen_delta_h(casrn) / 1000.0, 2)


def test_hsp_pool_is_unique_and_inside_plausible_ranges():
    entries = load("hsp")["entries"]
    casrns = [entry["casrn"] for entry in entries]
    assert len(casrns) == len(set(casrns))
    for entry in entries:
        assert 10.0 <= entry["delta_d"] <= 30.0, entry
        assert 0.0 <= entry["delta_p"] <= 50.0, entry
        assert 0.0 <= entry["delta_h"] <= 60.0, entry
        assert entry["unit"] == "MPa^0.5"
        assert entry["method"]
    assert any(entry.get("smiles") for entry in entries)


def test_melting_pool_is_complete_and_the_mixtures_are_recorded():
    pool = load("melting")
    assert pool["count"] >= 12
    for entry in pool["entries"]:
        assert 100.0 <= entry["tm_k"] <= 500.0, entry
        assert 1000.0 <= entry["hfus_j_mol"] <= 120000.0, entry
        assert entry["group"] in {"n-alkane", "fatty acid", "fatty alcohol"}
    skipped = {item["casrn"]: item for item in pool["skipped"]}
    assert set(skipped) == {"8002-74-2", "8009-03-8"}
    assert all("Hfus missing" in item["reason"] for item in skipped.values())
    assert pool["curated_cas"] == pool["count"] + len(pool["skipped"])


def test_melting_names_are_the_canonical_chemicals_names():
    """S5 found two curated labels off by one carbon; the canonical name wins."""
    from chemicals import search_chemical

    for entry in load("melting")["entries"]:
        assert entry["name"] == search_chemical(entry["casrn"]).common_name, entry["casrn"]
        assert entry["curated_name"]


def test_alloy_pool_points_at_the_databases_and_keeps_no_coefficients():
    pool = load("alloy_phases")
    assert pool["count"] == 3
    for entry in pool["entries"]:
        path = ROOT / entry["path"]
        assert path.is_file()
        assert entry["bytes"] == path.stat().st_size
        assert entry["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert entry["element_count"] == len(entry["elements"]) > 0
        assert entry["phase_count"] == len(entry["phases"]) > 0
        assert "VA" not in entry["elements"]
        assert "LIQUID" in entry["phases"]
        assert entry["licence"] == "ODbL-1.0 + DbCL-1.0"
    aluminium = next(entry for entry in pool["entries"] if entry["database"] == "mc_al")
    assert {"AL", "CU"} <= set(aluminium["elements"])
    assert {"FCC_A1", "LIQUID"} <= set(aluminium["phases"])


def test_builder_check_reports_no_drift():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_pool.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK:" in result.stdout
