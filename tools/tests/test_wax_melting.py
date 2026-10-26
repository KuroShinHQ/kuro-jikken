"""Tests for tools/wax_melting.py (needs chemicals; skipped in the bench env)."""
import pathlib
import sys

import pytest

pytest.importorskip("chemicals")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import wax_melting as W  # noqa: E402


def test_pure_component_returns_its_melting_point():
    assert abs(W.component_temperature("112-95-8", 1.0) - 309.9) < 0.1


def test_mixture_range_order_and_bounds():
    out = W.wax_range({"112-95-8": 0.5, "646-31-1": 0.3, "630-02-4": 0.2})
    assert out["wax_appearance_k"] > out["last_solid_k"]
    assert 290.0 < out["last_solid_k"] < 320.0
    assert 300.0 < out["wax_appearance_k"] < 345.0


def test_fractions_are_normalised():
    out = W.wax_range({"112-95-8": 1.0, "646-31-1": 1.0})
    assert [row["x"] for row in out["components"]] == [0.5, 0.5]


def test_zero_fraction_rejected():
    with pytest.raises(ValueError):
        W.component_temperature("112-95-8", 0.0)
