"""Tests for tools/p1c_analyze.py - synthetic rows only, no measurements."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from p1c_analyze import REFERENCE, analyse  # noqa: E402


def make_points(multiplier: float = 1.0, temps=None):
    temps = temps or [20.0, 40.0, 60.0, 80.0, 90.0]
    points = []
    for temp in temps:
        for rep in (1, 2):
            points.append(
                {
                    "point_id": f"P{int(temp)}-{rep}",
                    "rep": str(rep),
                    "temp": temp,
                    "mid": REFERENCE[temp] * multiplier,
                    "unc": 1.0,
                    "notes": "",
                }
            )
    return points


def test_exact_reference_values_pass():
    result = analyse(make_points())
    assert result["complete"] is True
    assert result["h1"] is True and result["h2"] is True and result["h3"] is True
    assert result["verdict"] == "PASS"


def test_twenty_percent_high_fails_accuracy():
    result = analyse(make_points(1.20))
    assert result["h1"] is False
    assert result["verdict"] == "FAIL"


def test_non_monotonic_fails_trend():
    points = make_points()
    for point in points:
        if point["temp"] == 60.0:
            point["mid"] = REFERENCE[60.0] * 0.5
    result = analyse(points)
    assert result["h2"] is False
    assert result["verdict"] == "FAIL"


def test_partial_set_is_incomplete():
    result = analyse(make_points(temps=[20.0, 40.0, 60.0]))
    assert result["complete"] is False
    assert result["fallback"] is False
    assert result["verdict"] == "INCOMPLETE"
