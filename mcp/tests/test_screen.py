"""S3 tests: target + pool + ledger -> candidates with gate traces."""
import pathlib
import sys

import pytest

pytest.importorskip("rdkit")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import screen  # noqa: E402

ORDERED = [
    ("Etanol suda cozunur olsun", "logS", "desc"),
    ("Su ile karisan bir cozucu", "gamma_inf_water", "asc"),
    ("Vazelin benzeri cilt koruyucu", "logS", "asc"),
]


@pytest.mark.parametrize("text, by, direction", ORDERED)
def test_three_targets_return_an_ordered_list_with_a_gate_trace(text, by, direction):
    result = screen.screen(text, limit=5, max_scan=40)
    screen.validate(result)
    assert result["status"] == "OK", result.get("reason")
    assert result["order"]["by"] == by
    assert result["order"]["direction"] == direction
    assert result["order"]["verdict"] == "CALIBRATED"
    assert result["candidates"]
    for row in result["candidates"]:
        assert row["gates"], row["casrn"]
        assert row["value"] is not None and row["unit"]
        error = row["error"]
        assert error["lower"] <= row["value"] <= error["upper"]


def test_logS_order_is_monotonic_and_uses_the_esol_gate():
    result = screen.screen("Etanol suda cozunur olsun", limit=10, max_scan=60)
    values = [row["value"] for row in result["candidates"]]
    assert values == sorted(values, reverse=True)
    for row in result["candidates"]:
        gate_ids = {gate["gate"] for gate in row["gates"]}
        assert {"gate.structure", "gate.esol"} <= gate_ids


def test_gamma_order_is_monotonic_and_uses_the_unifac_gate():
    result = screen.screen("Su ile karisan bir cozucu", limit=8, max_scan=30)
    values = [row["value"] for row in result["candidates"]]
    assert values == sorted(values)
    for row in result["candidates"]:
        gate_ids = {gate["gate"] for gate in row["gates"]}
        assert {"gate.structure", "gate.unifac"} <= gate_ids


def test_petrolatum_screen_lists_hydrocarbons_and_records_the_r4_blocker():
    result = screen.screen("Vazelin benzeri cilt koruyucu", limit=5, max_scan=20)
    assert result["status"] == "OK"
    assert all(row["group"] == "n-alkane" for row in result["candidates"])
    assert any("R4" in limit for limit in result["limits"])
    assert result["reference"]["gate"] == "gate.hsp"
    assert result["reference"]["verdict"] == "RED"


def test_wax_target_is_filtered_not_ranked():
    result = screen.screen("Mum karisimi 330 K altinda erisin", limit=20, max_scan=20)
    assert result["status"] == "OK"
    assert result["order"]["by"] is None
    assert all(row["tm_k"] <= 330.0 for row in result["candidates"])
    assert all(row["measured"] is True for row in result["candidates"])


def test_a_target_input_the_pool_cannot_supply_is_refused():
    result = screen.screen("Mum karisimi 330 K civarinda erisin")
    assert result["status"] == "CLARIFY"
    assert "tolerance" in result["reason"]
    assert result["candidates"] == []


def test_an_application_without_a_screen_strategy_is_refused():
    result = screen.screen("Al-5 wt% Cu alasimi 900 K altinda erisin")
    assert result["status"] == "CLARIFY"
    assert "no screen strategy" in result["reason"]
    assert result["candidates"] == []


def test_a_claim_without_an_engine_is_red_and_lists_nothing():
    result = screen.screen("Kanserojen olmayan bir yag yap")
    assert result["status"] == "RED"
    assert result["candidates"] == []


def test_screen_is_deterministic():
    first = screen.screen("Vazelin benzeri cilt koruyucu", limit=5, max_scan=20)
    second = screen.screen("Vazelin benzeri cilt koruyucu", limit=5, max_scan=20)
    assert [row["casrn"] for row in first["candidates"]] == [
        row["casrn"] for row in second["candidates"]
    ]


def test_validate_rejects_an_order_without_a_calibrated_verdict():
    result = screen.screen("Vazelin benzeri cilt koruyucu", limit=3, max_scan=20)
    broken = dict(result, order=dict(result["order"], by="logS", verdict="GUESS"))
    with pytest.raises(ValueError):
        screen.validate(broken)


