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


GATES = {
    "gate.structure": gate_structure,
    "gate.esol": gate_esol,
    "gate.unifac": gate_unifac,
    "gate.hsp": gate_hsp,
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


