"""P5a engine adapters: a gate-passed plan becomes exactly one answer dict.

Each adapter is a pure function ``(request, plan, payload) -> answer``. It may
only return what ``answer.build`` accepts or a fixed refusal carrying the
engine's own reason; it never writes the ledger and never invents a number.
Heavy libraries (pycalphad, RDKit, pandas) are imported inside the adapter so
that importing this module stays cheap.

Adapters exist for every capability that has a validated engine: solubility.aqueous
(ESOL), mixture.gamma (UNIFAC Dortmund), mixture.wax (ideal solid-liquid equilibrium
from ``tools/wax_melting.py``), alloy.phase (pycalphad) and molecule.identity (RDKit).
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
            f"model error bar {bar} log units (locked-set in-domain RMSE 1.2246, n=1917; "
            "the whole set is 2.14, so never quote this outside the in-domain group)",
        ],
        gate=gate,
    )


def unifac(request, plan, payload):
    """Activity coefficient from UNIFAC Dortmund: gamma(x) or gamma-infinity."""
    import unifac_gamma as U

    smiles = smiles_list(payload)
    gate = plan.get("gate")
    if "cosmo" in (request or "").lower():
        return A.refusal(
            "no engine",
            capability="mixture.gamma",
            reason=(
                "the request names cOSMO, which is not wired to the answer contract; "
                "answering with UNIFAC would be a different model"
            ),
            gate=gate,
        )
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
    error = None
    try:
        if payload.get("x_cu") is not None or payload.get("cu_wt_pct") is not None or payload.get("cu_pct") is not None:
            from pycalphad import Database

            from alloy_liquidus import liquidus

            if payload.get("x_cu") is not None:
                x_cu = float(payload["x_cu"])
                basis_text = f"mole fraction x(Cu) = {x_cu}"
            elif payload.get("cu_wt_pct") is not None:
                wt = float(payload["cu_wt_pct"])
                x_cu = _al_cu_mole_fraction(wt)
                basis_text = f"{wt} wt% Cu = mole fraction x(Cu) = {x_cu:.5f}"
            elif str(payload.get("basis") or "").strip().lower() in ("wt", "wt%", "weight"):
                wt = float(payload["cu_pct"])
                x_cu = _al_cu_mole_fraction(wt)
                basis_text = f"{wt} wt% Cu = mole fraction x(Cu) = {x_cu:.5f}"
            elif str(payload.get("basis") or "").strip().lower() in ("at", "at%", "atomic", "mol", "mole"):
                # atomic percent in a binary IS mole percent
                x_cu = float(payload["cu_pct"]) / 100.0
                basis_text = f"{payload['cu_pct']} at% Cu = mole fraction x(Cu) = {x_cu:.5f}"
            else:
                return A.refusal(
                    "unit mismatch",
                    capability="alloy.phase",
                    reason=(
                        f"cu_pct = {payload.get('cu_pct')} does not say wt% or at%; "
                        'add "basis": "wt" or "at"'
                    ),
                    gate=gate,
                )
            path = C.tdb_path(str(tdb))
            if x_cu <= 0.0:
                # the binary liquidus has no bracket at x_Cu = 0; pure Al is its own path
                elements = [str(e).upper() for e in _as_list(payload.get("elements"))]
                others = [element for element in elements if element not in ("AL", "CU")]
                if others:
                    return A.refusal(
                        "missing input",
                        capability="alloy.phase",
                        reason=(
                            f"0 % Cu would be pure {others[0]}, not aluminium; give "
                            "element + solid_phase for a pure-element melting point"
                        ),
                        gate=gate,
                    )
                pure = C.melting_point(str(tdb), "AL", "FCC_A1", low, high)
                value = float(pure["melting_k"])
                width = float(pure.get("bracket_width_k") or 0.0)
                error = {
                    "kind": "bisection bracket",
                    "lower": value - width / 2.0,
                    "upper": value + width / 2.0,
                }
                method = pure["method"] + ", pure Al (0 % Cu)"
                database = pure["database"]
                limits = [
                    "pure AL melting point (FCC_A1 -> LIQUID); the Al-Cu liquidus needs x_Cu > 0",
                    f"±{width / 2.0:.3f} K is the bisection bracket (numerical resolution), "
                    "not database or model uncertainty",
                ]
                does_not_say = "mechanical strength, creep, oxidation or corrosion"
                engine = "pycalphad equilibrium + bisection (pure element)"
            else:
                value, width = liquidus(
                    Database(str(path)), x_cu, low=low, high=high, with_bracket=True
                )
                error = {
                    "kind": "bisection bracket",
                    "lower": value - width / 2.0,
                    "upper": value + width / 2.0,
                }
                method = "pycalphad equilibrium + bisection (9 steps), Al-Cu liquidus"
                database = path.name
                limits = [
                    f"liquidus of {basis_text}; Al-Cu database phases only",
                    f"±{width / 2.0:.3f} K is the bisection bracket (numerical resolution), "
                    "not database or model uncertainty",
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
            width = float(out.get("bracket_width_k") or 0.0)
            error = {
                "kind": "bisection bracket",
                "lower": value - width / 2.0,
                "upper": value + width / 2.0,
            }
            method = out["method"] + ", pure element"
            database = out["database"]
            limits = [
                f"pure {out['element']} melting point ({out['solid_phase']} -> LIQUID)",
                f"±{width / 2.0:.3f} K is the bisection bracket (numerical resolution), "
                "not database or model uncertainty",
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
        error=error,
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


WAX_MODEL = "ideal solid-liquid equilibrium, gamma = 1"


def _wax_components(payload):
    """(CAS -> mole fraction, None) or (None, why it is missing)."""
    if not isinstance(payload, dict):
        return None, "the wax engine needs a payload with CAS numbers"
    raw = payload.get("casrn") or payload.get("cas") or payload.get("components")
    if isinstance(raw, dict) and (raw.get("casrn") or raw.get("components")):
        raw = raw.get("casrn") or raw.get("components")
    if isinstance(raw, dict):
        return {str(k).strip(): float(v) for k, v in raw.items() if str(k).strip()}, None
    cas = _as_list(raw)
    if not cas:
        return None, "no CAS number for the wax engine"
    xs = payload.get("x") if payload.get("x") is not None else payload.get("xs")
    if xs is None:
        if len(cas) == 1:
            return {cas[0]: 1.0}, None
        return None, (
            "a blend needs mole fractions in the same order as the CAS list "
            '(e.g. "x": [0.5, 0.5]); assuming equimolar would invent the composition'
        )
    xs = [float(v) for v in _as_list(xs)]
    if len(xs) != len(cas):
        return None, f"{len(cas)} CAS numbers but {len(xs)} mole fractions"
    if any(v <= 0 for v in xs):
        return None, "every mole fraction must be greater than zero"
    return dict(zip(cas, xs)), None


def wax(request, plan, payload):
    """Melting range of an n-alkane blend (ideal SLE): YELLOW, range only."""
    import wax_melting as W

    gate = plan.get("gate")
    if gate is None:
        return A.refusal(
            "no data",
            capability="mixture.wax",
            reason="no gate input for the wax engine",
            gate=None,
        )
    components, problem = _wax_components(payload)
    if problem:
        return A.refusal(
            "missing input",
            capability="mixture.wax",
            reason=problem,
            gate=gate,
        )
    try:
        out = W.wax_range(components)
    except ValueError as exc:
        return A.refusal(
            "missing parameters",
            capability="mixture.wax",
            reason=f"{type(exc).__name__}: {exc}",
            gate=gate,
        )
    wat = float(out["wax_appearance_k"])
    last = float(out["last_solid_k"])
    parts = ", ".join(
        f"{row['casrn']} x={row['x']}" for row in out["components"]
    )
    return A.build(
        capability="mixture.wax",
        value=wat,
        unit="K",
        method=f"ideal SLE: ln(x_i) = -dH_fus,i/R (1/T - 1/Tm,i) for {parts}",
        # the model sets every activity coefficient to 1: a range is not a GREEN number
        verdict="YELLOW",
        provenance={
            "engine": WAX_MODEL,
            "dataset": "chemicals (Tm, Hfus) via tools/wax_melting.py",
        },
        reproduce=reproduce_command(request, payload),
        does_not_say=(
            "wax content, crystal structure, rheology, pour point, hardness or any "
            "performance claim; activity coefficients are not modelled"
        ),
        error={"kind": "range", "lower": last, "upper": wat},
        limits=[
            f"melting range {last:.1f} to {wat:.1f} K for the stated mole fractions",
            "ideal solution (gamma = 1): real wax blends need activity coefficients",
            "n-alkanes only; a mixture CAS such as 8002-74-2 has no Hfus and is refused",
        ],
        gate=gate,
    )


def vle(request, plan, payload):
    """Azeotropic temperature of a binary at fixed pressure (model, not measurement)."""
    import vle as V

    gate = plan.get("gate")
    components = _as_list(payload.get("components") if isinstance(payload, dict) else None)
    if len(components) != 2:
        return A.refusal(
            "missing input",
            capability="vle.azeotrope",
            reason="give exactly two component names, e.g. components=['ethanol','water']",
            gate=gate,
        )
    pressure = _float(payload, "pressure_pa", V.DEFAULT_PRESSURE_PA)
    try:
        out = V.azeotrope(components, pressure)
    except V.VleError as exc:
        return A.refusal(
            "missing parameters",
            capability="vle.azeotrope",
            reason=str(exc),
            gate=gate,
        )
    if not out["azeotrope"]:
        return A.refusal(
            "no azeotrope",
            capability="vle.azeotrope",
            reason=f"{components[0]}/{components[1]} at {pressure:.0f} Pa",
            gate=gate,
        )
    first, second = out["components"]
    value = float(out["temperature_k"])
    bar = V.DECLARED_BAR_K
    return A.build(
        capability="vle.azeotrope",
        value=value,
        unit="K",
        method="modified Raoult's law: Dortmund UNIFAC gamma(x,T) + thermo Psat",
        verdict=_verdict(gate),
        provenance={
            "engine": "Dortmund UNIFAC + thermo Psat (modified Raoult)",
            "dataset": "DOUFIP2016 via thermo 0.6.1; validation docs/VLE.md",
        },
        reproduce=reproduce_command(request, payload),
        does_not_say=(
            "whether a real mixture separates this way at another pressure; "
            "ternary azeotropes; distillation design or energy use"
        ),
        error={"kind": "model", "lower": value - bar, "upper": value + bar},
        limits=[
            f"binary only at {pressure:.0f} Pa; modified Raoult's law with UNIFAC gamma(x,T)",
            f"azeotrope at x({first}) = {out['x1']:.3f} (y = {out['y1']:.3f}); "
            f"pure boiling points {out['pure_boiling_k'][0]:.2f} / "
            f"{out['pure_boiling_k'][1]:.2f} K",
            "validated on ethanol/water (+0.08 K) and propan-2-ol/water (0.00 K); "
            "other pairs are model predictions (docs/VLE.md)",
        ],
        gate=gate,
    )


ADAPTERS = {
    "solubility.aqueous": esol,
    "mixture.gamma": unifac,
    "mixture.wax": wax,
    "alloy.phase": calphad,
    "molecule.identity": identity,
    "vle.azeotrope": vle,
}
