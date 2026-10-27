"""P5c: the golden set, numerically. Class + number + tolerance, in CI.

A RED row is a correct result, not a failed test: the table says what the
answer must be, and "no number" is an answer. Values are regression pins of
what the engine returns (the tolerance states how far a recomputation may
drift); accuracy claims live in validation/, not here.
"""
import pathlib
import sys

import pytest

pytest.importorskip("pint")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "mcp"))

import answer as A  # noqa: E402
import ledger as L  # noqa: E402
import pipeline as P  # noqa: E402

TDB = "mc_al_v2.032.pycalphad.tdb"

# (row, request, payload, verdict, reason, value, abs tolerance, unit)
ROWS = [
    (1, "etanol suda ne kadar cozunur", {"smiles": "CCO"},
     "GREEN", None, -0.1247458, 1e-6, "log10(mol/L)"),
    (2, "aseton suda ne kadar cozunur", {"smiles": "CC(=O)C"},
     "GREEN", None, -0.575135, 1e-6, "log10(mol/L)"),
    (3, "sofra tuzu suda ne kadar cozunur", {"smiles": "[Na+].[Cl-]"},
     "RED", "out of domain", None, 0, None),
    (4, "vazelin bu kremle uyumlu mu",
     {"casrn": ["8009-03-8"], "smiles": ["CCO", "O"]},
     "RED", "no data", None, 0, None),
    (5, "mineral yagi gliserinle karisir mi", {"casrn": ["8042-47-5"]},
     "RED", "no data", None, 0, None),
    (6, "Al-2Cu alasimi 600 C'de erir mi",
     {"tdb": TDB, "elements": ["AL", "CU"], "cu_wt_pct": 2.0},
     "GREEN", None, 927.783203125, 1.0, "kelvin"),
    (7, "Mg alasimi 700 C'ye dayanir mi", {"elements": ["MG"]},
     "RED", "no data", None, 0, None),
    (8, "bu molekulun MW'si kac", {"smiles": "CCO"},
     "GREEN", None, 46.069, 1e-3, "gram / mole"),
    (9, "etanol/su azeotrop noktasi", {"components": ["ethanol", "water"]},
     "GREEN", None, 351.40, 0.5, "kelvin"),
    (10, "bu ilac toksik mi", None, "RED", "no engine", None, 0, None),
    (11, "bu protein hedefe baglanir mi", None, "RED", "no engine", None, 0, None),
    (12, "mum 40 C'de erir mi", {"casrn": ["112-92-5"]}, "YELLOW", None, 332.6, 0.1, "kelvin"),
    (13, "etanolun suda gamma-infinity'si", {"smiles": ["CCO", "O"]},
     "GREEN", None, 4.7918, 1e-4, "ratio"),
    (14, "asetonun suda gamma'si cosmo ile", {"smiles": ["CC(=O)C", "O"]},
     "RED", "no engine", None, 0, None),
    (15, "bu SMILES gecerli mi", None, "RED", "no engine", None, 0, None),
    (16, "celik 500 C'de oksitlenir mi", None, "RED", "no engine", None, 0, None),
    (17, "emulsiyon kararli mi", None, "RED", "no engine", None, 0, None),
    (18, "bu molekulun logP'si", {"smiles": "CCO"},
     "GREEN", None, -0.0014, 1e-4, "dimensionless"),
    (19, "ld50 degeri nedir", None, "RED", "no engine", None, 0, None),
    (20, "karisim ayrilir mi", None, "RED", "no data", None, 0, None),
]


@pytest.mark.parametrize("row", ROWS, ids=[f"row{r[0]}" for r in ROWS])
def test_golden_row(row):
    number, request, payload, verdict, reason, value, tolerance, unit = row
    plan, ans = P.compute(request, payload)
    assert ans["verdict"] == verdict, f"row {number}: {ans.get('reason')}"
    if verdict == "RED":
        assert ans["value"] is None
        assert ans["reason"] == reason
        assert ans["sentence"]
        return
    assert ans["value"] == pytest.approx(value, abs=tolerance)
    assert ans["unit"] == unit
    assert ans["gate"]["verdict"] in {"PASS", "YELLOW"}
    assert ans["provenance"]["engine"] and ans["provenance"]["dataset"]
    assert ans["reproduce"] and ans["does_not_say"]
    if ans["error"] is not None:
        assert ans["error"]["lower"] <= ans["value"] <= ans["error"]["upper"]


def test_every_golden_row_is_stored_with_its_gate(tmp_path):
    path = tmp_path / "golden.jsonl"
    ids = [P.ask(row[1], row[2], path=path)["ledger"] for row in ROWS]
    entries = L.read(path)
    assert len(entries) == len(ROWS)
    assert len(set(ids)) == len(ROWS)
    numbers = [e for e in entries if e["answer"]["value"] is not None]
    assert len(numbers) == 8  # rows 1, 2, 6, 8, 9, 12, 13, 18 (row 12 = R1 wax)
    for entry in entries:
        A.validate(entry["answer"])
        if entry["answer"]["value"] is not None:
            assert entry["answer"]["gate"]["verdict"] in {"PASS", "YELLOW"}
            assert entry["answer"]["provenance"]


def test_golden_numbers_replay_bit_for_bit(tmp_path):
    path = tmp_path / "golden.jsonl"
    numbers = [row for row in ROWS if row[5] is not None]
    for row in numbers:
        out = P.ask(row[1], row[2], path=path)
        result = L.replay(
            out["ledger"],
            root=tmp_path,
            compute=lambda entry: P.compute(entry["request"], entry.get("payload"))[1],
        )
        assert result["value_same"] is True, row[0]
        assert result["ok"] is True, row[0]
