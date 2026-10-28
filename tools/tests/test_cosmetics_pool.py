"""S4 tests: the cosmetics pool is sourced, licensed and refuses formulations.

Acceptance for S4 (docs/ROADMAP_20261027.md): "kaynak + lisans karari" and a
`DATA_INVENTORY.md` row. The pool is generated from two external files, so the
tests check what the builder could get wrong: a count that does not match the
rows, a missing licence, a name that is not really in CosIng, and the boundary
("formulation" is a permanent RED, not a feature request).
"""
import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import cosmetics_sources as S  # noqa: E402

POOL = ROOT / "data" / "cosmetics" / "cosmetics.json"
INDEX = ROOT / "data" / "cosmetics" / "index.json"
DOC = ROOT / "docs" / "COSMETICS_DATASET.md"
MANIFEST = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))


def load():
    return json.loads(POOL.read_text(encoding="utf-8"))


def test_pool_file_matches_its_index():
    pool, index = load(), json.loads(INDEX.read_text(encoding="utf-8"))
    row = index["pools"]["cosmetics"]
    payload = POOL.read_bytes()
    assert row["bytes"] == len(payload)
    assert row["sha256"] == hashlib.sha256(payload).hexdigest()
    assert row["count"] == pool["count"]


def test_count_and_order_are_internally_consistent():
    pool = load()
    entries = pool["entries"]
    assert pool["count"] == len(entries)
    assert entries, "an empty pool is not a dataset"
    threshold = pool["thresholds"]["min_products"]
    assert all(row["products"] >= threshold for row in entries)
    keys = [(-row["products"], row["inci"]) for row in entries]
    assert keys == sorted(keys)
    assert pool["coverage"]["matched_cosing"] == len(entries)


def test_every_entry_has_a_cosing_identity():
    entries = load()["entries"]
    for row in entries:
        cosing = row["cosing"]
        assert cosing["inci"], row["inci"]
        # six CosIng records carry no status field; it is not invented
        assert cosing["status"] in {None, "Active", "Inactive", "proposed"}, row["inci"]
        assert cosing["item_type"] in {"ingredient", "substance"}, row["inci"]
    with_status = sum(1 for row in entries if row["cosing"]["status"])
    assert with_status / len(entries) > 0.99
    with_functions = sum(1 for row in entries if row["cosing"]["functions"])
    assert with_functions / len(entries) > 0.95


def test_licences_and_sources_are_stated():
    pool = load()
    assert pool["sources"]["obf"]["licence"] == "ODbL-1.0 + DbCL-1.0"
    assert pool["sources"]["cosing"]["licence"] == "CC-BY-4.0"
    for source in ("obf", "cosing"):
        assert len(pool["sources"][source]["sha256"]) == 64
        assert pool["sources"][source]["attribution"]
    assert "CC-BY-4.0" in MANIFEST["allowed_licences"]
    assert "ODbL-1.0 + DbCL-1.0" in MANIFEST["allowed_licences"]
    ids = {row["id"] for row in MANIFEST["datasets"]}
    assert {"obf_products_20261028", "cosing_labels_20261028"} <= ids


def test_pool_refuses_formulations_and_claims():
    pool = load()
    assert any("formulation" in item for item in pool["not_for"])
    assert "never a formulation" in pool["role"]
    row_fields = {"inci", "products", "brands", "cosing"}
    cosing_fields = {"inci", "cas", "ec", "functions", "status", "item_type",
                     "restricted", "restriction", "annex", "max_concentration"}
    for row in pool["entries"]:
        assert set(row) == row_fields, row["inci"]
        assert set(row["cosing"]) == cosing_fields, row["inci"]


def test_docs_state_the_boundary():
    text = DOC.read_text(encoding="utf-8")
    assert "CC-BY-4.0" in text and "ODbL" in text
    assert "formulation" in text.lower()
    assert "permanent RED" in text or "kalici RED" in text


def test_lookup_cli_answers_and_refuses():
    top = subprocess.run([sys.executable, str(ROOT / "tools" / "cosmetics_lookup.py"), "--top", "3"],
                         capture_output=True, text=True, cwd=ROOT)
    assert top.returncode == 0, top.stderr
    assert len(top.stdout.strip().splitlines()) == 3
    one = subprocess.run([sys.executable, str(ROOT / "tools" / "cosmetics_lookup.py"), "glycerin"],
                         capture_output=True, text=True, cwd=ROOT)
    assert one.returncode == 0, one.stderr
    assert "GLYCERIN" in one.stdout
    missing = subprocess.run([sys.executable, str(ROOT / "tools" / "cosmetics_lookup.py"),
                              "not-an-inci-name"], capture_output=True, text=True, cwd=ROOT)
    assert missing.returncode == 1


def test_tokeniser_keeps_names_whole():
    assert S.split_inci("Aqua, 1,2-Hexanediol, Parfum") == ["Aqua", " 1,2-Hexanediol", " Parfum"]
    assert S.normalise("Caprylic/Capric Triglyceride") == "CAPRYLIC/CAPRIC TRIGLYCERIDE"
    assert S.normalise("Aqua (Water)") == "AQUA"
    assert S.normalise("INGREDIENTS") == ""
    assert S.normalise("Linalool.") == "LINALOOL"
    assert S.normalise("Butyrospermum Parkii (Shea) Butter") == "BUTYROSPERMUM PARKII BUTTER"
    assert S.normalise("Aqua/Water/Eau") == "AQUA"
    assert S.normalise("Fragrance") == "PARFUM"
    assert S.match_key("Alcohol Denat.") == "ALCOHOL DENAT"
    product = {"ingredients_text": "Ingredients: Aqua, Glycerin, Parfum",
               "ingredients": [{"text": "Aqua"}, {"text": "Glycerin"}]}
    assert S.product_tokens(product) == ["AQUA", "GLYCERIN", "PARFUM"]


@pytest.mark.skipif(not (S.RAW_DIR / S.OBF_NAME).is_file() or not S.cosing_files(),
                    reason="raw S4 sources stay outside the repository")
def test_build_is_reproducible():
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "build_cosmetics.py"), "--check"],
                            capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
