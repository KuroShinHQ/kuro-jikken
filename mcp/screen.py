"""S3 screen(): target (S1) + candidate pool (S2) + calibration ledger (R5).

The one rule that shapes this module: **a candidate list may only be ordered by
a property the calibration ledger calls CALIBRATED** (`data/calibration.json`,
``docs/CALIBRATION.md``). Today that is aqueous logS and gamma-infinity in
water. Every other property may filter or annotate a row, never order it - a
ranking without a measured error is an invented answer.

The pool is the identifier source. A target such as "etanol suda cozunur olsun"
is missing a SMILES because it describes a *goal*, not a molecule; the pool
supplies the structures, so ``missing: ["smiles"]`` does not block a screen.
Missing `basis`, `tolerance` or `tdb` do block it, because the pool cannot
invent them.

Every row carries the gate trace that produced or refused its number:

    {"casrn": ..., "value": ..., "unit": ..., "error": {...},
     "gates": [{"gate": "gate.structure", "verdict": "PASS", "reason": ...},
               {"gate": "gate.esol", "verdict": "PASS", "reason": ...}]}

    python mcp/screen.py "Etanol suda cozunur olsun" --limit 5
    python mcp/screen.py "Vazelin benzeri cilt koruyucu" --limit 5
"""
import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import gates  # noqa: E402
import target as targets  # noqa: E402

SCHEMA = "kj-screen/1"
POOL_DIR = ROOT / "data" / "pool"
LEDGER_PATH = ROOT / "data" / "calibration.json"
WATER_SMILES = "O"

# identifiers the pool can supply; anything else in target.missing is a blocker
POOL_IDENTIFIERS = {"smiles", "casrn", "components"}

STRATEGIES = {
    "solubility.aqueous": {
        "pool": "hsp",
        "gate": "gate.esol",
        "property": "logS",
        "unit": "log10(mol/L)",
        "direction": "desc",
        "capability": "solubility.aqueous",
        "why": "highest predicted aqueous solubility first",
    },
    "solvent.miscibility": {
        "pool": "hsp",
        "gate": "gate.unifac",
        "property": "gamma_inf_water",
        "unit": "1",
        "direction": "asc",
        "capability": "mixture.gamma",
        "why": "lowest gamma-infinity in water first (more compatible)",
    },
    "formulation.petrolatum_like": {
        "pool": "melting",
        "subset": {"group": "n-alkane"},
        "gate": "gate.esol",
        "property": "logS",
        "unit": "log10(mol/L)",
        "direction": "asc",
        "capability": "solubility.aqueous",
        "why": "hydrophobic first: lowest predicted aqueous solubility among hydrocarbons",
        "reference_gate": ("gate.hsp", "8009-03-8"),
        "blocked_by": (
            "R4 is open: petrolatum (8009-03-8) has no Hansen entry, and the HSP "
            "table is REFERENCE_ONLY in R5, so Ra cannot order this list"
        ),
    },
    "wax.range": {
        "pool": "melting",
        "gate": "gate.wax",
        "property": None,
        "unit": None,
        "direction": None,
        "capability": None,
        "filter": "melting_k",
        "why": "components that pass the wax gate; filtered, never ranked (Tm is data, not a calibrated model)",
    },
}

DOES_NOT_SAY = (
    "that a candidate is safe, effective, stable, cheap or pleasant to use. A "
    "list is a starting point for measurement, not a recommendation."
)


def load_pool(name: str, pool_dir=None) -> dict:
    path = pathlib.Path(pool_dir or POOL_DIR) / f"{name}.json"
    pool = json.loads(path.read_text(encoding="utf-8"))
    if pool.get("schema") != "kj-pool/1":
        raise ValueError(f"{path.name}: unexpected schema {pool.get('schema')!r}")
    return pool


def load_ledger(path=None) -> dict:
    ledger = json.loads(pathlib.Path(path or LEDGER_PATH).read_text(encoding="utf-8"))
    if ledger.get("schema") != "kj-calibration/1":
        raise ValueError("unexpected calibration schema")
    return ledger


def calibrated_capabilities(ledger=None) -> dict:
    ledger = ledger or load_ledger()
    return {
        entry["capability"]: entry
        for entry in ledger["entries"]
        if entry.get("verdict") == "CALIBRATED"
    }


def _refuse(base, status, reason):
    base.update({
        "status": status,
        "reason": reason,
        "candidates": [],
        "order": {"by": None, "direction": None, "reason": reason},
        "limits": [reason],
    })
    return base


def _constraints(target):
    out = {}
    for constraint in target.get("constraints") or []:
        out.setdefault(constraint["key"], []).append(constraint)
    return out


def _passes(value, constraint):
    op = constraint["op"]
    if value is None:
        return False
    if op == "=":
        tolerance = constraint.get("tolerance")
        if tolerance:
            return abs(value - constraint["value"]) <= 0.5 * tolerance
        return abs(value - constraint["value"]) <= 1e-9
    if op == "<=":
        return value <= constraint["value"]
    if op == ">=":
        return value >= constraint["value"]
    if op == "~":
        tolerance = constraint.get("tolerance")
        return tolerance is not None and abs(value - constraint["value"]) <= tolerance
    return False


