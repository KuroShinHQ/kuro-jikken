from __future__ import annotations

import pandas as pd
import pytest

from bench.select import filter_frame, in_domain, select, write_id_lists


def frame(rows):
    return pd.DataFrame(rows, columns=["ID", "Name", "InChIKey", "SMILES"])


BASE = frame(
    [
        ("A-1", "benzene", "UHOVQNZJYSORNB-UHFFFAOYSA-N", "C1=CC=CC=C1"),
        ("A-2", "water", "XLYOFNOQVPJJNP-UHFFFAOYSA-N", "O"),
        ("A-3", "ethanol", "LFQSCWFLJHTTHZ-UHFFFAOYSA-N", "CCO"),
        ("A-4", "toluene", "YXFVVABEGXRONW-UHFFFAOYSA-N", "CC1=CC=CC=C1"),
        ("A-5", "acetate sodium", "VMHLLURERBWHNL-UHFFFAOYSA-M", "CC(=O)[O-].[Na+]"),
        ("A-6", "phosphoric acid", "NBIIXXVUZAFLBC-UHFFFAOYSA-N", "OP(=O)(O)O"),
        ("A-7", "too big", "BIGBIGBIGBIGBIG-UHFFFAOYSA-N", "C" * 60),
        ("A-8", "unparsable", "BADBADBADBADBAD-UHFFFAOYSA-N", "C1CC"),
        ("A-9", "benzene duplicate", "UHOVQNZJYSORNB-UHFFFAOYSA-N", "c1ccccc1"),
        ("A-10", "ammonium", "QGZKDVFQNNGYKY-UHFFFAOYSA-O", "[NH4+]"),
    ]
)


def test_in_domain_accepts_benzene_and_water():
    assert in_domain("C1=CC=CC=C1") == (True, "in_domain")
    assert in_domain("O") == (True, "in_domain")


@pytest.mark.parametrize(
    "smiles,reason",
    [
        ("", "missing_smiles"),
        ("CC(=O)[O-].[Na+]", "multi_component"),
        ("C1CC", "smiles_unparsable"),
        ("[NH4+]", "charged"),
        ("OP(=O)(O)O", "element_not_allowed:P"),
        ("C" * 60, "mw_over_500"),
    ],
)
def test_in_domain_reasons(smiles, reason):
    ok, got = in_domain(smiles)
    assert ok is False
    assert got == reason


def test_filter_dedupes_and_counts():
    kept, reasons = filter_frame(BASE)
    ids = [row["molecule_id"] for row in kept]
    assert "UHOVQNZJYSORNB-UHFFFAOYSA-N" in ids
    assert ids.count("UHOVQNZJYSORNB-UHFFFAOYSA-N") == 1
    assert reasons["duplicate_inchikey"] == 1
    assert reasons["multi_component"] == 1
    assert reasons["element_not_allowed:P"] == 1
    assert reasons["mw_over_500"] == 1
    assert reasons["smiles_unparsable"] == 1
    assert reasons["charged"] == 1


def test_select_splits_and_is_reproducible():
    first, report = select(BASE, n_total=4, n_pilot=1, seed=7)
    second, _ = select(BASE, n_total=4, n_pilot=1, seed=7)
    assert [r["molecule_id"] for r in first] == [r["molecule_id"] for r in second]
    assert [r["split"] for r in first] == ["pilot", "confirmatory", "confirmatory", "confirmatory"]
    assert report["n_total"] == 4
    assert report["n_confirmatory"] == 3


def test_select_requires_enough_molecules():
    with pytest.raises(ValueError, match="only"):
        select(BASE, n_total=250, n_pilot=50, seed=1)


def test_write_id_lists_hashes(tmp_path):
    records, _ = select(BASE, n_total=4, n_pilot=1, seed=7)
    hashes = write_id_lists(records, tmp_path)
    assert (tmp_path / "ids_pilot.txt").read_text().count("\n") == 1
    assert (tmp_path / "ids_confirmatory.txt").read_text().count("\n") == 3
    assert set(hashes) == {"ids_pilot.txt", "ids_confirmatory.txt", "ids_all.csv"}
    assert all(len(value) == 64 for value in hashes.values())
