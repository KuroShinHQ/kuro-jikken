"""Pure-element melting from a CALPHAD database, shared by the MCP server and the
answer contract (so both use exactly one implementation).

Databases are ODbL 1.0 + DbCL 1.0 and stay outside the repository; they live in
``KJ_TDB_DIR`` (default ``C:\\KuroshinHQ\\_hub\\data\\alloy_tdb_mgf``).
"""
import os
import pathlib

import pycalphad.variables as v
from pycalphad import Database, equilibrium

TDB_DIR = pathlib.Path(os.environ.get("KJ_TDB_DIR", r"C:\KuroshinHQ\_hub\data\alloy_tdb_mgf"))


def tdb_path(name: str) -> pathlib.Path:
    """Resolve a database file name inside TDB_DIR; reject path traversal."""
    candidate = (TDB_DIR / pathlib.Path(name).name).resolve()
    if candidate.parent != TDB_DIR.resolve():
        raise ValueError("database must be a file name inside the database folder")
    if not candidate.is_file():
        raise ValueError(f"database not found: {name} (looked in {TDB_DIR})")
    return candidate


def stable_phase(db: Database, element: str, phases: list, temperature: float) -> list:
    result = equilibrium(
        db, [element.upper(), "VA"], phases, {v.T: float(temperature), v.P: 101325}
    )
    return [p for p in result.Phase.values.squeeze().tolist() if p]


def melting_point(
    database: str,
    element: str,
    solid_phase: str,
    low_k: float,
    high_k: float,
) -> dict:
    """Melting temperature of a pure element, by bisection over a checked bracket."""
    path = tdb_path(database)
    phases = [solid_phase, "LIQUID"]
    db = Database(str(path))
    if solid_phase not in db.phases:
        raise ValueError(f"phase {solid_phase} is not in {database}")
    below = stable_phase(db, element, phases, low_k)
    above = stable_phase(db, element, phases, high_k)
    if "LIQUID" in below or "LIQUID" not in above:
        raise ValueError(
            f"bracket is not valid for {element}: {low_k} K -> {below}, "
            f"{high_k} K -> {above}"
        )
    lo, hi = float(low_k), float(high_k)
    for _ in range(12):
        mid = (lo + hi) / 2.0
        if "LIQUID" in stable_phase(db, element, phases, mid):
            hi = mid
        else:
            lo = mid
    return {
        "database": path.name,
        "element": element.upper(),
        "solid_phase": solid_phase,
        "melting_k": round((lo + hi) / 2.0, 2),
        "bracket_width_k": round(hi - lo, 4),
        "conditions": "P = 101325 Pa, pure element (X = 1)",
        "method": "pycalphad equilibrium + bisection, 12 steps",
        "note": "Melting/solidus only. Creep, oxidation and corrosion are not modelled.",
    }
