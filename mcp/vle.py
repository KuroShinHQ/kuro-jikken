"""V1: binary vapour-liquid equilibrium at a fixed pressure, and its azeotrope.

Model, not a measurement: modified Raoult's law with

* ``gamma(x, T)`` from Dortmund UNIFAC (``tools/unifac_gamma.py``, DOUFIP2016),
* ``Psat(T)`` from thermo 0.6.1's pure-component correlation.

What it is validated against (``docs/VLE.md``):

    ethanol/water       351.40 K vs 351.32 K literature  (+0.08 K), x 0.894 vs 0.894
    propan-2-ol/water   353.52 K vs 353.52 K literature  ( 0.00 K), x 0.680 vs 0.681
    methanol/water      no azeotrope at 1 atm (negative control)

A pair outside that table is a model prediction, not a validated number: the
gate says YELLOW and the answer says so in ``limits``. No ternary mixtures, no
pressure sweep, no distillation design, no ranking.
"""
from __future__ import annotations

import pathlib
import sys

_TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

SCHEMA = "kj-vle/1"
DEFAULT_PRESSURE_PA = 101325.0
T_MIN_K = 250.0
T_MAX_K = 500.0
DECLARED_BAR_K = 0.5

# pairs whose azeotrope was compared with literature (docs/VLE.md)
VALIDATED = {
    ("ethanol", "water"),
    ("2-propanol", "water"),
}

_cache: dict[str, object] = {}


class VleError(Exception):
    """A clean refusal reason; the adapter turns it into a fixed sentence."""


def _normalise(name: str) -> str:
    return " ".join(str(name).strip().lower().replace("_", " ").split())


def _chem(name: str):
    from thermo import Chemical

    key = _normalise(name)
    if key not in _cache:
        try:
            _cache[key] = Chemical(name)
        except Exception as exc:  # thermo raises several unrelated types
            raise VleError(
                f"component {name!r} not found in the thermo database "
                f"({type(exc).__name__})"
            ) from exc
    return _cache[key]


def pair_key(components) -> tuple:
    """Normalised (a, b) key used to look a pair up in VALIDATED."""
    return tuple(_normalise(c) for c in components)


def psat(name: str, temperature_k: float) -> float:
    chemical = _chem(name)
    chemical.T = float(temperature_k)
    return float(chemical.Psat)


def pure_boiling_point(name: str, pressure_pa: float = DEFAULT_PRESSURE_PA) -> float:
    """Temperature at which the pure component reaches ``pressure_pa``."""
    lo, hi = T_MIN_K, T_MAX_K
    if psat(name, lo) > pressure_pa or psat(name, hi) < pressure_pa:
        raise VleError(f"no boiling point for {name!r} inside {T_MIN_K:.0f}-{T_MAX_K:.0f} K")
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if psat(name, mid) < pressure_pa:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _gamma(smiles, xs, temperature_k):
    import unifac_gamma as U

    try:
        return U.gamma(list(smiles), list(xs), temperature=float(temperature_k), version=1)
    except (U.MissingInteraction, U.UnsupportedGroup) as exc:
        raise VleError(str(exc)) from exc


def bubble_temperature(names, smiles, x1: float, pressure_pa: float) -> float:
    """Temperature where sum(x_i gamma_i Psat_i) = P at fixed liquid composition."""

    def residual(temperature_k: float) -> float:
        xs = [x1, 1.0 - x1]
        gammas = _gamma(smiles, xs, temperature_k)
        total = sum(
            xs[i] * gammas[i] * psat(names[i], temperature_k) for i in range(2)
        )
        return total - pressure_pa

    lo, hi = T_MIN_K, T_MAX_K
    f_lo, f_hi = residual(lo), residual(hi)
    if f_lo > 0 or f_hi < 0:
        raise VleError(
            f"no bubble point at x({names[0]}) = {x1:.2f} inside {T_MIN_K:.0f}-{T_MAX_K:.0f} K"
        )
    for _ in range(35):
        mid = 0.5 * (lo + hi)
        if residual(mid) > 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def _y1(names, smiles, x1: float, temperature_k: float, pressure_pa: float) -> float:
    xs = [x1, 1.0 - x1]
    gammas = _gamma(smiles, xs, temperature_k)
    return xs[0] * gammas[0] * psat(names[0], temperature_k) / pressure_pa


def azeotrope(
    components,
    pressure_pa: float = DEFAULT_PRESSURE_PA,
    step: float = 0.04,
) -> dict:
    """Scan x1, then bisect where y1 - x1 changes sign.

    Returns ``azeotrope: False`` (no number) when the pair is zeotropic.
    """
    names = [str(c).strip() for c in (components or [])]
    if len(names) != 2 or not all(names):
        raise VleError("a binary VLE needs exactly two component names")
    if not 0.01 <= float(step) <= 0.2:
        raise VleError("step must be between 0.01 and 0.2")

    smiles = [_chem(name).smiles for name in names]
    if not all(smiles):
        raise VleError("thermo returned no SMILES for at least one component")

    pressure_pa = float(pressure_pa)
    pure = [pure_boiling_point(name, pressure_pa) for name in names]

    previous = None
    for k in range(1, int(round(1.0 / step))):
        x1 = k * step
        temperature_k = bubble_temperature(names, smiles, x1, pressure_pa)
        delta = _y1(names, smiles, x1, temperature_k, pressure_pa) - x1
        if delta == 0.0:
            return _result(names, smiles, pressure_pa, pure, x1, temperature_k)
        if previous is not None and previous[1] * delta < 0:
            low, high = previous[0], x1
            for _ in range(45):
                mid = 0.5 * (low + high)
                temperature_mid = bubble_temperature(names, smiles, mid, pressure_pa)
                delta_mid = _y1(names, smiles, mid, temperature_mid, pressure_pa) - mid
                if previous[1] * delta_mid <= 0:
                    high = mid
                else:
                    low = mid
            x_azeo = 0.5 * (low + high)
            temperature_azeo = bubble_temperature(names, smiles, x_azeo, pressure_pa)
            return _result(names, smiles, pressure_pa, pure, x_azeo, temperature_azeo)
        previous = (x1, delta)

    return {
        "schema": SCHEMA,
        "components": names,
        "smiles": smiles,
        "pressure_pa": pressure_pa,
        "azeotrope": False,
        "temperature_k": None,
        "x1": None,
        "y1": None,
        "pure_boiling_k": pure,
        "method": "modified Raoult + Dortmund UNIFAC gamma(x,T) + thermo Psat",
        "grid_step": float(step),
    }


def _result(names, smiles, pressure_pa, pure, x1, temperature_k) -> dict:
    return {
        "schema": SCHEMA,
        "components": names,
        "smiles": smiles,
        "pressure_pa": pressure_pa,
        "azeotrope": True,
        "temperature_k": float(temperature_k),
        "x1": float(x1),
        "y1": float(_y1(names, smiles, x1, temperature_k, pressure_pa)),
        "pure_boiling_k": pure,
        "method": "modified Raoult + Dortmund UNIFAC gamma(x,T) + thermo Psat",
        "grid_step": None,
    }


if __name__ == "__main__":
    import json
    import sys

    pair = sys.argv[1:] or ["ethanol", "water"]
    print(json.dumps(azeotrope(pair), ensure_ascii=False, indent=2))
