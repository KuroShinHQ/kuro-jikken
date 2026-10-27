"""S1 tests: a goal sentence becomes an application + constraints, or a question.

Acceptance for S1 (docs/ROADMAP_20261027.md): "5 ornek hedef parse; bilinmeyen ->
CLARIFY". The five examples live in ``target.EXAMPLES`` so the documentation and
the test cannot drift apart.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import target  # noqa: E402

TDB = "mc_al_v2.032.pycalphad.tdb"


def test_the_five_documented_examples_parse():
    expected = {
        "Al-5 wt% Cu alasimi 900 K altinda erisin": ("CLARIFY", "alloy.liquidus", ["tdb"]),
        "Mum karisimi (8002-74-2) 330 K altinda erisin": ("READY", "wax.range", []),
        "Vazelin benzeri cilt koruyucu": ("READY", "formulation.petrolatum_like", []),
        "Etanol suda cozunur olsun": ("CLARIFY", "solubility.aqueous", ["smiles"]),
        "Kanserojen olmayan bir yag yap": ("RED", None, []),
    }
    assert set(target.EXAMPLES) == set(expected)
    for text in target.EXAMPLES:
        parsed = target.parse(text)
        status, application, missing = expected[text]
        assert parsed["status"] == status, text
        assert parsed["application"] == application, text
        assert parsed["missing"] == missing, text
        target.validate(parsed)


def test_alloy_target_reads_the_composition_and_the_bound():
    text = "Al-5 wt% Cu alasimi 900 K altinda erisin"
    parsed = target.parse(text, {"tdb": TDB})
    assert parsed["status"] == "READY"
    assert parsed["components"] == ["Al", "Cu"]
    by_key = {c["key"]: c for c in parsed["constraints"]}
    assert by_key["composition.Cu"]["value"] == 5.0
    assert by_key["composition.Cu"]["basis"] == "wt"
    assert by_key["composition.Cu"]["base"] == "Al"
    assert by_key["composition.Cu"]["span"] == "5 wt% cu"
    assert by_key["liquidus_k"]["op"] == "<="
    assert by_key["liquidus_k"]["value"] == 900.0


def test_alloy_target_without_a_database_asks_instead_of_defaulting():
    parsed = target.parse("Al-5 wt% Cu alasimi 900 K altinda erisin")
    assert parsed["status"] == "CLARIFY"
    assert parsed["missing"] == ["tdb"]
    assert parsed["reason"] == "target needs tdb"


def test_celsius_is_converted_to_kelvin_and_the_conversion_is_recorded():
    parsed = target.parse("Al alasimi 5 wt% Cu ile 627 C altinda erisin", {"tdb": TDB})
    bound = [c for c in parsed["constraints"] if c["key"] == "liquidus_k"][0]
    assert bound["value"] == pytest.approx(900.15, abs=0.01)
    assert bound["unit"] == "K"
    assert bound["converted_from"] == "C"


def test_a_percentage_without_a_basis_is_a_question():
    parsed = target.parse("Al alasimi %5 Cu ile 900 K altinda erisin", {"tdb": TDB})
    assert parsed["status"] == "CLARIFY"
    assert parsed["missing"] == ["basis"]
    composition = [c for c in parsed["constraints"] if c["key"] == "composition.Cu"][0]
    assert composition["basis"] is None


def test_a_vague_bound_needs_a_tolerance():
    parsed = target.parse("Al alasimi 5 wt% Cu ile 900 K civarinda erisin", {"tdb": TDB})
    assert parsed["status"] == "CLARIFY"
    assert parsed["missing"] == ["tolerance"]
    bound = [c for c in parsed["constraints"] if c["key"] == "liquidus_k"][0]
    assert bound["op"] == "~"
    assert any("preference" in note for note in parsed["notes"])


def test_petrolatum_target_is_ready_and_names_the_reference_limit():
    parsed = target.parse("Vazelin benzeri cilt koruyucu")
    assert parsed["status"] == "READY"
    assert parsed["application"] == "formulation.petrolatum_like"
    assert any("8009-03-8" in note for note in parsed["notes"])
    assert any("REFERENCE_ONLY" in note for note in parsed["notes"])


def test_unknown_application_becomes_a_question():
    parsed = target.parse("Bana guzel bir sey yap")
    assert parsed["status"] == "CLARIFY"
    assert parsed["application"] is None
    assert parsed["missing"] == ["application"]
    assert parsed["reason"] == "no application matches"


def test_two_equally_strong_applications_are_not_a_pick():
    parsed = target.parse("Mum alasimi yap")
    assert parsed["status"] == "CLARIFY"
    assert parsed["candidates"] == ["alloy.liquidus", "wax.range"]
    assert parsed["reason"] == "two applications match"


@pytest.mark.parametrize(
    "text, word",
    [
        ("Vazelin benzeri ama TEWL dusuk olsun", "tewl"),
        ("Kanserojen olmayan bir yag yap", "kanserojen"),
        ("Azeotrop karisim hedefle", "azeotrop"),
    ],
)
def test_claims_without_an_engine_are_red(text, word):
    parsed = target.parse(text)
    assert parsed["status"] == "RED"
    assert word in parsed["reason"]
    assert parsed["constraints"] == []
    assert parsed["application"] is None


def test_a_cas_number_in_the_sentence_is_an_identifier_not_a_guess():
    parsed = target.parse("Mum karisimi (8002-74-2) 330 K altinda erisin")
    assert parsed["status"] == "READY"
    payload = target.engine_payload(parsed, {"casrn": ["8002-74-2"]})
    assert payload == {"casrn": ["8002-74-2"]}


def test_engine_payload_bridges_only_pairs_the_engines_accept():
    alloy = target.parse("Al-5 wt% Cu alasimi 900 K altinda erisin", {"tdb": TDB})
    assert target.engine_payload(alloy, {"tdb": TDB}) == {
        "elements": ["AL", "CU"], "cu_pct": 5.0, "basis": "wt", "tdb": TDB,
    }

    iron = target.parse("Fe-5 wt% Cu alasimi 900 K altinda erisin", {"tdb": TDB})
    assert iron["status"] == "READY"
    assert target.engine_payload(iron, {"tdb": TDB}) is None

    wax = target.parse("Mum karisimi (8002-74-2) 330 K altinda erisin")
    assert target.engine_payload(wax, {"casrn": ["8002-74-2"]}) == {"casrn": ["8002-74-2"]}
    assert target.engine_payload(wax, {}) is None


def test_validate_rejects_a_malformed_target():
    parsed = target.parse("Vazelin benzeri cilt koruyucu")
    with pytest.raises(ValueError):
        target.validate(dict(parsed, status="DONE"))
    with pytest.raises(ValueError):
        target.validate(dict(parsed, constraints=[{"key": "x", "value": 1}]))
    with pytest.raises(ValueError):
        target.validate(dict(parsed, status="READY", missing=["tdb"]))
