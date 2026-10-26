"""Ideal-solution wax melting range for n-alkane mixtures (offline).

Ideal solid-liquid equilibrium: component i crystallises when
ln(x_i) = -dH_fus,i / R * (1/T - 1/Tm,i).
Activity coefficients are set to 1, so this is a YELLOW model: ranges only.

Run with .venv_inventory\\Scripts\\python.exe tools\\wax_melting.py
"""
import math

from chemicals import Hfus, Tm

R = 8.314462618


def component_temperature(casrn: str, x: float) -> float:
    """Temperature at which this component starts to crystallise."""
    if not 0.0 < x <= 1.0:
        raise ValueError("mole fraction must be in (0, 1]")
    tm = Tm(CASRN=casrn)
    dh = Hfus(CASRN=casrn)
    if tm is None or dh is None:
        raise ValueError(f"missing Tm or Hfus for CAS {casrn}")
    if x == 1.0:
        return float(tm)
    return 1.0 / (1.0 / tm - R * math.log(x) / dh)


def wax_range(components: dict) -> dict:
    """Wax appearance and last-solid temperatures for a mole-fraction mixture."""
    total = sum(components.values())
    if total <= 0:
        raise ValueError("fractions must sum to a positive number")
    rows = []
    for cas, value in components.items():
        x = value / total
        rows.append({"casrn": cas, "x": round(x, 4),
                     "t_k": round(component_temperature(cas, x), 1)})
    temps = [row["t_k"] for row in rows]
    return {
        "components": rows,
        "wax_appearance_k": max(temps),
        "last_solid_k": min(temps),
        "range_k": round(max(temps) - min(temps), 1),
        "model": "ideal solid-liquid equilibrium, gamma = 1",
        "limits": "YELLOW: ranges only. No activity coefficients, no rheology, "
        "no wax content, no performance claim.",
    }


if __name__ == "__main__":
    demo = {"112-95-8": 0.5, "646-31-1": 0.3, "630-02-4": 0.2}
    result = wax_range(demo)
    for row in result["components"]:
        print(row["casrn"], row["x"], row["t_k"])
    print("wax_appearance_K", result["wax_appearance_k"])
    print("last_solid_K", result["last_solid_k"])
