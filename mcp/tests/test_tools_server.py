"""Tests for mcp/tools_server.py (CALPHAD + Hansen).

The bench environment (``.venv``) does not carry pycalphad or chemicals, so the
whole module is skipped there. Run it with the inventory environment:

    .venv_inventory\\Scripts\\python.exe -m pytest mcp\\tests\\test_tools_server.py -q

The CALPHAD test reads the MatCalc database from ``KJ_TDB_DIR``; when that folder
is absent the test is skipped instead of failing.
"""
import os
import pathlib
import sys

import pytest

pytest.importorskip("pycalphad")
pytest.importorskip("chemicals")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import tools_server as T  # noqa: E402

TDB_DIR = pathlib.Path(os.environ.get("KJ_TDB_DIR", r"C:\KuroshinHQ\_hub\data\alloy_tdb_mgf"))


def test_hsp_lookup_water():
    value = T.hsp_lookup("7732-18-5")
    assert value["delta_d"] == 15.5
    assert value["delta_p"] == 16.0
    assert value["delta_h"] == 42.3
    assert value["unit"] == "MPa^0.5"


def test_hsp_lookup_unknown_cas_raises():
    with pytest.raises(ValueError):
        T.hsp_lookup("8009-03-8")  # petrolatum is a mixture, not in the table


def test_hsp_rank_orders_and_reports_errors():
    out = T.hsp_rank("7732-18-5", ["108-88-3", "8009-03-8", "64-17-5"])
    assert out["ranking"][0]["casrn"] == "64-17-5"
    assert [row["casrn"] for row in out["ranking"]][-1] == "8009-03-8"
    assert "error" in out["ranking"][-1]


def test_tdb_path_traversal_is_rejected():
    with pytest.raises(ValueError):
        T.alloy_melting_point("..\\outside.tdb", "AL", "FCC_A1", 900.0, 1000.0)


def test_invalid_bracket_is_refused():
    if not (TDB_DIR / "mc_al_v2.032.pycalphad.tdb").is_file():
        pytest.skip("MatCalc databases not present")
    with pytest.raises(ValueError):
        T.alloy_melting_point("mc_al_v2.032.pycalphad.tdb", "AL", "FCC_A1", 950.0, 960.0)


def test_pure_aluminium_melting_matches_literature():
    if not (TDB_DIR / "mc_al_v2.032.pycalphad.tdb").is_file():
        pytest.skip("MatCalc databases not present")
    value = T.alloy_melting_point("mc_al_v2.032.pycalphad.tdb", "AL", "FCC_A1", 930.0, 936.0)
    assert 933.0 < value["melting_k"] < 934.0


def test_unifac_groups_ethanol():
    out = T.unifac_groups("CCO")
    assert out["subgroups"] == {"CH3": 1, "CH2": 1, "OH": 1}


def test_unifac_r_q_match_published_table():
    out = T.unifac_groups("CCCCCC")
    assert abs(out["r"] - 4.4998) < 0.001
    assert abs(out["q"] - 3.856) < 0.001


def test_unifac_rejects_bad_smiles():
    with pytest.raises(ValueError):
        T.unifac_groups("C1CC")


def test_unifac_gamma_ethanol_water_is_physical():
    out = T.unifac_gamma(["CCO", "O"], [0.5, 0.5])
    assert out["unit"] == "gamma (dimensionless)"
    assert len(out["value"]) == 2
    assert all(value > 1.0 for value in out["value"])
    assert "Dortmund" in out["model"]


def test_unifac_gamma_infinity_dortmund_ethanol():
    out = T.unifac_gamma_infinity(["CCO", "O"])
    # measured 3.77 (Straver & de Loos 2005); Dortmund 4.79, original 7.62
    assert 4.0 < out["value"][0] < 5.5
    assert out["solvent"] == "O"


def test_unifac_gamma_missing_pair_is_an_error_not_a_number():
    out = T.unifac_gamma_infinity(["CSC", "O"], version=0)
    assert out["value"] is None
    assert "no UNIFAC interaction" in out["error"]


def test_kj_recipe_passes_a_repo_recipe():
    out = T.kj_recipe("data/recipes/mint_lemon.json")
    assert out["verdict"] == "PASS"
    assert out["steps"] == 5
    assert out["equation"] is None
    assert out["note"].startswith("procedure only")


def test_kj_recipe_accepts_the_document_itself():
    import json

    path = pathlib.Path(__file__).resolve().parents[2] / "data" / "recipes" / "silver_tarnish.json"
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    out = T.kj_recipe(doc)
    assert out["verdict"] == "PASS"
    assert out["equation"]["balanced"] is True


def test_kj_recipe_red_is_a_result_not_an_exception():
    doc = {
        "schema": "kj-recipe/1",
        "id": "bad",
        "kind": "food",
        "title": "Cold cure",
        "claim_boundary": "x",
        "ingredients": [],
        "steps": [],
        "safety": [],
        "does_not_say": [],
        "sources": [],
    }
    out = T.kj_recipe(doc)
    assert out["verdict"] == "RED"
    assert out["reason"]
