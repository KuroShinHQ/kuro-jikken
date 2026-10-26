"""MCP server for the physics engines behind kuro-jikken (Task: engine wiring).

Run with the *inventory* environment, which has pycalphad, chemicals and thermo:

    C:\\KuroshinHQ\\kuro-jikken\\.venv_inventory\\Scripts\\python.exe mcp\\tools_server.py

Why a separate server: the bench environment (``.venv``) is frozen for the
confirmatory run and must not gain new packages. The inventory environment is
isolated and already carries the CALPHAD and Hansen tooling.

Databases are **not** in this repository. The MatCalc open databases are ODbL
1.0 + DbCL 1.0 (share-alike); the pre-modified copies that pycalphad can parse
come from the Materials Genome Foundation 2023 workshop repository. They live in
``KJ_TDB_DIR`` (default ``C:\\KuroshinHQ\\_hub\\data\\alloy_tdb_mgf``) so that the
public MIT repository stays free of share-alike data.

Every tool returns a dict with ``value``/``unit`` or an explicit error string.
No number is returned without its unit and its method.
"""
import os
import pathlib

import pycalphad.variables as v
from chemicals import hansen_delta_d, hansen_delta_h, hansen_delta_p
from mcp.server.mcpserver import MCPServer
from pycalphad import Database, equilibrium

TDB_DIR = pathlib.Path(
    os.environ.get("KJ_TDB_DIR", r"C:\KuroshinHQ\_hub\data\alloy_tdb_mgf")
)
MCP = MCPServer("kuro-jikken-tools")

HSP_NOTE = (
    "Hansen parameters in MPa^0.5 (chemicals returns Pa^0.5, divided by 1000). "
    "Ranking only: no performance, safety or sensory claim follows from a distance."
)


def _tdb(name: str) -> pathlib.Path:
    """Resolve a database file name inside TDB_DIR; reject path traversal."""
    candidate = (TDB_DIR / pathlib.Path(name).name).resolve()
    if candidate.parent != TDB_DIR.resolve():
        raise ValueError("database must be a file name inside the database folder")
    if not candidate.is_file():
        raise ValueError(f"database not found: {name} (looked in {TDB_DIR})")
    return candidate


def _stable_phase(db: Database, element: str, phases: list[str], temperature: float) -> list[str]:
    result = equilibrium(
        db, [element.upper(), "VA"], phases, {v.T: float(temperature), v.P: 101325}
    )
    return [p for p in result.Phase.values.squeeze().tolist() if p]


@MCP.tool()
def alloy_melting_point(
    database: str,
    element: str,
    solid_phase: str,
    low_k: float,
    high_k: float,
) -> dict:
    """Melting temperature of a pure element from a CALPHAD database, by bisection.

    ``low_k`` must be solid and ``high_k`` liquid for the given database; the
    function checks both brackets before bisecting and refuses to guess.
    """
    path = _tdb(database)
    phases = [solid_phase, "LIQUID"]
    db = Database(str(path))
    if solid_phase not in db.phases:
        raise ValueError(f"phase {solid_phase} is not in {database}")
    below = _stable_phase(db, element, phases, low_k)
    above = _stable_phase(db, element, phases, high_k)
    if "LIQUID" in below or "LIQUID" not in above:
        raise ValueError(
            f"bracket is not valid for {element}: {low_k} K -> {below}, "
            f"{high_k} K -> {above}"
        )
    lo, hi = float(low_k), float(high_k)
    for _ in range(12):
        mid = (lo + hi) / 2.0
        if "LIQUID" in _stable_phase(db, element, phases, mid):
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


@MCP.tool()
def hsp_lookup(casrn: str) -> dict:
    """Hansen solubility parameters (dD, dP, dH) of one compound, by CAS number."""
    values = [hansen_delta_d(casrn), hansen_delta_p(casrn), hansen_delta_h(casrn)]
    if any(value is None for value in values):
        raise ValueError(f"no Hansen data for CAS {casrn}")
    return {
        "casrn": casrn,
        "delta_d": round(values[0] / 1000.0, 2),
        "delta_p": round(values[1] / 1000.0, 2),
        "delta_h": round(values[2] / 1000.0, 2),
        "unit": "MPa^0.5",
        "source": "chemicals (MIT), Ruben Manuel Hansen table",
        "note": HSP_NOTE,
    }


@MCP.tool()
def hsp_distance(cas_a: str, cas_b: str) -> dict:
    """Hansen distance Ra between two compounds; smaller means more compatible."""
    a = hsp_lookup(cas_a)
    b = hsp_lookup(cas_b)
    ra = (
        4.0 * (a["delta_d"] - b["delta_d"]) ** 2
        + (a["delta_p"] - b["delta_p"]) ** 2
        + (a["delta_h"] - b["delta_h"]) ** 2
    ) ** 0.5
    return {
        "cas_a": cas_a,
        "cas_b": cas_b,
        "ra": round(ra, 2),
        "unit": "MPa^0.5",
        "method": "Ra = sqrt(4*dD^2 + dP^2 + dH^2)",
        "note": HSP_NOTE,
    }


if __name__ == "__main__":
    MCP.run()
