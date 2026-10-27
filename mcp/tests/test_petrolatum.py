"""R4: petrolatum has no Hansen entry, and the refusal is pinned (DEC-20261027-R4)."""
import pathlib
import sys

import pytest

pytest.importorskip("chemicals")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import gates  # noqa: E402
import resolver  # noqa: E402
import screen  # noqa: E402
import target as targets  # noqa: E402

MIXTURES = ("8009-03-8", "8002-74-2", "8042-47-5")


@pytest.mark.parametrize("casrn", MIXTURES)
def test_the_hsp_gate_refuses_mixtures(casrn):
    record = gates.check("gate.hsp", casrn)
    assert record["verdict"] == "RED"
    assert "no Hansen entry" in record["reason"]


def test_chemicals_has_no_hansen_values_for_petrolatum():
    from chemicals import hansen_delta_d, hansen_delta_h, hansen_delta_p

    assert hansen_delta_d("8009-03-8") is None
    assert hansen_delta_p("8009-03-8") is None
    assert hansen_delta_h("8009-03-8") is None


def test_vazelin_resolves_to_petrolatum_and_says_why_it_is_limited():
    record = resolver.resolve("vazelin")
    assert record["casrn"] == "8009-03-8"
    assert record["smiles"] is None
    assert any("no Hansen entry" in note for note in record["notes"])


def test_the_petrolatum_target_carries_the_reference_limit():
    parsed = targets.parse("Vazelin benzeri cilt koruyucu")
    assert parsed["status"] == "READY"
    assert parsed["application"] == "formulation.petrolatum_like"
    assert any("8009-03-8" in note for note in parsed["notes"])
    assert any("REFERENCE_ONLY" in note for note in parsed["notes"])


def test_the_screen_shows_the_r4_blocker_and_never_orders_on_hsp():
    result = screen.screen("Vazelin benzeri cilt koruyucu", limit=3, max_scan=20)
    assert result["status"] == "OK"
    assert result["reference"]["gate"] == "gate.hsp"
    assert result["reference"]["verdict"] == "RED"
    assert result["order"]["by"] not in {None, "hsp", "ra"}
    assert any("R4" in limit for limit in result["limits"])


def test_neither_pool_silently_gains_petrolatum():
    import json

    root = pathlib.Path(__file__).resolve().parents[2]
    melting = json.loads((root / "data" / "pool" / "melting.json").read_text(encoding="utf-8"))
    hsp = json.loads((root / "data" / "pool" / "hsp.json").read_text(encoding="utf-8"))
    assert all(entry["casrn"] != "8009-03-8" for entry in melting["entries"])
    assert all(entry["casrn"] != "8009-03-8" for entry in hsp["entries"])
    assert any(item["casrn"] == "8009-03-8" for item in melting["skipped"])

