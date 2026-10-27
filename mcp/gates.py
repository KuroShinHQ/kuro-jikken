"""Applicability gates: run BEFORE any number, return PASS / YELLOW / RED + reason.

Each gate is a pure function over already-resolved identifiers, so it can be
tested without an engine call. A gate never computes a property.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))


def _out(verdict, reason, **extra):
    return {"verdict": verdict, "pass": verdict != "RED", "reason": reason, **extra}


def gate_structure(smiles: str) -> dict:
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return _out("RED", "SMILES does not parse")
    if len(Chem.GetMolFrags(mol)) > 1:
        return _out("RED", "multi-component SMILES; give one neutral molecule")
    return _out("PASS", "single neutral fragment")


def gate_esol(smiles: str) -> dict:
    from esol import domain_classify

    d = domain_classify(smiles)
    if not d.get("ok"):
        return _out("RED", d.get("error", "ESOL could not read the structure"))
    if d["in_domain"]:
        return _out("PASS", "ESOL in domain", error_bar_logS=1.2)
    return _out("YELLOW", "; ".join(d["domain_reasons"]), error_bar_logS=5.0)


def gate_unifac(smiles_list) -> dict:
    import unifac_gamma as U

    if isinstance(smiles_list, str):
        smiles_list = smiles_list.split()
    if not isinstance(smiles_list, (list, tuple)) or len(smiles_list) < 2:
        return _out("RED", "a mixture gate needs at least two SMILES")
    try:
        U.gamma_inf(list(smiles_list), version=1)
    except (U.MissingInteraction, U.UnsupportedGroup) as exc:
        return _out("RED", str(exc))
    except Exception as exc:  # a gate must refuse cleanly, never crash
        return _out("RED", f"gate could not run: {type(exc).__name__}: {exc}")
    return _out("PASS", "groups and main-group pairs present (Dortmund)")


def gate_hsp(casrn: str) -> dict:
    from chemicals import hansen_delta_d

    if hansen_delta_d(casrn) is None:
        return _out("RED", f"no Hansen entry for CAS {casrn} (mixtures such as petrolatum have none)")
    return _out("PASS", "Hansen entry present", note="ranking only")


_SIGMA_KEYS = None


def gate_cosmo(inchikey: str) -> dict:
    """InChIKey must exist in the PubChemQC sigma index; charged species are out."""
    global _SIGMA_KEYS
    import os

    import pandas as pd

    path = pathlib.Path(os.environ.get("KURO_SIGMA_DIR", r"C:\KuroshinHQ\_hub\data\formulation_sigma")) / "sigma_profile_index.parquet"
    if _SIGMA_KEYS is None:
        if not path.is_file():
            return _out("RED", f"sigma index not found: {path}")
        _SIGMA_KEYS = set(pd.read_parquet(path, columns=["InChIKey"])["InChIKey"])
    if not isinstance(inchikey, str) or len(inchikey) != 27:
        return _out("RED", "not an InChIKey")
    if inchikey not in _SIGMA_KEYS:
        return _out("RED", "molecule is outside PubChemQC sigma coverage")
    return _out("PASS", "sigma profile exists for this InChIKey")


def _tdb_dir() -> pathlib.Path:
    import os

    return pathlib.Path(
        os.environ.get("KJ_TDB_DIR", r"C:\KuroshinHQ\_hub\data\alloy_tdb_mgf")
    )


def gate_calphad(payload) -> dict:
    """TDB must exist and declare every element the request needs.

    ``payload`` is ``{"tdb": "mc_al_v2.032.pycalphad.tdb", "elements": ["AL", "CU"]}``
    or a plain TDB name (coverage then only reported, not checked).
    """
    if isinstance(payload, dict):
        name = payload.get("tdb") or payload.get("database")
        elements = payload.get("elements") or []
    elif isinstance(payload, str):
        name, elements = payload, []
    else:
        return _out("RED", "calphad gate needs a TDB name and an element list")
    if not name:
        return _out("RED", "no TDB file named")

    base = _tdb_dir()
    path = (base / pathlib.Path(str(name)).name).resolve()
    if path.parent != base.resolve() or not path.is_file():
        return _out("RED", f"TDB not found: {name} (looked in {base})")

    declared = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].upper() == "ELEMENT":
            declared.add(parts[1].upper())
    declared.discard("VA")

    wanted = {str(e).strip().upper() for e in elements if str(e).strip()}
    if not wanted:
        return _out(
            "YELLOW",
            f"database exists but coverage was not checked ({path.name})",
            elements=sorted(declared),
        )
    missing = sorted(wanted - declared)
    if missing:
        return _out("RED", f"{path.name} has no ELEMENT entry for {', '.join(missing)}")
    return _out("PASS", f"all elements declared in {path.name}", elements=sorted(wanted))


def gate_wax(casrn_list) -> dict:
    """Melting-range model needs both Tm and Hfus for every component.

    Wax mixtures (petrolatum 8009-03-8, paraffin 8002-74-2) carry Tm but no Hfus
    in the ``chemicals`` table, so they are refused instead of guessed.
    """
    from chemicals import Hfus, Tm

    if isinstance(casrn_list, dict):
        inner = casrn_list.get("casrn") or casrn_list.get("components")
        casrn_list = inner if inner else list(casrn_list.keys())
    if isinstance(casrn_list, str):
        casrn_list = [c for c in casrn_list.replace(",", " ").split() if c]
    if not isinstance(casrn_list, (list, tuple)) or not casrn_list:
        return _out("RED", "wax gate needs at least one CAS number")

    gaps = []
    for casrn in casrn_list:
        missing = []
        if Tm(casrn) is None:
            missing.append("Tm")
        if Hfus(casrn) is None:
            missing.append("Hfus")
        if missing:
            gaps.append(f"{casrn} ({'/'.join(missing)})")
    if gaps:
        return _out(
            "RED",
            "no melting data for " + ", ".join(gaps) + " (wax mixtures have no Hfus)",
        )
    return _out(
        "PASS",
        "Tm and Hfus present for every component",
        note="melting range only; no performance claim",
    )


def gate_vle(payload) -> dict:
    """Binary VLE: two known components, and whether this pair was validated."""
    import vle as V

    if not isinstance(payload, dict):
        return _out("RED", "a binary VLE gate needs a payload with components")
    components = payload.get("components")
    if isinstance(components, str):
        components = components.replace(",", " ").split()
    if not isinstance(components, (list, tuple)) or len(components) != 2:
        return _out("RED", "a binary VLE gate needs exactly two components")
    try:
        for name in components:
            V.psat(name, 350.0)
    except V.VleError as exc:
        return _out("RED", str(exc))
    except Exception as exc:  # a gate must refuse cleanly, never crash
        return _out("RED", f"component could not be read: {type(exc).__name__}: {exc}")
    pressure = float(payload.get("pressure_pa") or V.DEFAULT_PRESSURE_PA)
    pair = V.pair_key(components)
    if pair in V.VALIDATED:
        if abs(pressure - V.DEFAULT_PRESSURE_PA) > 1.0:
            return _out("YELLOW", "validated at 1 atm; this pressure is extrapolation")
        return _out("PASS", f"validated against literature: {pair[0]}/{pair[1]} (docs/VLE.md)")
    return _out("YELLOW", "model not validated for this pair (docs/VLE.md)")


GATES = {
    "gate.structure": gate_structure,
    "gate.esol": gate_esol,
    "gate.unifac": gate_unifac,
    "gate.hsp": gate_hsp,
    "gate.cosmo": gate_cosmo,
    "gate.calphad": gate_calphad,
    "gate.wax": gate_wax,
    "gate.vle": gate_vle,
}


def check(gate_id: str, payload):
    """Run one gate by id; unknown gate id is a RED, never a silent pass."""
    fn = GATES.get(gate_id)
    if fn is None:
        return _out("RED", f"no gate named {gate_id}")
    try:
        return fn(payload)
    except Exception as exc:  # a gate must refuse cleanly, never crash
        return _out("RED", f"gate crashed: {type(exc).__name__}: {exc}")


