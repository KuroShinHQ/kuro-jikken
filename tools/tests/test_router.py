"""Golden set: 20 requests -> expected route class (docs/ENGINE_ROUTER_PLAN.md §10)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "mcp"))

import router as R  # noqa: E402

GOLDEN = [
    ("etanol suda ne kadar cozunur", "solubility.aqueous"),
    ("aseton suda ne kadar cozunur", "solubility.aqueous"),
    ("sofra tuzu suda ne kadar cozunur", "solubility.aqueous"),
    ("vazelin bu kremle uyumlu mu", "mixture.gamma"),
    ("mineral yagi gliserinle karisir mi", "mixture.gamma"),
    ("Al-2Cu alasimi 600 C'de erir mi", "alloy.phase"),
    ("Mg alasimi 700 C'ye dayanir mi", "alloy.phase"),
    ("bu molekulun MW'si kac", "molecule.identity"),
    ("etanol/su azeotrop noktasi", "vle.azeotrope"),
    ("bu ilac toksik mi", "biology.toxicity"),
    ("bu protein hedefe baglanir mi", "biology.binding"),
    ("mum 40 C'de erir mi", "mixture.wax"),
    ("etanolun suda gamma-infinity'si", "mixture.gamma"),
    ("asetonun suda gamma'si cosmo ile", "mixture.gamma"),
    ("bu SMILES gecerli mi", "UNKNOWN"),
    ("celik 500 C'de oksitlenir mi", "UNKNOWN"),
    ("emulsiyon kararli mi", "product.performance"),
    ("bu molekulun logP'si", "molecule.identity"),
    ("ld50 degeri nedir", "biology.toxicity"),
    ("karisim ayrilir mi", "mixture.gamma"),
]


def test_golden_set_routes():
    bad = []
    for text, expected in GOLDEN:
        got = R.classify(text)["capability"]
        if got != expected:
            bad.append((text, expected, got))
    assert not bad, bad


def test_no_number_in_plan():
    out = R.plan("etanol suda ne kadar cozunur")
    assert "value" not in out and out["route"]["unit"] == "logS"


def test_red_has_no_engine():
    out = R.classify("bu ilac toksik mi")
    assert out["verdict"] == "RED" and out["engines"] == []
