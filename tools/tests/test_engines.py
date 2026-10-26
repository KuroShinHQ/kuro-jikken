"""P5a adapter tests: a gate-passed plan becomes one honest answer, or a refusal."""
import pathlib
import sys

import pytest

pytest.importorskip("pint")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "mcp"))

import answer as A  # noqa: E402
import engines as E  # noqa: E402
import router as R  # noqa: E402

REQUEST = "etanol suda ne kadar cozunur"


def test_every_adapter_has_units():
    assert set(E.ADAPTERS) <= set(A.UNITS)
    for _cid, _w, engines, _gate, _unit in R.CAPS:
        if engines:
            assert _cid in E.ADAPTERS


def test_smiles_list_reads_every_payload_shape():
    assert E.smiles_list({"smiles": "CCO"}) == ["CCO"]
    assert E.smiles_list({"smiles": ["CCO", "O"]}) == ["CCO", "O"]
    assert E.smiles_list({"components": "CCO O"}) == ["CCO", "O"]
    assert E.smiles_list("CCO") == ["CCO"]
    assert E.smiles_list(None) == []


def test_reproduce_command_carries_the_payload_and_never_writes():
    text = E.reproduce_command(REQUEST, {"smiles": "CCO"})
    assert text.startswith("python tools/ask.py")
    assert '"smiles": "CCO"' in text
    assert text.endswith("--no-write")


def test_esol_answer_is_gated_and_unit_checked():
    plan = R.plan(REQUEST, {"smiles": "CCO"})
    out = E.esol(REQUEST, plan, {"smiles": "CCO"})
    A.validate(out)
    assert out["verdict"] == "GREEN"
    assert out["value"] == pytest.approx(-0.1247458, abs=1e-6)
    assert out["unit"] == "log10(mol/L)"
    assert out["error"]["lower"] <= out["value"] <= out["error"]["upper"]


def test_salt_is_refused_instead_of_given_a_wide_bar():
    """Golden row 3: ESOL on a salt is out of domain, so no number at all."""
    plan = R.plan(REQUEST, {"smiles": "[Na+].[Cl-]"})
    assert plan["gate"]["verdict"] == "YELLOW"
    out = E.esol(REQUEST, plan, {"smiles": "[Na+].[Cl-]"})
    assert out["verdict"] == "RED" and out["value"] is None
    assert out["reason"] == "out of domain"
    assert "charged species" in out["sentence"]


def test_adapter_refuses_when_the_gate_is_red():
    plan = {"route": {"capability": "solubility.aqueous"}, "gate": {"verdict": "RED", "reason": "no"}}
    out = E.esol(REQUEST, plan, {"smiles": "CCO"})
    assert out["verdict"] == "RED" and out["value"] is None


def test_unifac_gamma_infinity_for_ethanol_in_water():
    """Golden row 13: gamma-infinity, first SMILES = solute."""
    plan = R.plan("etanolun suda gamma-infinity'si", {"smiles": ["CCO", "O"]})
    out = E.unifac("etanolun suda gamma-infinity'si", plan, {"smiles": ["CCO", "O"]})
    A.validate(out)
    assert out["value"] == pytest.approx(4.7918, abs=1e-4)
    assert out["unit"] == "ratio"
    assert out["error"]["lower"] == pytest.approx(out["value"] * 0.7)


def test_unifac_at_a_stated_composition_uses_gamma_not_infinity():
    plan = R.plan("etanol gliserinle karisir mi", {"smiles": ["CCO", "OCC(O)CO"]})
    out = E.unifac(
        "etanol gliserinle karisir mi",
        plan,
        {"smiles": ["CCO", "OCC(O)CO"], "xs": [0.2, 0.8]},
    )
    assert out["value"] == pytest.approx(1.6185, abs=1e-4)
    assert "mole fractions" in out["method"]


def test_unifac_bad_composition_is_a_refusal_not_a_crash():
    plan = R.plan("etanol su ile karisir mi", {"smiles": ["CCO", "O"]})
    out = E.unifac("etanol su ile karisir mi", plan, {"smiles": ["CCO", "O"], "xs": [0.5]})
    assert out["verdict"] == "RED"
    assert out["reason"] == "missing parameters"


def test_calphad_without_a_database_is_a_refusal():
    plan = R.plan("aluminyum kac derecede erir", {"element": "AL"})
    out = E.calphad("aluminyum kac derecede erir", plan, {"element": "AL"})
    assert out["verdict"] == "RED" and out["reason"] == "no data"
    assert "mc_al_v2.032" in out["sentence"]


