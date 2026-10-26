"""Tests for tools/unifac_gamma.py (needs ugropy + thermo; bench env skips)."""
import pathlib
import sys

import pytest

pytest.importorskip("thermo")
pytest.importorskip("ugropy")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import unifac_gamma as U  # noqa: E402

MEASURED_ETHANOL_IN_WATER = 3.77  # Straver & de Loos 2005, 298 K, docs/GAMMA_VALIDATION.md


def test_default_is_dortmund():
    assert U.DEFAULT_VERSION == 1
    assert "Dortmund" in U.describe(1)["model"]
    assert "original" in U.describe(0)["model"]


def test_pure_component_is_ideal():
    assert U.gamma(["CCO"], [1.0]) == [1.0]


def test_water_in_water_is_ideal():
    assert U.gamma_inf(["O", "O"]) == [1.0, 1.0]


def test_ethanol_gamma_falls_with_its_own_concentration():
    dilute = U.gamma(["CCO", "O"], [0.05, 0.95])[0]
    concentrated = U.gamma(["CCO", "O"], [0.80, 0.20])[0]
    assert dilute > concentrated > 1.0


def test_homologous_alcohols_increase():
    ethanol = U.gamma_inf(["CCO", "O"])[0]
    propanol = U.gamma_inf(["CCCO", "O"])[0]
    assert propanol > ethanol > MEASURED_ETHANOL_IN_WATER


def test_dortmund_ethanol_within_thirty_percent_of_measurement():
    predicted = U.gamma_inf(["CCO", "O"])[0]
    assert abs(predicted / MEASURED_ETHANOL_IN_WATER - 1.0) <= 0.30


def test_original_unifac_overshoots_ethanol():
    predicted = U.gamma_inf(["CCO", "O"], version=0)[0]
    assert predicted > 2.0 * MEASURED_ETHANOL_IN_WATER


def test_dortmund_beats_original_on_propanol():
    measured = 13.34
    original = U.gamma_inf(["CCCO", "O"], version=0)[0]
    dortmund = U.gamma_inf(["CCCO", "O"], version=1)[0]
    assert abs(dortmund / measured - 1.0) < abs(original / measured - 1.0)


def test_missing_interaction_is_refused_not_guessed():
    with pytest.raises(U.MissingInteraction):
        U.gamma_inf(["CSC", "O"], version=0)


def test_alias_is_not_ambiguous_for_acetaldehyde():
    # ugropy spells the aldehyde group HCO; thermo has two subgroups named CHO
    assert U.subgroups("CC=O", version=0) == {"CH3": 1, "CHO": 1}
    assert 4.0 < U.gamma_inf(["CC=O", "O"])[0] < 6.0


def test_ambiguous_name_is_refused():
    table = {1: type("S", (), {"group": "X", "main_group": "A", "group_id": 1}),
             2: type("S", (), {"group": "X", "main_group": "B", "group_id": 2})}
    with pytest.raises(U.UnsupportedGroup):
        U._by_name(table, 0)


def test_length_and_fraction_validation():
    with pytest.raises(ValueError):
        U.gamma(["CCO"], [0.5, 0.5])
    with pytest.raises(ValueError):
        U.gamma(["CCO", "O"], [-0.1, 1.1])
    with pytest.raises(ValueError):
        U.gamma([], [])


def test_unknown_version_rejected():
    with pytest.raises(ValueError):
        U.gamma(["CCO"], [1.0], version=99)
