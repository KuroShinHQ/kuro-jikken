"""P1 tests: a procedure is a document with a gate, not a paragraph.

The two shipped recipes are the fixtures: every negative test mutates a real
recipe, so the contract is pinned to the files a user would actually run.
"""
import copy
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import recipe  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECIPES = ROOT / "data" / "recipes"
SHIPPED = sorted(RECIPES.glob("*.json"))


def minimal() -> dict:
    return {
        "schema": recipe.SCHEMA,
        "id": "test-procedure",
        "kind": "food",
        "title": "Test procedure",
        "summary": "Heat water and let it cool.",
        "claim_boundary": "Food preparation only; this procedure is not a medicine.",
        "ingredients": [{"name": "water", "amount": 1, "unit": "ml", "source": "design"}],
        "steps": [
            {
                "n": 1,
                "action": "Heat the water.",
                "temperature_c": 80,
                "temperature_role": "setpoint",
                "source": "design",
            }
        ],
        "safety": [{"text": "Hot water can scald.", "source": "ref"}],
        "does_not_say": ["that it does anything else"],
        "sources": [
            {
                "id": "ref",
                "title": "Reference",
                "url": "https://example.org/ref",
                "accessed": "2026-10-27",
                "licence": "test",
            }
        ],
    }


def shipped(name: str) -> dict:
    return copy.deepcopy(json.loads((RECIPES / name).read_text(encoding="utf-8")))


@pytest.mark.parametrize("path", SHIPPED, ids=lambda p: p.stem)
def test_shipped_recipes_pass_the_contract(path):
    report = recipe.validate(json.loads(path.read_text(encoding="utf-8")))
    assert report["verdict"] == "PASS"
    assert report["steps"] >= 3
    assert report["sources"]


def test_minimal_fixture_is_valid_and_allows_a_design_setpoint():
    report = recipe.validate(minimal())
    assert report["verdict"] == "PASS"
    assert report["equation"] is None


def test_unknown_source_id_is_refused():
    data = minimal()
    data["steps"][0]["source"] = "not-a-source"
    with pytest.raises(recipe.RecipeError, match="unknown source id"):
        recipe.validate(data)


def test_temperature_limit_without_a_source_is_refused():
    data = minimal()
    data["steps"][0].update(temperature_c=65, temperature_role="limit", source="design")
    with pytest.raises(recipe.RecipeError, match="temperature limit"):
        recipe.validate(data)


def test_medical_claim_outside_the_boundary_is_refused():
    data = minimal()
    data["steps"][0]["action"] = "This drink cures the flu."
    with pytest.raises(recipe.RecipeError, match="medical claim"):
        recipe.validate(data)


def test_a_negated_claim_is_allowed():
    data = minimal()
    data["safety"][0]["text"] = "This drink is not a medicine."
    assert recipe.validate(data)["verdict"] == "PASS"


def test_a_treatment_word_in_an_object_context_is_not_a_claim():
    data = minimal()
    data["safety"][0]["text"] = "Repeated treatment removes a little silver."
    assert recipe.validate(data)["verdict"] == "PASS"


def test_equation_must_balance():
    data = shipped("silver_tarnish.json")
    data["equation"]["text"] = "3 Ag2S(s) + 2 Al(s) + 5 H2O(l) -> 6 Ag(s) + 2 Al(OH)3(s) + 3 H2S(g)"
    with pytest.raises(recipe.RecipeError, match="not balanced"):
        recipe.validate(data)


def test_the_shipped_equation_is_balanced_atom_by_atom():
    data = shipped("silver_tarnish.json")
    report = recipe.validate(data)
    assert report["equation"]["balanced"] is True
    assert report["equation"]["elements"] == {"Ag": 6, "Al": 2, "H": 12, "O": 6, "S": 3}


def test_a_cited_but_unused_source_is_refused():
    data = minimal()
    data["sources"].append(
        {
            "id": "dead",
            "title": "Dead citation",
            "url": "https://example.org/dead",
            "accessed": "2026-10-27",
            "licence": "test",
        }
    )
    with pytest.raises(recipe.RecipeError, match="never used"):
        recipe.validate(data)


def test_turkish_translation_must_have_the_same_shape():
    data = minimal()
    data["tr"] = {
        "title": "Deneme",
        "summary": "Deneme.",
        "claim_boundary": "Yalnizca hazirlik; ilac degil.",
        "steps": ["Bir", "Fazla"],
        "safety": ["Bir"],
        "does_not_say": ["Bir"],
    }
    with pytest.raises(recipe.RecipeError, match="tr.steps"):
        recipe.validate(data)


def test_markdown_keeps_the_boundary_steps_and_every_source():
    data = shipped("mint_lemon.json")
    text = recipe.render_markdown(data, "data/recipes/mint_lemon.json")
    assert data["claim_boundary"] in text or data["tr"]["claim_boundary"] in text
    for step in data["steps"]:
        assert step["source"] in text
    for source in data["sources"]:
        assert source["id"] in text
        assert source["url"] in text
    assert "None" not in text
    assert "65" in text


def test_cli_returns_red_and_exit_1_for_a_broken_file(tmp_path, capsys):
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps({"schema": recipe.SCHEMA}), encoding="utf-8")
    assert recipe.main([str(broken)]) == 1
    row = json.loads(capsys.readouterr().out)
    assert row["verdict"] == "RED"
    assert "missing required fields" in row["reason"]
