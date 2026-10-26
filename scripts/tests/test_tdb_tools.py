from scripts.tdb_merge_constituents import merge
from scripts.tdb_normalize import decode, normalise

RAW = (
    "$ header\n"
    " REFERENCE_ELEMENT AL !\n"
    " ELEMENT AL FCC_A1 26.98 4577 28.3 !\n"
    " PARAMETER G(FCC_A1,AL;0) 298 +100 N REF:POV12 !\n"
    " PARAMETER HMVA(FCC_A1,AL;0) 273 +1 !\n"
    " PHASE SI_DIAMOND_A4 % 1 1 >\n"
    "Silicon precipitate. Space group Fd3m\n"
    ">> 4 !\n"
    " CONSTITUENT SI_DIAMOND_A4 : AL,SI : !\n"
)


def test_decode_falls_back_to_latin1():
    assert decode(b"caf\xe9") == "café"


def test_vendor_command_dropped():
    assert "REFERENCE_ELEMENT" not in normalise(RAW)


def test_hmva_and_ref_tag_removed():
    out = normalise(RAW)
    assert "HMVA" not in out
    assert "N REF:" not in out


def test_abbreviation_expanded():
    assert "PARAMETER G" in normalise(RAW)


def test_phase_prose_removed():
    line = [l for l in normalise(RAW).splitlines() if "SI_DIAMOND" in l][0]
    assert "precipitate" not in line.lower()
    assert ">>" in line


def test_merge_injects_constituents():
    merged, missing = merge(normalise(RAW))
    line = [l for l in merged.splitlines() if "SI_DIAMOND" in l][0]
    assert "AL,SI" in line
    assert missing == []


def test_merge_reports_missing_constituent():
    merged, missing = merge(" PHASE X % 1 1 > >> 0 !\n")
    assert missing == ["X"]
    assert "PHASE X" in merged

