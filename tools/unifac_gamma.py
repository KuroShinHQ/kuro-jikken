"""UNIFAC activity coefficients (gamma) for liquid mixtures (offline).

Groups come from ugropy (MIT); subgroup r/q and the interaction matrices come
from thermo 0.6.1 (MIT). Two published parameter sets are exposed:

  version=0  original UNIFAC (Fredenslund 1975, Hansen 1991 table, UFIP)
  version=1  Dortmund UNIFAC (Gmehling, DOUFIP2016, temperature dependent)

Default is version=1. Validation against measured infinite-dilution values in
water (Straver & de Loos 2005, J. Chem. Eng. Data 50, 1171,
doi:10.1021/je0495942) is in docs/GAMMA_VALIDATION.md: Dortmund stays inside
about +/-25 % for alcohols and ketones, original UNIFAC overshoots by +50..+110 %.

Two guards exist because a wrong number is worse than no number:

* ``UnsupportedGroup``  - ugropy produced a subgroup name the parameter table
  does not know (a silent name mismatch would use the wrong group).
* ``MissingInteraction`` - the main-group pair is absent from the parameter
  table. thermo fills the hole with a zero interaction, which turns a
  hydrophobic solute into a near-ideal one; we refuse to return that.

Run with .venv_inventory\\Scripts\\python.exe tools\\unifac_gamma.py
"""
from __future__ import annotations

from ugropy import dortmund as ug_dortmund
from ugropy import unifac as ug_unifac
from thermo.unifac import DOUFIP2016, DOUFSG, UFIP, UFSG, UNIFAC

DEFAULT_VERSION = 1

# version -> (label, subgroup table, interaction table, ugropy grouping module)
VERSIONS = {
    0: ("original UNIFAC (Fredenslund 1975; UFIP)", UFSG, UFIP, ug_unifac),
    1: ("Dortmund UNIFAC (Gmehling; DOUFIP2016)", DOUFSG, DOUFIP2016, ug_dortmund),
}

# ugropy and thermo do not spell every subgroup the same way.
NAME_ALIASES = {"HCO": "CHO", "OH (P)": "OH(P)", "OH (S)": "OH(S)", "OH (T)": "OH(T)"}


class UnsupportedGroup(ValueError):
    """A subgroup name that the chosen parameter table does not contain."""


class MissingInteraction(ValueError):
    """A main-group pair that the chosen parameter table does not contain."""


def _normalise(name: str) -> str:
    name = name.replace(" (", "(").strip()
    return NAME_ALIASES.get(name, name)


def _table(version: int):
    try:
        return VERSIONS[version]
    except KeyError as exc:
        raise ValueError(f"version must be one of {sorted(VERSIONS)}") from exc


def _by_name(table, version: int) -> dict:
    """Name -> subgroup object for one table, refusing ambiguous names.

    thermo's tables spell two different subgroups 'CHO' (the aldehyde, main
    group CHO, and a CH2O unit, main group CH2O). Picking one silently changes
    the molecule, so the main-group name breaks the tie; any other conflict is
    an error.
    """
    buckets = {}
    for obj in table.values():
        buckets.setdefault(_normalise(obj.group), []).append(obj)
    out = {}
    for name, items in buckets.items():
        if len(items) == 1:
            out[name] = items[0]
            continue
        exact = [obj for obj in items if _normalise(obj.main_group) == name]
        if len(exact) == 1:
            out[name] = exact[0]
            continue
        raise UnsupportedGroup(
            f"subgroup name {name!r} is ambiguous in the version {version} table "
            f"({[obj.group_id for obj in items]}); refusing to guess"
        )
    return out


def subgroups(smiles: str, version: int = DEFAULT_VERSION) -> dict:
    """UNIFAC subgroup counts for one SMILES, as the chosen table spells them."""
    _, table, _, grouper = _table(version)
    known = _by_name(table, version)
    result = grouper.get_groups(smiles, "smiles")
    counts = {}
    for name, count in dict(result.subgroups).items():
        if not count:
            continue
        key = _normalise(name)
        if key not in known:
            raise UnsupportedGroup(
                f"subgroup {name!r} (normalised {key!r}) is not in the version "
                f"{version} table"
            )
        counts[key] = counts.get(key, 0) + int(count)
    if not counts:
        raise UnsupportedGroup(f"no UNIFAC subgroups found for {smiles!r}")
    return counts


def _chemgroups(smiles_list, version):
    """Subgroup ids per molecule, plus the set of main groups involved."""
    _, table, _, _ = _table(version)
    by_name = _by_name(table, version)
    out = []
    mains = set()
    for smiles in smiles_list:
        groups = subgroups(smiles, version)
        ids = {}
        for name, count in groups.items():
            obj = by_name[name]
            ids[obj.group_id] = ids.get(obj.group_id, 0) + count
            mains.add(obj.main_group_id)
        out.append(ids)
    return out, mains


def _check_pairs(mains, version):
    """Refuse to run when the interaction matrix has a hole for this mixture."""
    _, _, interactions, _ = _table(version)
    for a in sorted(mains):
        for b in sorted(mains):
            if a == b:
                continue
            if b not in interactions.get(a, {}) or a not in interactions.get(b, {}):
                raise MissingInteraction(
                    f"no UNIFAC interaction for main groups {a}/{b} in version "
                    f"{version}; the pair is missing from the published table, so "
                    "no gamma is returned"
                )


def _model(smiles_list, xs, temperature, version):
    if len(smiles_list) != len(xs) or not smiles_list:
        raise ValueError("smiles and mole fractions must have the same, non-zero length")
    if any(x < 0 for x in xs) or sum(xs) <= 0:
        raise ValueError("mole fractions must be non-negative and sum above zero")
    total = sum(xs)
    fractions = [float(x) / total for x in xs]
    chemgroups, mains = _chemgroups(smiles_list, version)
    _check_pairs(mains, version)
    return UNIFAC.from_subgroups(
        float(temperature), fractions, chemgroups, version=version
    )


def gamma(smiles_list, xs, temperature: float = 298.15, version: int = DEFAULT_VERSION):
    """Activity coefficients for a mixture of SMILES at mole fractions xs."""
    model = _model(smiles_list, xs, temperature, version)
    return [round(float(g), 4) for g in model.gammas()]


def gamma_inf(smiles_list, temperature: float = 298.15, version: int = DEFAULT_VERSION):
    """Activity coefficients at infinite dilution (first entry = first solute)."""
    xs = [0.0] * len(smiles_list)
    xs[-1] = 1.0
    model = _model(smiles_list, xs, temperature, version)
    return [round(float(g), 4) for g in model.gammas_infinite_dilution()]


def describe(version: int = DEFAULT_VERSION) -> dict:
    """Provenance block for reports and the MCP tool."""
    label, table, interactions, _ = _table(version)
    return {
        "version": version,
        "model": label,
        "subgroups": len(table),
        "interaction_pairs": sum(len(row) for row in interactions.values()),
        "source": "ugropy groups + thermo 0.6.1 UNIFAC matrices (MIT)",
    }


if __name__ == "__main__":
    for version in sorted(VERSIONS):
        print(describe(version))
        print("  ethanol/water 0.5/0.5 :", gamma(["CCO", "O"], [0.5, 0.5], version=version))
        print("  gamma-inf ethanol/water:", gamma_inf(["CCO", "O"], version=version))
