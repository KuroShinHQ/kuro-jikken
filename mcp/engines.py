"""P5a engine adapters: a gate-passed plan becomes exactly one answer dict.

Each adapter is a pure function ``(request, plan, payload) -> answer``. It may
only return what ``answer.build`` accepts or a fixed refusal carrying the
engine's own reason; it never writes the ledger and never invents a number.
Heavy libraries (pycalphad, RDKit, pandas) are imported inside the adapter so
that importing this module stays cheap.

Adapters exist only for capabilities whose engine is validated today:
solubility.aqueous (ESOL), mixture.gamma (UNIFAC Dortmund), alloy.phase
(pycalphad) and molecule.identity (RDKit). ``mixture.wax`` has a gate but no
engine, so it is refused before any adapter is reached.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
for _path in (HERE, HERE.parent / "tools"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import answer as A  # noqa: E402

# validated model error bars, quoted from the locked-set evaluations
ESOL_IN_DOMAIN_BAR = 1.2  # log units, validation/solubility/KARNE.md
UNIFAC_RELATIVE_BAR = 0.30  # +/-30 %: literature comparison, DEVAM 238 (median 21 %)


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [part for part in value.replace(",", " ").split() if part]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value)]


def smiles_list(payload):
    """Every SMILES the payload carries, in order (mixture = order matters)."""
    if isinstance(payload, str):
        return _as_list(payload)
    if not isinstance(payload, dict):
        return []
    for key in ("smiles", "smiles_list", "components"):
        found = _as_list(payload.get(key))
        if found:
            return found
    return []


def _float(payload, key, default=None):
    if not isinstance(payload, dict) or payload.get(key) is None:
        return default
    return float(payload[key])


def reproduce_command(request: str, payload) -> str:
    """The exact command that recomputes this answer (no ledger write)."""
    parts = ["python", "tools/ask.py", json.dumps(request, ensure_ascii=False)]
    if payload is not None:
        parts += ["--payload", json.dumps(payload, ensure_ascii=False, sort_keys=True)]
    return " ".join(parts) + " --no-write"


def _verdict(gate) -> str:
    return "GREEN" if (gate or {}).get("verdict") == "PASS" else "YELLOW"


def esol(request, plan, payload):
    """Aqueous solubility (logS) from the published ESOL coefficients."""
    from esol import esol_published

    smiles = smiles_list(payload)
    gate = plan.get("gate")
    if not smiles:
        return A.refusal(
            "no data",
            capability="solubility.aqueous",
            reason="no SMILES for the solubility engine",
            gate=gate,
        )
    out = esol_published(smiles[0])
    if not out.get("ok"):
        return A.refusal(
            "out of domain",
            capability="solubility.aqueous",
            reason=out.get("error"),
            gate=gate,
        )
    if (gate or {}).get("verdict") != "PASS":
        reasons = out.get("domain_reasons") or [str((gate or {}).get("reason", "gate not PASS"))]
        return A.refusal(
            "out of domain",
            capability="solubility.aqueous",
            reason="; ".join(reasons),
            gate=gate,
        )
    value = float(out["value"])
    bar = float(out.get("error_bar_logS", ESOL_IN_DOMAIN_BAR))
    return A.build(
        capability="solubility.aqueous",
        value=value,
        unit="logS",
        method="ESOL (Delaney 2004): Crippen logP, MW, rotatable bonds, aromatic proportion",
        verdict=_verdict(gate),
        provenance={
            "engine": "ESOL (Delaney 2004)",
            "dataset": f"mcp/esol.py coefficients; RDKit {out.get('rdkit_version', 'unknown')}",
        },
        reproduce=reproduce_command(request, payload),
        does_not_say=(
            "measured solubility, pH dependence, salt effects, or any temperature "
            "other than 25 C"
        ),
        error={"kind": "model", "lower": value - bar, "upper": value + bar},
        limits=[
            "neutral single-component organic molecules in water at 25 C",
            f"model error bar {bar} log units (locked-set RMSE)",
        ],
        gate=gate,
    )


def unifac(request, plan, payload):
    """Activity coefficient from UNIFAC Dortmund: gamma(x) or gamma-infinity."""
    import unifac_gamma as U

    smiles = smiles_list(payload)
    gate = plan.get("gate")
    if len(smiles) < 2:
        return A.refusal(
            "no data",
            capability="mixture.gamma",
            reason="a mixture needs at least two SMILES (solute first, solvent last)",
            gate=gate,
        )
    temperature = _float(payload, "temperature", 298.15)
    raw_xs = _as_list(payload.get("xs") if isinstance(payload, dict) else None)
    xs = [float(x) for x in raw_xs]
    try:
        if xs:
            values = U.gamma(smiles, xs, temperature=temperature, version=1)
            what = f"gamma at mole fractions {xs} (first component)"
        else:
            values = U.gamma_inf(smiles, temperature=temperature, version=1)
            what = "gamma-infinity (first component as solute, last as solvent)"
    except (U.MissingInteraction, U.UnsupportedGroup) as exc:
        return A.refusal(
            "missing parameters",
            capability="mixture.gamma",
            reason=str(exc),
            gate=gate,
        )
    except ValueError as exc:
        return A.refusal(
            "missing parameters",
            capability="mixture.gamma",
            reason=f"{type(exc).__name__}: {exc}",
            gate=gate,
        )
    value = float(values[0])
    model = U.describe(1)
    return A.build(
        capability="mixture.gamma",
        value=value,
        unit="gamma",
        method=f"UNIFAC Dortmund (version 1): {what}",
        verdict=_verdict(gate),
        provenance={
            "engine": "UNIFAC Dortmund (thermo 0.6.1)",
            "dataset": f"{model['model']}; {model['subgroups']} subgroups, {model['interaction_pairs']} pairs",
        },
        reproduce=reproduce_command(request, payload),
        does_not_say=(
            "phase split, azeotropes or VLE; the value is an activity coefficient at "
            "the stated composition and temperature only"
        ),
        error={
            "kind": "model",
            "lower": value * (1.0 - UNIFAC_RELATIVE_BAR),
            "upper": value * (1.0 + UNIFAC_RELATIVE_BAR),
        },
        limits=[
            "validated to about +/-30 % against measured aqueous gamma-infinity "
            "(median 21 %, 7 of 9 within +/-30 %)",
            f"temperature fixed at {temperature} K; composition fixed as stated",
        ],
        gate=gate,
    )


def _al_cu_mole_fraction(wt_pct: float) -> float:
    """Cu wt% -> mole fraction, average atomic weights (Cu 63.546, Al 26.9815)."""
    cu = wt_pct / 63.546
    al = (100.0 - wt_pct) / 26.9815
    return cu / (cu + al)


def calphad(request, plan, payload):
    """Melting / liquidus temperature from a CALPHAD database (K)."""
    import calphad_engine as C

    gate = plan.get("gate")
    if not isinstance(payload, dict):
        return A.refusal(
            "missing parameters",
            capability="alloy.phase",
            reason="the CALPHAD engine needs a payload with a TDB name",
            gate=gate,
        )
    tdb = payload.get("tdb") or payload.get("database")
    if not tdb:
        return A.refusal(
            "no data",
            capability="alloy.phase",
            reason="no TDB file named",
            closest="mc_al_v2.032 / mc_fe_v2.059 / mc_ni_v2.034 (name one in the payload)",
            gate=gate,
        )
    low = _float(payload, "low_k", 600.0)
    high = _float(payload, "high_k", 950.0)
    try:
        if payload.get("x_cu") is not None or payload.get("cu_wt_pct") is not None:
            from pycalphad import Database

            from alloy_liquidus import liquidus

            if payload.get("x_cu") is not None:
                x_cu = float(payload["x_cu"])
                basis = f"mole fraction x(Cu) = {x_cu}"
            else:
                wt = float(payload["cu_wt_pct"])
                x_cu = _al_cu_mole_fraction(wt)
                basis = f"{wt} wt% Cu = mole fraction x(Cu) = {x_cu:.5f}"
            path = C.tdb_path(str(tdb))
            value = float(liquidus(Database(str(path)), x_cu, low=low, high=high))
            method = "pycalphad equilibrium + bisection (9 steps), Al-Cu liquidus"
            database = path.name
            limits = [
                f"liquidus of {basis}; Al-Cu database phases only",
                "database assessment, not a measurement; no model error bar is claimed",
            ]
            does_not_say = "mechanical strength, creep, oxidation or corrosion"
            engine = "pycalphad equilibrium (Al-Cu liquidus)"
        else:
            needed = ("element", "solid_phase", "low_k", "high_k")
            missing = [key for key in needed if payload.get(key) in (None, "")]
            if missing:
                return A.refusal(
                    "unit mismatch",
                    capability="alloy.phase",
                    reason=(
                        "missing "
                        + ", ".join(missing)
                        + " (pure-element melting) or x_cu / cu_wt_pct (Al-Cu liquidus)"
                    ),
                    gate=gate,
                )
            out = C.melting_point(
                str(tdb),
                str(payload["element"]),
                str(payload["solid_phase"]),
                float(payload["low_k"]),
                float(payload["high_k"]),
            )
            value = float(out["melting_k"])
            method = out["method"] + ", pure element"
            database = out["database"]
            limits = [
                f"pure {out['element']} melting point ({out['solid_phase']} -> LIQUID)",
                "database assessment, not a measurement; no model error bar is claimed",
            ]
            does_not_say = "alloy behaviour, creep, oxidation or corrosion"
            engine = "pycalphad equilibrium + bisection"
    except ValueError as exc:
        return A.refusal(
            "out of domain",
            capability="alloy.phase",
            reason=f"{type(exc).__name__}: {exc}",
            gate=gate,
        )
    return A.build(
        capability="alloy.phase",
        value=value,
        unit="K",
        method=method,
        verdict=_verdict(gate),
        provenance={"engine": engine, "dataset": database},
        reproduce=reproduce_command(request, payload),
        does_not_say=does_not_say,
        limits=limits,
        gate=gate,
    )


def identity(request, plan, payload):
    """One RDKit property: molecular weight (g/mol) or Crippen logP (ratio)."""
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors

    gate = plan.get("gate")
    smiles = smiles_list(payload)
    if not smiles:
        return A.refusal(
            "no data",
            capability="molecule.identity",
            reason="no SMILES for the RDKit property",
            gate=gate,
        )
    mol = Chem.MolFromSmiles(smiles[0])
    if mol is None:
        return A.refusal(
            "out of domain",
            capability="molecule.identity",
            reason=f"RDKit could not parse SMILES: {smiles[0]!r}",
            gate=gate,
        )
    prop = str((payload or {}).get("property") or "").strip().lower() if isinstance(payload, dict) else ""
    text = (request or "").lower()
    if not prop:
        prop = "logp" if ("logp" in text or "log p" in text) else "mw"
    from rdkit import rdBase

    if prop in ("logp", "log p"):
        value = float(Crippen.MolLogP(mol))
        return A.build(
            capability="molecule.identity",
            value=value,
            unit="1",
            method="RDKit Crippen.MolLogP(mol)",
            verdict=_verdict(gate),
            provenance={"engine": "RDKit Crippen", "dataset": f"rdkit {rdBase.rdkitVersion}"},
            reproduce=reproduce_command(request, payload),
            does_not_say="measured logP, logD at a given pH, or membrane permeability",
            limits=["octanol-water partition estimate for the neutral structure as drawn"],
            gate=gate,
        )
    value = float(Descriptors.MolWt(mol))
    return A.build(
        capability="molecule.identity",
        value=value,
        unit="g/mol",
        method="RDKit Descriptors.MolWt(mol), average atomic weights",
        verdict=_verdict(gate),
        provenance={"engine": "RDKit Descriptors", "dataset": f"rdkit {rdBase.rdkitVersion}"},
        reproduce=reproduce_command(request, payload),
        does_not_say="measured mass, isotopic mass, or purity",
        limits=["average molecular weight of the structure as drawn; implicit hydrogens included"],
        error={"kind": "definition", "lower": value, "upper": value},
        gate=gate,
    )


ADAPTERS = {
    "solubility.aqueous": esol,
    "mixture.gamma": unifac,
    "alloy.phase": calphad,
    "molecule.identity": identity,
}