def _logS_row(entry):
    from esol import esol_published

    smiles = entry["smiles"]
    structure = gates.check("gate.structure", smiles)
    if structure["verdict"] == "RED":
        return None, "structure RED", [{"gate": "gate.structure", **structure}]
    gate = gates.check("gate.esol", smiles)
    trace = [{"gate": "gate.structure", **structure}, {"gate": "gate.esol", **gate}]
    if gate["verdict"] == "RED":
        return None, f"gate.esol RED: {gate['reason']}", trace
    result = esol_published(smiles)
    if not result.get("ok"):
        return None, result.get("error", "ESOL failed"), trace
    bar = float(gate.get("error_bar_logS", 1.2))
    value = float(result["value"])
    return {
        "value": round(value, 4),
        "unit": "log10(mol/L)",
        "error": {"kind": "model", "lower": round(value - bar, 4), "upper": round(value + bar, 4)},
        "measured": False,
        "gates": trace,
    }, None, trace


def _gamma_row(entry, relative_bar):
    import unifac_gamma

    smiles = entry["smiles"]
    structure = gates.check("gate.structure", smiles)
    if structure["verdict"] == "RED":
        return None, "structure RED", [{"gate": "gate.structure", **structure}]
    payload = [smiles, WATER_SMILES]
    gate = gates.check("gate.unifac", payload)
    trace = [{"gate": "gate.structure", **structure}, {"gate": "gate.unifac", **gate}]
    if gate["verdict"] == "RED":
        return None, f"gate.unifac RED: {gate['reason']}", trace
    try:
        value = float(unifac_gamma.gamma_inf(payload, version=1)[0])
    except Exception as exc:  # noqa: BLE001 - a row that cannot compute is skipped, not faked
        return None, f"gamma_inf failed: {type(exc).__name__}", trace
    return {
        "value": round(value, 4),
        "unit": "1",
        "error": {
            "kind": "model",
            "lower": round(value * (1.0 - relative_bar), 4),
            "upper": round(value * (1.0 + relative_bar), 4),
        },
        "measured": False,
        "gates": trace,
    }, None, trace


def _wax_row(entry):
    gate = gates.check("gate.wax", [entry["casrn"]])
    trace = [{"gate": "gate.wax", **gate}]
    if gate["verdict"] == "RED":
        return None, f"gate.wax RED: {gate['reason']}", trace
    return {
        "value": entry["tm_k"],
        "unit": "K",
        "error": None,
        "measured": True,
        "gates": trace,
    }, None, trace


def _reference_trace(strategy):
    pair = strategy.get("reference_gate")
    if not pair:
        return None
    gate_id, payload = pair
    record = gates.check(gate_id, payload)
    return {"gate": gate_id, "payload": payload, **record}


