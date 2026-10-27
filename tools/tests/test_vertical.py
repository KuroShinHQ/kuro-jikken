"""S5 tests: the vertical-slice document is generated, current and bounded."""
import pathlib
import sys

import pytest

pytest.importorskip("rdkit")

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "mcp"))

import screen  # noqa: E402
import vertical_slice  # noqa: E402


def test_document_has_the_five_candidates_and_their_gate_traces():
    text = vertical_slice.document()
    result = screen.screen(vertical_slice.TARGET, limit=5, max_scan=200)
    assert len(result["candidates"]) == 5
    for row in result["candidates"]:
        assert row["casrn"] in text
        assert row["name"] in text
    assert text.count("esol:PASS") >= 5


def test_refusal_boundary_is_measured_not_prose():
    text = vertical_slice.document()
    assert "no Hansen entry" in text
    assert "TEWL claim" in text and "**RED**" in text
    assert "carcinogen claim" in text
    assert "**CLARIFY**" in text


def test_document_on_disk_matches_a_fresh_render():
    path = ROOT / "docs" / "S5_PETROLATUM_SLICE.md"
    assert path.is_file()
    assert path.read_text(encoding="utf-8") == vertical_slice.document()


def test_render_is_deterministic():
    assert vertical_slice.document() == vertical_slice.document()
