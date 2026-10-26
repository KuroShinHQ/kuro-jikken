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


def test_gamma_plan_runs_hsp_when_a_cas_is_given():
    plan = R.plan("vazelin bu kremle uyumlu mu", {"casrn": ["8009-03-8"], "smiles": ["CCO", "O"]})
    gates = {g["gate"]: g["verdict"] for g in plan["gates"]}
    assert gates == {"gate.unifac": "PASS", "gate.hsp": "RED"}
    assert plan["gate"]["verdict"] == "RED"
    assert "no Hansen entry" in plan["gate"]["reason"]


def test_extra_gate_is_skipped_without_a_cas():
    plan = R.plan("vazelin bu kremle uyumlu mu", {"smiles": ["CCO", "O"]})
    assert [g["gate"] for g in plan["gates"]] == ["gate.unifac"]
    assert plan["gate"]["verdict"] == "PASS"


def test_hsp_passes_for_a_known_small_molecule():
    plan = R.plan("etanol gliserinle karisir mi", {"casrn": ["64-17-5"], "smiles": ["CCO", "OCC(O)CO"]})
    assert {g["gate"]: g["verdict"] for g in plan["gates"]} == {"gate.unifac": "PASS", "gate.hsp": "PASS"}
    assert plan["gate"]["verdict"] == "PASS"


def test_aggregate_prefers_red_then_yellow_then_pass():
    P, Y, Rr = ({"verdict": "PASS", "reason": "ok"},
                {"verdict": "YELLOW", "reason": "wide bar"},
                {"verdict": "RED", "reason": "out"})
    assert R.aggregate_gates([("a", P), ("b", Rr)])["verdict"] == "RED"
    assert R.aggregate_gates([("a", P), ("b", Y)])["verdict"] == "YELLOW"
    assert R.aggregate_gates([("a", P)])["verdict"] == "PASS"
    assert R.aggregate_gates([]) is None


def test_gate_payloads_slice_the_dictionary():
    route = R.classify("etanol suda ne kadar cozunur")
    pairs = R.gate_payloads(route, {"smiles": "CCO", "casrn": ["64-17-5"]})
    assert pairs == [("gate.esol", "CCO")]
    route = R.classify("Al-2Cu alasimi 600 C'de erir mi")
    payload = {"tdb": "mc_al_v2.032.pycalphad.tdb", "elements": ["AL", "CU"]}
    assert R.gate_payloads(route, payload) == [("gate.calphad", payload)]
    assert R.gate_payloads(route, {"smiles": "CCO"}) == []  # no tdb -> gate cannot run
