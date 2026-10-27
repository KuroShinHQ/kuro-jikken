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
import pathlib
import sys

from chemicals import hansen_delta_d, hansen_delta_h, hansen_delta_p
from mcp.server.mcpserver import MCPServer

TOOLS_DIR = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
if str(pathlib.Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import calphad_engine  # noqa: E402

MCP = MCPServer("kuro-jikken-tools")

HSP_NOTE = (
    "Hansen parameters in MPa^0.5 (chemicals returns Pa^0.5, divided by 1000). "
    "Ranking only: no performance, safety or sensory claim follows from a distance."
)

UNIFAC_NOTE = (
    "gamma is dimensionless. Version 1 (Dortmund) is the default and stays "
    "within about +/-25 % of measured aqueous gamma-infinity for alcohols and "
    "ketones; version 0 (original UNIFAC) overshoots by +50..+110 %. A missing "
    "main-group pair is returned as an error, never as a number. "
    "See docs/GAMMA_VALIDATION.md."
)


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
    function checks both brackets before bisecting and refuses to guess. The
    implementation lives in ``mcp/calphad_engine.py`` so that this tool and the
    answer contract (P5a) run exactly the same code.
    """
    return calphad_engine.melting_point(database, element, solid_phase, low_k, high_k)


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


@MCP.tool()
def hsp_rank(reference_cas: str, candidate_cas: list[str]) -> dict:
    """Rank candidates by Hansen distance to a reference; smaller is closer."""
    ref = hsp_lookup(reference_cas)
    rows = []
    for cas in candidate_cas:
        try:
            item = hsp_lookup(cas)
        except ValueError as exc:
            rows.append({"casrn": cas, "error": str(exc)})
            continue
        ra = (
            4.0 * (ref["delta_d"] - item["delta_d"]) ** 2
            + (ref["delta_p"] - item["delta_p"]) ** 2
            + (ref["delta_h"] - item["delta_h"]) ** 2
        ) ** 0.5
        rows.append({"casrn": cas, "ra": round(ra, 2)})
    rows.sort(key=lambda row: row.get("ra", 1e9))
    return {
        "reference": reference_cas,
        "unit": "MPa^0.5",
        "ranking": rows,
        "note": HSP_NOTE,
    }


@MCP.tool()
def unifac_groups(smiles: str) -> dict:
    """UNIFAC subgroup decomposition (ugropy): counts, r and q for one molecule.

    This is the inventory view. Use ``unifac_gamma`` (or
    ``unifac_gamma_infinity``) for actual activity coefficients.
    """
    from ugropy import unifac

    try:
        result = unifac.get_groups(smiles, "smiles")
    except Exception as exc:  # ugropy raises several types for a bad structure
        raise ValueError(f"UNIFAC decomposition failed: {exc}") from exc
    return {
        "smiles": smiles,
        "subgroups": dict(result.subgroups),
        "r": round(result.r, 4),
        "q": round(result.q, 4),
        "source": "ugropy 3.2.5, UNIFAC subgroup table",
        "note": "Groups and r/q from original UNIFAC. Activity coefficients: "
        "unifac_gamma / unifac_gamma_infinity.",
    }


def _unifac_model():
    import unifac_gamma as model

    return model


@MCP.tool()
def unifac_gamma(
    smiles: list[str],
    mole_fractions: list[float],
    temperature: float = 298.15,
    version: int = 1,
) -> dict:
    """UNIFAC activity coefficients (gamma) for a liquid mixture, offline.

    version 1 = Dortmund UNIFAC (default, recommended), 0 = original UNIFAC.
    No LLM, no solvent data, no side claim: gamma only.
    """
    model = _unifac_model()
    try:
        values = model.gamma(
            list(smiles), list(mole_fractions), temperature=float(temperature), version=int(version)
        )
    except ValueError as exc:
        return {"error": str(exc), "value": None, "unit": "gamma (dimensionless)"}
    return {
        "value": values,
        "unit": "gamma (dimensionless)",
        "temperature_K": float(temperature),
        "model": model.describe(int(version))["model"],
        "note": UNIFAC_NOTE,
    }


@MCP.tool()
def unifac_gamma_infinity(
    smiles: list[str], temperature: float = 298.15, version: int = 1
) -> dict:
    """UNIFAC activity coefficients at infinite dilution, offline.

    Entry k is solute k infinitely diluted in the last entry of ``smiles``.
    """
    model = _unifac_model()
    try:
        values = model.gamma_inf(list(smiles), temperature=float(temperature), version=int(version))
    except ValueError as exc:
        return {"error": str(exc), "value": None, "unit": "gamma (dimensionless)"}
    return {
        "value": values,
        "unit": "gamma-infinity (dimensionless)",
        "temperature_K": float(temperature),
        "solvent": smiles[-1],
        "model": model.describe(int(version))["model"],
        "note": UNIFAC_NOTE,
    }


@MCP.tool()
def kj_ask(request: str, payload: dict | None = None, plan_only: bool = False) -> dict:
    """One call: plan -> gate -> engine -> answer contract -> ledger (P5a/P5d).

    ``plan_only=True`` keeps the old dry behaviour: it says which engine, gate
    and unit would be used and produces no number. Otherwise the answer is
    computed, gated, stored in the append-only ledger and returned; a refusal is
    a normal result with ``value = None`` and a fixed sentence.
    """
    if plan_only:
        from router import plan

        return plan(request, payload)

    from pipeline import ask

    return ask(request, payload)


@MCP.tool()
def kj_replay(entry_id: str, recompute: bool = True) -> dict:
    """Replay one ledger entry; with ``recompute`` the number is re-derived.

    Without ``recompute`` the plan, gate and stored-answer digest are checked and
    ``value_same`` is ``None`` (never a fake True). With it, the number is
    compared within ``ledger.VALUE_REL_TOL``/``VALUE_ABS_TOL``.
    """
    from ledger import replay
    from pipeline import compute as compute_answer

    compute = (
        (lambda entry: compute_answer(entry["request"], entry.get("payload"))[1])
        if recompute
        else None
    )
    return replay(entry_id, compute=compute)


@MCP.tool()
def kj_recipe(
    recipe: dict | str,
    markdown: bool = False,
    check_http: bool = False,
) -> dict:
    """Audit a procedure document against the kj-recipe/1 contract (P1).

    ``recipe`` is either a path to a recipe JSON (repo-relative or absolute) or
    the document itself. The tool checks the source ids, the mandatory claim
    boundary, the atom balance of a declared equation and the Turkish mirror.
    It never computes chemistry and returns no number: a failure is a normal
    result, ``verdict = "RED"`` with the reason, not an exception.

    ``markdown=True`` adds the rendered document; ``check_http=True`` fetches
    every cited URL (a 403 is reported as a bot wall, not as a dead page).
    """
    from recipe import RecipeError, check_urls, load, render_markdown, validate

    try:
        doc = load(recipe) if isinstance(recipe, str) else recipe
        report = validate(doc)
    except RecipeError as exc:
        return {"schema": "kj-recipe/1", "verdict": "RED", "reason": str(exc)}
    if check_http:
        report["http"] = check_urls(doc)
    if markdown:
        report["markdown"] = render_markdown(doc)
    return report


if __name__ == "__main__":
    MCP.run()
