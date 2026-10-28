"""Tests for the known-first resolver (P1b). Data: AqSolDB snapshot in the repo."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mcp"))

import known_first as kf  # noqa: E402


def first_rows(n: int = 20):
    with open(kf.DATA, encoding="utf-8", newline="") as handle:
        return [row for _, row in zip(range(n), csv.DictReader(handle, delimiter="\t"))]


def test_twenty_known_substances_carry_their_source():
    rows = first_rows(20)
    assert len(rows) == 20
    for row in rows:
        result = kf.resolve(row["SMILES"])
        assert result["status"] == "KNOWN", row["SMILES"]
        assert result["source"]["name"] == "AqSolDB"
        assert result["source"]["doi"] == "10.7910/DVN/OVHAW8"
        assert result["source"]["license"] == "CC0-1.0"
        assert result["source"]["rows"][0]["row_id"]
def test_prediction_used_when_substance_is_not_known(monkeypatch):
    monkeypatch.setattr(kf, "_index", lambda: {})
    result = kf.resolve("CCO")
    assert result["status"] == "PREDICTED"
    assert result["in_domain"] is True
    assert result["error_bar"] == 1.2


def test_out_of_domain_is_red(monkeypatch):
    monkeypatch.setattr(kf, "_index", lambda: {})
    result = kf.resolve("[Fe+2]")
    assert result["status"] == "RED"
    assert result["in_domain"] is False
    assert "metal" in result["reason"]


def test_invalid_smiles_is_red():
    result = kf.resolve("not_a_smiles")
    assert result["status"] == "RED"
    assert "parse" in result["reason"].lower()