def screen(text, payload=None, *, limit=10, max_scan=200, pool_dir=None,
           ledger_path=None) -> dict:
    """Scan the pool for one target; returns candidates with their gate traces."""
    target = targets.parse(text, payload or {})
    base = {
        "schema": SCHEMA,
        "text": text,
        "target": target,
        "application": target.get("application"),
        "status": "OK",
        "reason": None,
        "order": {"by": None, "direction": None, "reason": None},
        "constraints": target.get("constraints") or [],
        "reference": None,
        "pool": None,
        "scanned": 0,
        "eligible": 0,
        "skipped": {},
        "candidates": [],
        "limits": [],
        "does_not_say": DOES_NOT_SAY,
    }
    if target["status"] == "RED":
        return _refuse(base, "RED", target["reason"])
    if target["status"] == "CLARIFY" and target.get("application") is None:
        return _refuse(base, "CLARIFY", target["reason"])

    application = target.get("application")
    strategy = STRATEGIES.get(application)
    if strategy is None:
        return _refuse(base, "CLARIFY", f"no screen strategy for {application!r}")

    blockers = [field for field in target.get("missing") or []
                if field not in POOL_IDENTIFIERS]
    if blockers:
        return _refuse(
            base, "CLARIFY",
            f"the pool cannot supply {', '.join(blockers)}; screen does not invent inputs",
        )

    ledger = load_ledger(ledger_path)
    calibrated = calibrated_capabilities(ledger)
    pool = load_pool(strategy["pool"], pool_dir)
    base["pool"] = {
        "name": pool["pool"],
        "count": pool["count"],
        "licence": pool["licence"],
        "source": pool["source"],
    }
    base["reference"] = _reference_trace(strategy)
    base["constraints"] = target.get("constraints") or []
    constraints = _constraints(target)

    rankable = strategy["property"] is not None and strategy["capability"] in calibrated
    if strategy["property"] is not None and not rankable:
        base["order"] = {
            "by": None,
            "direction": None,
            "reason": f"{strategy['capability']} is not CALIBRATED in data/calibration.json",
        }
        base["limits"].append(base["order"]["reason"])
    elif rankable:
        entry = calibrated[strategy["capability"]]
        base["order"] = {
            "by": strategy["property"],
            "direction": strategy["direction"],
            "capability": strategy["capability"],
            "verdict": "CALIBRATED",
            "error_model": entry["declared"]["kind"],
            "source": "data/calibration.json",
        }
    else:
        base["order"] = {
            "by": None,
            "direction": None,
            "reason": "this target is filtered, not ranked: no calibrated property applies",
        }

    relative_bar = 0.0
    if strategy["capability"] == "mixture.gamma" and rankable:
        relative_bar = float(calibrated["mixture.gamma"]["declared"]["value"])

    subset = strategy.get("subset") or {}
    rows, skipped = [], {}
    for entry in pool["entries"]:
        if any(entry.get(key) != value for key, value in subset.items()):
            continue
        identifiers = {"smiles": entry.get("smiles"), "casrn": entry.get("casrn")}
        if strategy["gate"] in ("gate.esol", "gate.unifac") and not identifiers["smiles"]:
            skipped["no smiles"] = skipped.get("no smiles", 0) + 1
            continue
        if strategy["gate"] == "gate.wax" and not identifiers["casrn"]:
            skipped["no casrn"] = skipped.get("no casrn", 0) + 1
            continue
        base["scanned"] += 1
        if base["scanned"] > max_scan:
            break

        if strategy["gate"] == "gate.esol":
            computed, reason, trace = _logS_row(entry)
        elif strategy["gate"] == "gate.unifac":
            computed, reason, trace = _gamma_row(entry, relative_bar)
        else:
            computed, reason, trace = _wax_row(entry)
        if computed is None:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue

        if "melting_k" in constraints:
            if not all(_passes(entry.get("tm_k"), item) for item in constraints["melting_k"]):
                skipped["melting_k filter"] = skipped.get("melting_k filter", 0) + 1
                continue

        row = {
            "casrn": entry.get("casrn"),
            "name": entry.get("name"),
            "smiles": entry.get("smiles"),
            "group": entry.get("group"),
            "value": computed["value"],
            "unit": computed["unit"],
            "error": computed["error"],
            "measured": computed["measured"],
            "gates": computed["gates"],
        }
        if "tm_k" in entry:
            row["tm_k"] = entry["tm_k"]
        rows.append(row)

    base["eligible"] = len(rows)
    base["skipped"] = skipped
    if base["order"].get("by"):
        reverse = base["order"]["direction"] == "desc"
        rows.sort(key=lambda row: (row["value"], row["casrn"] or ""), reverse=reverse)
    else:
        rows.sort(key=lambda row: row["casrn"] or "")
    base["candidates"] = rows[:max(0, int(limit))]
    base["max_scan"] = int(max_scan)
    base["limits"] += [
        "each row carries the gate trace that allowed its number; a RED gate never reaches the list",
        f"scanned at most {max_scan} eligible entries in pool order: the list is the best "
        "of that slice, not of the whole pool",
        f"pool licence: {pool['licence']} ({strategy['pool']}.json); a pool entry is not a ranking right",
    ]
    if strategy.get("blocked_by"):
        base["limits"].append(strategy["blocked_by"])
    if strategy.get("filter"):
        base["limits"].append(
            f"filtered by {strategy['filter']} only; the list is in CAS order, not a ranking"
        )
        base["limits"].append(
            "components only: a named mixture is not formulated here, and no "
            "wax content, rheology or performance follows from a melting point"
        )
    return base


def validate(result: dict) -> None:
    """Schema check: a screen result must not look more certain than it is."""
    if result.get("schema") != SCHEMA:
        raise ValueError("wrong schema")
    if result.get("status") not in {"OK", "CLARIFY", "RED"}:
        raise ValueError("status must be OK, CLARIFY or RED")
    order = result.get("order") or {}
    if order.get("by") and order.get("verdict") != "CALIBRATED":
        raise ValueError("an order must name a CALIBRATED property")
    for row in result.get("candidates") or []:
        if not row.get("gates"):
            raise ValueError(f"candidate without a gate trace: {row.get('casrn')}")
        if row.get("value") is not None and not row.get("unit"):
            raise ValueError(f"candidate value without a unit: {row.get('casrn')}")
        if row.get("value") is not None and row.get("error"):
            if not (row["error"]["lower"] <= row["value"] <= row["error"]["upper"]):
                raise ValueError(f"candidate lies outside its own error bar: {row.get('casrn')}")
        if not row.get("measured") and row.get("value") is not None and not row.get("error"):
            raise ValueError(f"model value without an error bar: {row.get('casrn')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="screen a target against the candidate pool")
    parser.add_argument("text", nargs="+", help="target sentence")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--max-scan", type=int, default=200)
    args = parser.parse_args()
    result = screen(" ".join(args.text), limit=args.limit, max_scan=args.max_scan)
    validate(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
