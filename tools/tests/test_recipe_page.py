"""The page is a machine copy of the gated recipe, not a parallel document."""
import json
import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "mcp"))

import recipe  # noqa: E402
import recipe_page  # noqa: E402

RECIPES = sorted((ROOT / "data" / "recipes").glob("*.json"))
PATTERN = re.compile(r"const R = (.*); // kj-recipe-json")


@pytest.mark.parametrize("path", RECIPES, ids=lambda p: p.stem)
def test_page_embeds_the_exact_gated_json(tmp_path, path):
    row = recipe_page.generate(path, tmp_path)
    text = pathlib.Path(row["page"]).read_text(encoding="utf-8")
    embedded = json.loads(PATTERN.search(text).group(1))
    assert embedded == json.loads(path.read_text(encoding="utf-8"))
    assert "breakIt" in text and "target setpoint" in text


def test_check_reports_a_stale_page(tmp_path):
    path = RECIPES[0]
    recipe_page.generate(path, tmp_path)
    assert recipe_page.generate(path, tmp_path, check=True)["stale"] is False
    page = tmp_path / recipe_page.page_name(path)
    page.write_text("stale", encoding="utf-8")
    assert recipe_page.generate(path, tmp_path, check=True)["stale"] is True


def test_a_recipe_with_a_medical_claim_never_gets_a_page(tmp_path):
    doc = json.loads(RECIPES[0].read_text(encoding="utf-8"))
    doc["steps"][0]["action"] = "This drink cures the flu."
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(recipe.RecipeError):
        recipe_page.generate(path, tmp_path)
    assert not list(tmp_path.glob("recipe_bad.html"))
