from __future__ import annotations

import pytest

from bench.props import PROPERTIES, PROPERTY_BY_KEY, reference_row

EXPECTED = {
    "C1=CC=CC=C1": {
        "formula": "C6H6",
        "molecular_weight": 78.114,
        "heavy_atom_count": 6,
        "ring_count": 1,
        "hbd_lipinski": 0,
        "hba_lipinski": 0,
        "rotatable_bonds": 0,
    },
    "O": {
        "formula": "H2O",
        "molecular_weight": 18.015,
        "heavy_atom_count": 1,
        "ring_count": 0,
        "hbd_lipinski": 2,
        "hba_lipinski": 1,
        "rotatable_bonds": 0,
    },
    "NC(N)=O": {
        "formula": "CH4N2O",
        "molecular_weight": 60.056,
        "heavy_atom_count": 4,
        "ring_count": 0,
        "hbd_lipinski": 4,
        "hba_lipinski": 3,
        "rotatable_bonds": 0,
    },
    "CC(=O)Oc1ccccc1C(=O)O": {
        "formula": "C9H8O4",
        "molecular_weight": 180.159,
        "heavy_atom_count": 13,
        "ring_count": 1,
        "hbd_lipinski": 1,
        "hba_lipinski": 4,
        "rotatable_bonds": 2,
    },
    "Cn1cnc2c1c(=O)n(C)c(=O)n2C": {
        "formula": "C8H10N4O2",
        "molecular_weight": 194.194,
        "heavy_atom_count": 14,
        "ring_count": 2,
        "hbd_lipinski": 0,
        "hba_lipinski": 6,
        "rotatable_bonds": 0,
    },
}


def test_seven_properties_and_unique_keys():
    assert len(PROPERTIES) == 7
    assert len({p.key for p in PROPERTIES}) == 7
    assert [p.key for p in PROPERTIES] == list(PROPERTY_BY_KEY)


@pytest.mark.parametrize("smiles,expected", EXPECTED.items())
def test_reference_values_match_pinned_rdkit(smiles, expected):
    got = reference_row(smiles)
    for key, want in expected.items():
        if isinstance(want, float):
            assert got[key] == pytest.approx(want, abs=1e-3)
        else:
            assert got[key] == want


def test_bad_smiles_raises_cleanly():
    with pytest.raises(ValueError):
        PROPERTY_BY_KEY["formula"].reference("C1CC")


def test_every_property_has_a_definition_and_format_hint():
    for prop in PROPERTIES:
        assert prop.definition.strip()
        assert prop.format_hint.strip()
        assert prop.label.strip()
