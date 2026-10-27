"""Liquidus temperature of an aluminium alloy from a MatCalc TDB (pycalphad).

Run with .venv_inventory\\Scripts\\python.exe tools\\alloy_liquidus.py
The database is not in this repository (ODbL share-alike); KJ_TDB_DIR points
at the folder that holds the pycalphad-ready files.
"""
import os
import pathlib

import pycalphad.variables as v
from pycalphad import Database, equilibrium

TDB = pathlib.Path(
    os.environ.get("KJ_TDB_DIR", r"C:\KuroshinHQ\_hub\data\alloy_tdb_mgf")
)
PHASES = ["LIQUID", "FCCAL", "THETA_AL2CU", "ALCU_E", "ALCU_ETA", "AL2CU3_D", "AL9CU11_Z"]


def liquidus(
    db: Database,
    x_cu: float,
    low: float = 600.0,
    high: float = 950.0,
    with_bracket: bool = False,
):
    """Temperature at which the last solid disappears (bisection, 9 steps).

    The bracket is checked first: if the alloy is not solid at ``low`` or still
    solid at ``high``, the bisection has no answer and this raises instead of
    returning the bracket edge (2026-10-27: x_Cu = 0 used to return 600.34 K).

    ``with_bracket=True`` returns ``(value, bracket_width_k)``. The width is the
    numerical resolution of the bisection, **not** a model or database error.
    """

    def solid(temperature: float) -> bool:
        result = equilibrium(
            db, ["AL", "CU", "VA"], PHASES,
            {v.T: temperature, v.P: 101325, v.X("CU"): x_cu},
        )
        names = result.Phase.values.squeeze().tolist()
        amounts = result.NP.values.squeeze().tolist()
        return any(n and n != "LIQUID" and a > 1e-6 for n, a in zip(names, amounts))

    if not 0.0 < x_cu < 1.0:
        raise ValueError(f"x_Cu must be strictly between 0 and 1 (got {x_cu}); use the pure-element path")
    if not solid(low):
        raise ValueError(f"no solid phase at {low} K for x_Cu = {x_cu}: bracket starts above the solidus")
    if solid(high):
        raise ValueError(f"still solid at {high} K for x_Cu = {x_cu}: bracket ends below the liquidus")

    lo, hi = low, high
    for _ in range(9):
        mid = (lo + hi) / 2.0
        if solid(mid):
            lo = mid
        else:
            hi = mid
    value = (lo + hi) / 2.0
    if with_bracket:
        return value, hi - lo
    return value


def main() -> None:
    db = Database(str(TDB / "mc_al_v2.032.pycalphad.tdb"))
    for x in (0.01, 0.05, 0.10, 0.173):
        print(f"x_Cu {x:.3f} liquidus_K {liquidus(db, x):.1f}")


if __name__ == "__main__":
    main()
