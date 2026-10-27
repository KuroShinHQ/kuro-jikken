"""Tests for the R5 calibration ledger and its audit script."""
import copy
import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / "data" / "calibration.json"
SPEC = importlib.util.spec_from_file_location("calibration_check", ROOT / "tools" / "calibration_check.py")
CAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAL)


@pytest.fixture(scope="module")
def ledger():
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_audit_exits_zero():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "calibration_check.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RESULT PASS" in result.stdout


def test_every_adapter_and_gate_has_an_entry(ledger):
    sys.path.insert(0, str(ROOT / "mcp"))
    sys.path.insert(0, str(ROOT / "tools"))
    import engines
    import gates

    caps = {entry["capability"] for entry in ledger["entries"]}
    gate_ids = {entry["gate"] for entry in ledger["entries"]}
    assert set(engines.ADAPTERS) <= caps
    assert set(gates.GATES) <= gate_ids


def test_only_calibrated_properties_are_rankable(ledger):
    rankable = {e["capability"] for e in ledger["entries"] if e["verdict"] == "CALIBRATED"}
    assert rankable == {"solubility.aqueous", "mixture.gamma"}


def test_esol_metrics_match_the_locked_csv(ledger):
    entry = next(e for e in ledger["entries"] if e["id"] == "cal.solubility.aqueous.logs")
    live = CAL.esol_domains()
    for domain in ("in", "out", "all"):
        recorded = entry["measured"]["domains"][domain]
        assert live[domain]["n"] == recorded["n"]
        for key in ("mae", "rmse", "bias", "within_1.0"):
            assert live[domain][key] == pytest.approx(recorded[key], abs=0.002)


def test_calphad_points_recompute_to_the_recorded_error(ledger):
    entry = next(e for e in ledger["entries"] if e["id"] == "cal.alloy.phase.liquidus")
    points = entry["points"]
    assert CAL.points_metric(points, "max_abs") == pytest.approx(8.3, abs=1e-6)
    assert CAL.points_metric(points, "mae") == pytest.approx(2.17, abs=0.005)


def test_unifac_points_recompute_the_median(ledger):
    entry = next(e for e in ledger["entries"] if e["id"] == "cal.mixture.gamma.unifac")
    assert CAL.points_metric(entry["points"], "median_relative") == pytest.approx(0.2131, abs=0.001)


def test_understated_bar_is_rejected(ledger):
    entry = copy.deepcopy(next(e for e in ledger["entries"] if e["id"] == "cal.solubility.aqueous.logs"))
    entry["declared"]["value"] = 0.5
    entry["declared"]["rounding"] = 0.0
    problems = CAL.check_entry(entry)
    assert any("understates" in problem for problem in problems), problems


def test_a_covering_bar_cannot_hide_behind_measured_not_declared(ledger):
    entry = copy.deepcopy(next(e for e in ledger["entries"] if e["id"] == "cal.solubility.aqueous.logs"))
    entry["verdict"] = "MEASURED_NOT_DECLARED"
    entry["declared"]["value"] = 2.0
    problems = CAL.check_entry(entry)
    assert any("already covers" in problem for problem in problems), problems


def test_uncalibrated_entry_must_not_carry_a_metric(ledger):
    entry = copy.deepcopy(next(e for e in ledger["entries"] if e["id"] == "cal.mixture.wax.range"))
    entry["measured"]["metric"] = "mae"
    entry["measured"]["value"] = 1.0
    entry["measured"]["n"] = 5
    problems = CAL.check_entry(entry)
    assert any("UNCALIBRATED" in problem for problem in problems), problems


def test_every_entry_names_its_source_and_licence(ledger):
    for entry in ledger["entries"]:
        assert entry["dataset"]["source"], entry["id"]
        assert entry["dataset"]["license"], entry["id"]
        assert entry["reproduce"], entry["id"]
        assert entry["evidence"], entry["id"]
        assert entry["limits"], entry["id"]
