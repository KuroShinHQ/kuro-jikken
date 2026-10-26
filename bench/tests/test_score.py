from __future__ import annotations

import pytest

from bench.props import PROPERTY_BY_KEY
from bench.score import (
    PROCESS_CATEGORIES,
    classify_error,
    hill_normalize,
    parse_formula,
    score_answer,
)

FORMULA = PROPERTY_BY_KEY["formula"]
MW = PROPERTY_BY_KEY["molecular_weight"]
HEAVY = PROPERTY_BY_KEY["heavy_atom_count"]


def test_parse_formula_and_hill_order():
    assert parse_formula("C6H6") == {"C": 6, "H": 6}
    assert parse_formula("CH4N2O") == {"C": 1, "H": 4, "N": 2, "O": 1}
    assert parse_formula("c6h6") is None
    assert parse_formula("C6H6!") is None
    assert hill_normalize({"H": 6, "C": 6}) == "C6H6"
    assert hill_normalize({"O": 1, "H": 2}) == "H2O"


def test_formula_scoring_ignores_element_order():
    assert score_answer(FORMULA, "H6C6", "C6H6")["correct"] is True
    assert score_answer(FORMULA, "C6H6", "C6H6")["correct"] is True
    assert score_answer(FORMULA, "C6H6O", "C6H6")["correct"] is False
    assert score_answer(FORMULA, 42, "C6H6")["correct"] is False


def test_count_and_weight_tolerances():
    assert score_answer(HEAVY, 6, 6)["correct"] is True
    assert score_answer(HEAVY, 6.0, 6)["correct"] is True
    assert score_answer(HEAVY, "6", 6)["correct"] is True
    assert score_answer(HEAVY, 7, 6)["correct"] is False
    assert score_answer(HEAVY, 6.5, 6)["correct"] is False
    assert score_answer(MW, 78.114, 78.114)["correct"] is True
    assert score_answer(MW, 78.16, 78.114)["correct"] is True   # diff 0.046
    assert score_answer(MW, 78.17, 78.114)["correct"] is False  # diff 0.056


def test_missing_answer():
    assert score_answer(FORMULA, None, "C6H6")["correct"] is False
    assert score_answer(FORMULA, None, "C6H6")["detail"] == "missing_answer"


def _call(tool="formula", match=True, value="C6H6"):
    return {"tool": tool, "canonical_match": match, "value": value, "ok": True}


def test_categories():
    assert (
        classify_error(mode="A", prop=FORMULA, answer="C6H5", reference="C6H6", trace=[])
        == "chemistry_knowledge_error"
    )
    assert (
        classify_error(mode="B", prop=FORMULA, answer="C6H5", reference="C6H6", trace=[])
        == "no_tool_call"
    )
    assert (
        classify_error(
            mode="B", prop=FORMULA, answer="C2H6", reference="C6H6", trace=[_call(match=False)]
        )
        == "bad_smiles_passed"
    )
    assert (
        classify_error(
            mode="B", prop=FORMULA, answer="C6H5", reference="C6H6", trace=[_call()]
        )
        == "other"
    )
    assert (
        classify_error(
            mode="B",
            prop=MW,
            answer=78.2,
            reference=78.114,
            trace=[_call(tool="molecular_weight", value=78.114)],
        )
        == "arithmetic_error"
    )
    assert (
        classify_error(
            mode="B",
            prop=MW,
            answer=78114.0,
            reference=78.114,
            trace=[_call(tool="molecular_weight", value=78.114)],
        )
        == "unit_error"
    )
    assert (
        classify_error(
            mode="B", prop=FORMULA, answer=None, reference="C6H6", trace=[_call()]
        )
        == "parse_failure"
    )
    assert "unit_error" in PROCESS_CATEGORIES
    assert "chemistry_knowledge_error" not in PROCESS_CATEGORIES
