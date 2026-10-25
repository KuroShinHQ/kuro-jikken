"""Applicability-domain flag + error-bar rules (v0.1.0 amendment step).

Rules come from the PREREGISTERED domain statement and the amendment text,
never from the function's own output:
in-domain = neutral, single-component, no metal atom, MW<=500, no phosphorus.
Number sources: KARNE 5-6 (locked-set single evaluation): in-domain RMSE 1.225,
salts/mixtures 5.27, metals 4.99 -> error bars 1.2 (in) / 5.0 (out).
"""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from esol import domain_classify, esol_published, IN_DOMAIN_ERR, OUT_DOMAIN_ERR  # noqa: E402

IN_DOMAIN_SAMPLES = {
    "CC(=O)OC1=CC=CC=C1C(=O)O",  # aspirin
    "CCO",                        # ethanol
    "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # caffeine
}
OUT_DOMAIN_SAMPLES = {
    "[Na+].[Cl-]",      # multi + charged
    "CC(=O)O[Na]",      # metal sodium
    "CC[Pd]CC",         # organometallic palladium
    "CP(C)C",           # trimethylphosphine (phosphorus rule)
    "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC(=O)O",  # MW > 500 fatty acid
}

def test_in_domain_samples_flagged_in():
    for smi in IN_DOMAIN_SAMPLES:
        d = domain_classify(smi)
        assert d["ok"] is True and d["in_domain"] is True and d["domain_reasons"] == []

def test_out_domain_samples_flagged_out_with_reasons():
    for smi in OUT_DOMAIN_SAMPLES:
        d = domain_classify(smi)
        assert d["ok"] is True and d["in_domain"] is False and len(d["domain_reasons"]) >= 1

def test_error_bar_matches_group_and_cited_source():
    r_in = esol_published("CCO")
    r_out = esol_published("[Na+].[Cl-]")
    assert r_in["ok"] is True and r_in["in_domain"] is True
    assert r_in["error_bar_logS"] == pytest.approx(IN_DOMAIN_ERR)
    assert "KARNE" in r_in["error_bar_source"]
    assert r_out["ok"] is True and r_out["in_domain"] is False
    assert r_out["error_bar_logS"] == pytest.approx(OUT_DOMAIN_ERR)

def test_out_domain_caveat_says_plainly_unreliable():
    r = esol_published("CC(=O)O[Na]")
    assert "OUT OF APPLICABILITY DOMAIN" in r["caveat"]
    assert "unreliable" in r["caveat"]

def test_constants_from_karne_groups():
    assert IN_DOMAIN_ERR == pytest.approx(1.2)
    assert OUT_DOMAIN_ERR == pytest.approx(5.0)
