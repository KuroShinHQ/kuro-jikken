"""Task 4 · pytest known-answer tests for the RDKit tool (docs/FIRST_TASKS.md).

Source policy:
* Expected values for formula / molecular_weight / heavy_atom_count /
  rotatable_bonds / hbond values that MATCH definitions come from PubChem
  (PUG REST snapshot stored in ``data/raw_pubchem/cid_<cid>_*.json``,
  retrieved 2026-10-24) — never from the function under test.
* The five rows where RDKit's pinned definition and PubChem's differ carry a
  DEFINITION-DERIVED constant (rule + structure arithmetic, cited in comments)
  plus the PubChem value reference; the delta is analyzed, not hidden, in
  ``validation/tool_vs_pubchem.md`` (Task 6).

Molecule set: 14 harmless, well-known compounds (README §5 benefit-of-doubt).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdkit_tool import (  # noqa: E402
    RDKit_VERSION,
    formula,
    heavy_atom_count,
    hbond_acceptors,
    hbond_donors,
    molecular_weight,
    parse_smiles,
    ring_count,
    rotatable_bonds,
    hbd_lipinski,
    hbd_plain,
    hba_lipinski,
    hba_plain,
    rotatable_bonds_strict,
    rotatable_bonds_nonstrict,
)

PINNED_RDKit = "2026.09.1"

# (name, cid, PubChem SMILES, PubChem formula, PubChem MW [g/mol], PC heavy atoms)
PUBCHEM_CITED = [
    ("water",       962,  "O",                                     "H2O",      18.015, 1),
    ("ethanol",     702,  "CCO",                                   "C2H6O",    46.07,  3),
    ("benzene",     241,  "C1=CC=CC=C1",                           "C6H6",     78.11,  6),
    ("aceticacid",  176,  "CC(=O)O",                               "C2H4O2",   60.05,  4),
    ("acetone",     180,  "CC(=O)C",                               "C3H6O",    58.08,  4),
    ("urea",        1176, "C(=O)(N)N",                             "CH4N2O",   60.056, 4),
    ("glycine",     750,  "C(C(=O)O)N",                            "C2H5NO2",  75.07,  5),
    ("aspirin",     2244, "CC(=O)OC1=CC=CC=C1C(=O)O",              "C9H8O4",   180.16, 13),
    ("caffeine",    2519, "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",          "C8H10N4O2", 194.19, 14),
    ("glucose",     5793, "C([C@@H]1[C@H]([C@@H]([C@H](C(O1)O)O)O)O)O", "C6H12O6", 180.16, 12),
    ("citricacid",  311,  "C(C(=O)O)C(CC(=O)O)(C(=O)O)O",          "C6H8O7",   192.12, 13),
    ("ibuprofen",   3672, "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",         "C13H18O2", 206.28, 15),
    ("menthol",     1254, "CC1CCC(C(C1)O)C(C)C",                   "C10H20O",  156.26, 11),
    ("vanillin",    1183, "COC1=C(C=CC(=C1)C=O)O",                 "C8H8O3",   152.15, 11),
]

NAME2 = {row[0]: row for row in PUBCHEM_CITED}


def cite(row):
    name, cid = row[0], row[1]
    return f"PubChem CID {cid}, retrieved 2026-10-24 (data/raw_pubchem/cid_{cid}_*.json)"


# ---------------------------------------------------------------- envelope ---

@pytest.mark.parametrize("func", [formula, molecular_weight, heavy_atom_count,
                                  ring_count, rotatable_bonds, hbond_donors, hbond_acceptors])
def test_envelope_shape(func):
    out = func("CCO")
    for key in ("value", "unit", "method", "rdkit_version"):
        assert key in out, f"{func.__name__}: missing key {key}"
    assert out["rdkit_version"] == PINNED_RDKit
    assert isinstance(out["method"], str) and out["method"]


def test_rdkit_version_matches_pin():
    assert RDKit_VERSION == PINNED_RDKit


# ------------------------------------------------------------ PubChem rows ---

@pytest.mark.parametrize("name", [n for n, *_ in PUBCHEM_CITED])
def test_formula_matches_pubchem(name):
    row = NAME2[name]
    assert formula(row[2]).get("value") == row[3], cite(row)


@pytest.mark.parametrize("name", [n for n, *_ in PUBCHEM_CITED])
def test_molecular_weight_matches_pubchem(name):
    row = NAME2[name]
    out = molecular_weight(row[2])
    assert abs(out.get("value") - row[4]) <= 0.05, cite(row)


@pytest.mark.parametrize("name", [n for n, *_ in PUBCHEM_CITED])
def test_heavy_atom_count_matches_pubchem(name):
    row = NAME2[name]
    assert heavy_atom_count(row[2]).get("value") == row[5], cite(row)


ALIGNED_ROT_B = [n for n, *_ in PUBCHEM_CITED if n != "aspirin"]

@pytest.mark.parametrize("name", ALIGNED_ROT_B)
def test_rotatable_bonds_matches_pubchem(name):
    row = NAME2[name]
    pc_rotb = {"water": 0, "ethanol": 0, "benzene": 0, "aceticacid": 0, "acetone": 0,
               "urea": 0, "glycine": 1, "caffeine": 0, "glucose": 1, "citricacid": 5,
               "ibuprofen": 4, "menthol": 1, "vanillin": 2}[name]
    assert rotatable_bonds(row[2]).get("value") == pc_rotb, cite(row)


ALIGNED_HBD = [n for n, *_ in PUBCHEM_CITED if n not in ("water", "urea", "glycine")]

@pytest.mark.parametrize("name", ALIGNED_HBD)
def test_hbond_donors_pubchem_aligned(name):
    row = NAME2[name]
    pc_hbd = {"ethanol": 1, "benzene": 0, "aceticacid": 1, "acetone": 0, "aspirin": 1,
              "caffeine": 0, "glucose": 5, "citricacid": 4, "ibuprofen": 1,
              "menthol": 1, "vanillin": 1}[name]
    assert hbond_donors(row[2]).get("value") == pc_hbd, cite(row)


ALIGNED_HBA = [n for n, *_ in PUBCHEM_CITED if n not in ("urea", "caffeine")]

@pytest.mark.parametrize("name", ALIGNED_HBA)
def test_hbond_acceptors_pubchem_aligned(name):
    row = NAME2[name]
    pc_hba = {"water": 1, "ethanol": 1, "benzene": 0, "aceticacid": 2, "acetone": 1,
              "glycine": 3, "aspirin": 4, "glucose": 6, "citricacid": 7,
              "ibuprofen": 2, "menthol": 1, "vanillin": 3}[name]
    assert hbond_acceptors(row[2]).get("value") == pc_hba, cite(row)


# ------------------------------------- definition-difference rows (Task 6) ----

DEF_ROWS = [
    # (name, func, expected-from-pinned-definition, reason, PubChem value)
    ("water", hbond_donors, 2,
     "CalcNumLipinskiHBD counts NH/OH hydrogens; water H2O has 2 O-H hydrogens",
     "PubChem 1 (donor-atom count: one O)"),
    ("urea", hbond_donors, 4,
     "CalcNumLipinskiHBD counts NH/OH hydrogens; urea has 4 N-H hydrogens (2 NH2)",
     "PubChem 2 (donor-atom count: two N)"),
    ("glycine", hbond_donors, 3,
     "CalcNumLipinskiHBD counts NH/OH hydrogens; glycine: 2 (NH2) + 1 (COOH) = 3",
     "PubChem 2 (donor-atom count: N + O)"),
    ("urea", hbond_acceptors, 3,
     "CalcNumLipinskiHBA counts N/O atoms; urea N2O -> 3",
     "PubChem 1 (acceptor-eligible subset)"),
    ("caffeine", hbond_acceptors, 6,
     "CalcNumLipinskiHBA counts N/O atoms; caffeine N4O2 -> 6",
     "PubChem 3 (acceptor-eligible subset)"),
    ("aspirin", rotatable_bonds, 2,
     "CalcNumRotatableBonds default excludes amide/ester-like bonds per bundled doc",
     "PubChem 3 (includes the ester C-O bond)"),
]

@pytest.mark.parametrize("name, func, expected, reason, pcnote",
                         DEF_ROWS, ids=[f"{r[0]}_{r[1].__name__}" for r in DEF_ROWS])
def test_definition_difference_rows(name, func, expected, reason, pcnote):
    row = NAME2[name]
    assert func(row[2]).get("value") == expected, f"{reason} | {pcnote} | {cite(row)}"


# ------------------------------------------------------------ ring count ----

# No PubChem RingCount tag exists (probed; HBond*AtomCount/RingCount -> HTTP 400).
# Ring counts follow the pinned RDKit definition (CalcNumRings: SSSR-based),
# hand-counted from the structure:
RINGS = {"water": 0, "ethanol": 0, "benzene": 1, "aceticacid": 0, "acetone": 0,
         "urea": 0, "glycine": 0, "aspirin": 1, "caffeine": 2, "glucose": 1,
         "citricacid": 0, "ibuprofen": 1, "menthol": 1, "vanillin": 1}

@pytest.mark.parametrize("name", [n for n, *_ in PUBCHEM_CITED])
def test_ring_count_handcounted(name):
    row = NAME2[name]
    assert ring_count(row[2]).get("value") == RINGS[name]


# ------------------------------------------------------------ error paths ----

@pytest.mark.parametrize("func", [formula, molecular_weight, heavy_atom_count,
                                  ring_count, rotatable_bonds, hbond_donors, hbond_acceptors])
def test_invalid_smiles_clean_error(func):
    out = func("not-a-smiles")
    assert out == {"ok": False, "error": "RDKit could not parse SMILES: 'not-a-smiles'",
                   "rdkit_version": PINNED_RDKit}


def test_parse_smiles_invalid():
    out = parse_smiles("not-a-smiles")
    assert out["ok"] is False and "error" in out


@pytest.mark.parametrize("name", [n for n, *_ in PUBCHEM_CITED])
def test_parse_smiles_canonical_idempotent(name):
    row = NAME2[name]
    first = parse_smiles(row[2])
    assert first["ok"] is True
    second = parse_smiles(first["canonical_smiles"])
    assert second["ok"] is True
    assert first["canonical_smiles"] == second["canonical_smiles"], cite(row)


# --- definition variants (Task A): no primary chosen yet -------------------
# (name, hbd_lip, hbd_plain, hba_lip, hba_plain, rot_def, rot_ns,
#  pc_hbd, pc_hba, pc_rotb)
VARIANT_ROWS = [
    ("water", 2, 0, 1, 0, 0, 0, 1, 1, 0),
    ("ethanol", 1, 1, 1, 1, 0, 0, 1, 1, 0),
    ("benzene", 0, 0, 0, 0, 0, 0, 0, 0, 0),
    ("aceticacid", 1, 1, 2, 1, 0, 0, 1, 2, 0),
    ("acetone", 0, 0, 1, 1, 0, 0, 0, 1, 0),
    ("urea", 4, 2, 3, 1, 0, 0, 2, 1, 0),
    ("glycine", 3, 2, 3, 2, 1, 1, 2, 3, 1),
    ("aspirin", 1, 1, 4, 3, 2, 3, 1, 4, 3),
    ("caffeine", 0, 0, 6, 3, 0, 0, 0, 3, 0),
    ("glucose", 5, 5, 6, 6, 1, 1, 5, 6, 1),
    ("citricacid", 4, 4, 7, 4, 5, 5, 4, 7, 5),
    ("ibuprofen", 1, 1, 2, 1, 4, 4, 1, 2, 4),
    ("menthol", 1, 1, 1, 1, 1, 1, 1, 1, 1),
    ("vanillin", 1, 1, 3, 3, 2, 2, 1, 3, 2),
]

VROWS = {r[0]: r for r in VARIANT_ROWS}


@pytest.mark.parametrize("name", [r[0] for r in VARIANT_ROWS])
def test_variant_matrix(name):
    r = VROWS[name]
    smi = NAME2[name][2]
    assert hbd_lipinski(smi)["value"] == r[1], f"{name} hbd_lipinski"
    assert hbd_plain(smi)["value"] == r[2], f"{name} hbd_plain"
    assert hba_lipinski(smi)["value"] == r[3], f"{name} hba_lipinski"
    assert hba_plain(smi)["value"] == r[4], f"{name} hba_plain"
    assert rotatable_bonds_strict(smi)["value"] == r[5], f"{name} rot_def"
    assert rotatable_bonds_nonstrict(smi)["value"] == r[6], f"{name} rot_ns"
    assert r[7] == VROWS[name][7] and r[8] == VROWS[name][8]


def test_variant_aliases():
    smi = NAME2["urea"][2]
    assert hbd_lipinski(smi)["value"] == hbond_donors(smi)["value"]
    assert hba_lipinski(smi)["value"] == hbond_acceptors(smi)["value"]
    assert rotatable_bonds_strict(smi)["value"] == rotatable_bonds(smi)["value"]