def test_calphad_without_composition_basis_is_a_refusal():
    """'Al-2Cu' alone does not say wt% or at%: one question, no guess."""
    payload = {"tdb": "mc_al_v2.032.pycalphad.tdb", "elements": ["AL", "CU"]}
    plan = R.plan("Al-2Cu alasimi 600 C'de erir mi", payload)
    out = E.calphad("Al-2Cu alasimi 600 C'de erir mi", plan, payload)
    assert out["verdict"] == "RED"
    assert out["reason"] == "unit mismatch"
    assert "wt% mi at% mi" in out["sentence"]
    assert "x_cu / cu_wt_pct" in out["limits"][0]


def test_calphad_zero_copper_uses_the_pure_aluminium_path():
    """Bug 2026-10-27: x_Cu = 0 returned the bracket edge (600.34 K) as GREEN.

    The binary liquidus has no bracket at x_Cu = 0, so the adapter must take the
    validated pure-element path instead of bisecting an impossible bracket.
    """
    payload = {"tdb": "mc_al_v2.032.pycalphad.tdb", "elements": ["AL", "CU"], "cu_wt_pct": 0}
    request = "Al-0 wt% Cu alasimi erir mi"
    plan = R.plan(request, payload)
    out = E.calphad(request, plan, payload)
    assert out["verdict"] == "GREEN"
    assert out["value"] == pytest.approx(933.47, abs=0.1)
    assert "pure Al" in out["method"]


def test_identity_answers_mw_or_logp_by_request():
    payload = {"smiles": "CCO"}
    plan = R.plan("bu molekulun MW'si kac", payload)
    mw = E.identity("bu molekulun MW'si kac", plan, payload)
    assert mw["value"] == pytest.approx(46.069, abs=1e-3)
    assert mw["unit"] == "gram / mole"

    plan = R.plan("bu molekulun logP'si", payload)
    logp = E.identity("bu molekulun logP'si", plan, payload)
    assert logp["value"] == pytest.approx(-0.0014, abs=1e-4)
    assert logp["unit"] == "dimensionless"


def test_identity_refuses_an_unparseable_structure():
    plan = R.plan("bu molekulun logP'si", {"smiles": "unobtainium"})
    out = E.identity("bu molekulun logP'si", plan, {"smiles": "unobtainium"})
    assert out["verdict"] == "RED" and out["reason"] == "out of domain"

def test_unifac_refuses_when_the_request_asks_for_cosmo():
    """Answering a cOSMO question with UNIFAC would be a different model."""
    request = "asetonun suda gamma'si cosmo ile"
    plan = R.plan(request, {"smiles": ["CC(=O)C", "O"]})
    out = E.unifac(request, plan, {"smiles": ["CC(=O)C", "O"]})
    assert out["verdict"] == "RED" and out["value"] is None
    assert out["reason"] == "no engine"
    assert "cOSMO" in out["limits"][0]


# --- R1: mixture.wax now has an adapter -----------------------------------

def test_wax_blend_is_a_yellow_range():
    """Ideal SLE: WAT and last-solid bound the range; never GREEN."""
    payload = {"casrn": ["112-95-8", "630-02-4"], "x": [0.5, 0.5]}
    plan = R.plan("mumun erime araligi nedir", payload)
    out = E.wax("mumun erime araligi nedir", plan, payload)
    assert out["verdict"] == "YELLOW"
    assert out["unit"] == "kelvin"
    assert out["value"] == pytest.approx(326.7, abs=0.1)
    assert out["error"]["lower"] == pytest.approx(302.2, abs=0.1)
    assert out["error"]["kind"] == "range"
    assert out["provenance"]["engine"].startswith("ideal solid-liquid")


def test_wax_pure_component_returns_its_melting_point():
    payload = {"casrn": ["112-95-8"]}
    plan = R.plan("mumun erime araligi nedir", payload)
    out = E.wax("mumun erime araligi nedir", plan, payload)
    assert out["verdict"] == "YELLOW"
    assert out["error"]["lower"] == pytest.approx(out["value"], abs=0.05)


def test_wax_blend_without_fractions_asks_for_them():
    """Equimolar would be an invented composition: ask, do not guess."""
    payload = {"casrn": ["112-95-8", "630-02-4"]}
    plan = R.plan("mumun erime araligi nedir", payload)
    out = E.wax("mumun erime araligi nedir", plan, payload)
    assert out["verdict"] == "RED" and out["value"] is None
    assert out["reason"] == "missing input"
    assert "mole fractions" in out["limits"][0]


def test_wax_fraction_count_must_match_the_cas_count():
    payload = {"casrn": ["112-95-8", "630-02-4"], "x": [0.5]}
    plan = R.plan("mumun erime araligi nedir", payload)
    out = E.wax("mumun erime araligi nedir", plan, payload)
    assert out["verdict"] == "RED" and out["reason"] == "missing input"


def test_wax_dict_payload_reaches_the_gate():
    """{cas: x} form must not be a RED 'no CAS number' from the gate."""
    import gates

    rec = gates.check("gate.wax", {"112-95-8": 0.5, "630-02-4": 0.5})
    assert rec["verdict"] == "PASS"
