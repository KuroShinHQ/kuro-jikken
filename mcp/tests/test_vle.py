"""V1: binary azeotrope engine and its gate.

The two positive cases are the validation pairs from docs/VLE.md; the third is
the negative control (methanol/water is zeotropic at 1 atm).
"""
import pathlib
import sys

import pytest

pytest.importorskip("thermo")
pytest.importorskip("ugropy")

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mcp"))
sys.path.insert(0, str(ROOT / "tools"))

import answer as A  # noqa: E402
import gates as G  # noqa: E402
import pipeline as P  # noqa: E402
import vle as V  # noqa: E402


@pytest.fixture(scope="module")
def ethanol_water():
    return V.azeotrope(["ethanol", "water"], step=0.05)


@pytest.fixture(scope="module")
def propanol_water():
    return V.azeotrope(["2-propanol", "water"], step=0.05)


@pytest.fixture(scope="module")
def methanol_water():
    return V.azeotrope(["methanol", "water"], step=0.05)


def test_ethanol_water_matches_the_literature(ethanol_water):
    """351.32 K / x = 0.894 (docs/VLE.md); the model is within the declared bar."""
    assert ethanol_water["azeotrope"] is True
    assert ethanol_water["temperature_k"] == pytest.approx(351.32, abs=V.DECLARED_BAR_K)
    assert ethanol_water["x1"] == pytest.approx(0.894, abs=0.005)
    assert ethanol_water["y1"] == pytest.approx(ethanol_water["x1"], abs=0.002)


def test_propanol_water_matches_the_literature(propanol_water):
    """353.52 K / x = 0.681 (docs/VLE.md)."""
    assert propanol_water["azeotrope"] is True
    assert propanol_water["temperature_k"] == pytest.approx(353.52, abs=V.DECLARED_BAR_K)
    assert propanol_water["x1"] == pytest.approx(0.681, abs=0.005)


def test_methanol_water_has_no_azeotrope(methanol_water):
    """Negative control: the scan must find no sign change, and report no number."""
    assert methanol_water["azeotrope"] is False
    assert methanol_water["temperature_k"] is None
    assert methanol_water["x1"] is None


def test_gate_marks_validated_and_unvalidated_pairs():
    assert G.gate_vle({"components": ["ethanol", "water"]})["verdict"] == "PASS"
    assert G.gate_vle({"components": ["ethanol", "methanol"]})["verdict"] == "YELLOW"
    assert G.gate_vle({"components": ["ethanol", "water"], "pressure_pa": 50000})[
        "verdict"
    ] == "YELLOW"


def test_gate_refuses_unknown_components_and_wrong_arity():
    unknown = G.gate_vle({"components": ["unobtainium", "water"]})
    assert unknown["verdict"] == "RED" and "not found" in unknown["reason"]
    assert G.gate_vle({"components": ["ethanol"]})["verdict"] == "RED"
    assert G.gate_vle({"components": ["a", "b", "c"]})["verdict"] == "RED"


def test_three_components_are_not_a_binary():
    with pytest.raises(V.VleError):
        V.azeotrope(["ethanol", "water", "methanol"])


def test_answer_carries_the_full_contract(ethanol_water):
    """The engine answer must satisfy the same nine-field contract as every other."""
    out = P.compute("etanol/su azeotrop noktasi", {"components": ["ethanol", "water"]})[1]
    assert out["verdict"] == "GREEN"
    assert out["unit"] == "kelvin"
    assert out["value"] == pytest.approx(ethanol_water["temperature_k"], abs=0.2)
    assert out["error"]["lower"] <= out["value"] <= out["error"]["upper"]
    assert out["provenance"]["engine"] and out["provenance"]["dataset"]
    A.validate(out)
