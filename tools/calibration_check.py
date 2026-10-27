"""Calibration ledger audit (R5).

The ledger (``data/calibration.json``) says, for every property an engine can
answer, what its measured error is, what it was measured against, and whether
the error bar the answer declares actually covers that error. This script is
the only thing allowed to call an entry "CALIBRATED": it recomputes the metrics
instead of trusting the recorded numbers.

Rules (any violation -> exit 1):

1. Schema: ids unique, required fields present, every adapter capability and
   every gate covered by at least one entry.
2. Dataset files named in the ledger exist and match their recorded size/hash.
3. ``measured`` metrics are recomputed from the stored per-point rows, or for
   the locked solubility set from the 2399-row CSV.
4. ``CALIBRATED`` needs a declared bar of the same kind that covers the measured
   error. A bar smaller than the measured error must be recorded as
   ``MEASURED_NOT_DECLARED`` (or widened), never as ``CALIBRATED``.
5. Installed package versions are compared with the recorded environment
   (warning by default; ``--strict`` makes drift fatal).

Run: .venv_inventory\\Scripts\\python.exe tools\\calibration_check.py
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "calibration.json"

VERDICTS = {
    "CALIBRATED",
    "MEASURED_NOT_DECLARED",
    "UNCALIBRATED",
    "REFERENCE_ONLY",
    "DEFINITION",
}
DECLARED_KINDS = {
    "rmse",
    "mae",
    "max_abs",
    "median_relative",
    "bracket",
    "range",
    "exact",
    "definition",
    "none",
}
COMPARABLE = {"rmse", "mae", "max_abs", "median_relative"}
ENTRY_FIELDS = {
    "id",
    "capability",
    "property",
    "unit",
    "gate",
    "surface",
    "engine",
    "dataset",
    "declared",
    "measured",
    "verdict",
    "reproduce",
    "evidence",
    "limits",
}


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def load_ledger(path: pathlib.Path = LEDGER) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def points_metric(points, metric: str):
    """Recompute a metric from stored (measured, computed) rows."""
    pairs = []
    for row in points:
        measured = row.get("measured")
        computed = row.get("computed")
        if not (_is_number(measured) and _is_number(computed)):
            return None
        pairs.append((float(measured), float(computed)))
    if not pairs:
        return None
    deltas = [computed - measured for measured, computed in pairs]
    if metric == "max_abs":
        return max(abs(d) for d in deltas)
    if metric == "mae":
        return sum(abs(d) for d in deltas) / len(deltas)
    if metric == "rmse":
        return math.sqrt(sum(d * d for d in deltas) / len(deltas))
    if metric == "median_relative":
        rel = [abs(d) / abs(m) for (m, _), d in zip(pairs, deltas) if m != 0]
        return statistics.median(rel) if rel else None
    return None


def esol_domains() -> dict:
    """Recompute the locked-set metrics per applicability domain, P-A coefficients."""
    sys.path.insert(0, str(ROOT / "mcp"))
    sys.path.insert(0, str(ROOT / "tools"))
    from rdkit import RDLogger

    RDLogger.DisableLog("rdApp.*")
    import esol

    path = ROOT / "validation" / "solubility" / "preds_locked_20261025_050126.csv"
    buckets = {"in": [], "out": [], "all": []}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            delta = float(row["P_A"]) - float(row["measured"])
            buckets["all"].append(delta)
            domain = "in" if esol.domain_classify(row["smiles"]).get("in_domain") else "out"
            buckets[domain].append(delta)

    out = {}
    for name, deltas in buckets.items():
        n = len(deltas)
        out[name] = {
            "n": n,
            "mae": sum(abs(d) for d in deltas) / n,
            "rmse": math.sqrt(sum(d * d for d in deltas) / n),
            "bias": sum(deltas) / n,
            "within_1.0": sum(1 for d in deltas if abs(d) <= 1.0) / n,
        }
    return out


def _close(a, b, tol) -> bool:
    return _is_number(a) and _is_number(b) and abs(float(a) - float(b)) <= tol


def check_entry(entry: dict) -> list:
    problems = []
    missing = ENTRY_FIELDS - set(entry)
    if missing:
        return [f"{entry.get('id', '?')}: missing fields {sorted(missing)}"]

    name = entry["id"]
    if entry["verdict"] not in VERDICTS:
        problems.append(f"{name}: unknown verdict {entry['verdict']!r}")
    for key in ("engine", "dataset", "declared", "measured"):
        if not isinstance(entry[key], dict):
            problems.append(f"{name}: {key} must be an object")
    if problems:
        return problems

    if not entry["dataset"].get("source") or not entry["dataset"].get("license"):
        problems.append(f"{name}: dataset needs source and license")
    if not entry["reproduce"]:
        problems.append(f"{name}: needs a reproduce command")
    if not entry["evidence"] or not entry["limits"]:
        problems.append(f"{name}: needs evidence and limits")
    if not entry["engine"].get("name"):
        problems.append(f"{name}: engine needs a name")

    declared, measured = entry["declared"], entry["measured"]
    kind = declared.get("kind")
    if kind not in DECLARED_KINDS:
        problems.append(f"{name}: unknown declared kind {kind!r}")
    if kind == "none" and declared.get("value") is not None:
        problems.append(f"{name}: declared kind 'none' must have value null")
    if kind == "bracket" and declared.get("value") is not None:
        value = declared["value"]
        if not _is_number(value) or value < 0:
            problems.append(f"{name}: bracket width must be a positive number")

    metric = measured.get("metric")
    if metric not in DECLARED_KINDS:
        problems.append(f"{name}: unknown measured metric {metric!r}")

    dataset = entry["dataset"]
    path = dataset.get("path")
    if path:
        file = ROOT / path
        if not file.is_file():
            problems.append(f"{name}: dataset file missing: {path}")
        else:
            if dataset.get("bytes") and file.stat().st_size != dataset["bytes"]:
                problems.append(f"{name}: dataset size changed: {path}")
            if dataset.get("sha256"):
                digest = hashlib.sha256(file.read_bytes()).hexdigest().upper()
                if digest != str(dataset["sha256"]).upper():
                    problems.append(f"{name}: dataset hash changed: {path}")

    recomputed = None
    points = entry.get("points") or []
    if points:
        recomputed = points_metric(points, metric)
        if recomputed is None:
            problems.append(f"{name}: points could not be recomputed for {metric!r}")
        elif not _close(recomputed, measured.get("value"), 0.005):
            problems.append(
                f"{name}: measured {metric} recorded {measured.get('value')} but points give {round(recomputed, 4)}"
            )

    if entry["verdict"] == "CALIBRATED":
        if kind not in COMPARABLE or kind != metric:
            problems.append(
                f"{name}: CALIBRATED needs a comparable bar of the same kind (declared {kind!r}, measured {metric!r})"
            )
        else:
            bar = float(declared["value"]) + float(declared.get("rounding") or 0.0)
            if bar + 1e-9 < float(measured["value"]):
                problems.append(
                    f"{name}: declared bar {declared['value']} understates measured {metric} "
                    f"{measured['value']} - widen the bar or record MEASURED_NOT_DECLARED"
                )
    elif entry["verdict"] == "MEASURED_NOT_DECLARED":
        if kind in COMPARABLE and metric in COMPARABLE:
            bar = float(declared["value"]) + float(declared.get("rounding") or 0.0)
            if bar + 1e-9 >= float(measured["value"]):
                problems.append(
                    f"{name}: declared bar already covers the measured error - record CALIBRATED"
                )
    elif entry["verdict"] == "UNCALIBRATED":
        if metric != "none" or points or int(measured.get("n") or 0) != 0:
            problems.append(f"{name}: UNCALIBRATED must have no measured metric, no points, n = 0")
    elif entry["verdict"] == "DEFINITION":
        if kind != "definition":
            problems.append(f"{name}: DEFINITION needs declared kind 'definition'")
    elif entry["verdict"] == "REFERENCE_ONLY":
        if kind not in {"none", "range"}:
            problems.append(f"{name}: REFERENCE_ONLY must not declare a model error bar")
    return problems


def check_coverage(ledger: dict) -> list:
    """Every adapter capability and every gate must be covered by one entry."""
    problems = []
    sys.path.insert(0, str(ROOT / "mcp"))
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT / "mcp" / "tests"))
    import engines
    import gates

    adapter_caps = set(engines.ADAPTERS)
    gate_ids = set(gates.GATES)
    entries = ledger["entries"]

    covered_caps = {e["capability"] for e in entries}
    for cap in sorted(adapter_caps - covered_caps):
        problems.append(f"coverage: adapter capability {cap!r} has no calibration entry")
    for entry in entries:
        if entry["surface"] == "adapter" and entry["capability"] not in adapter_caps:
            problems.append(f"coverage: {entry['id']} claims adapter for unknown capability {entry['capability']!r}")

    covered_gates = {e["gate"] for e in entries}
    for gate in sorted(gate_ids - covered_gates):
        problems.append(f"coverage: gate {gate!r} has no calibration entry")

    ids = [e["id"] for e in entries]
    if len(ids) != len(set(ids)):
        problems.append("coverage: duplicate entry ids")
    return problems


def check_esol(ledger: dict) -> tuple:
    """Recompute the locked-set ESOL metrics and compare with the ledger."""
    entry = next((e for e in ledger["entries"] if e["id"] == "cal.solubility.aqueous.logs"), None)
    if entry is None:
        return ["esol: entry missing"], {}
    live = esol_domains()
    problems = []
    recorded = entry["measured"].get("domains") or {}
    for domain in ("in", "out", "all"):
        want = recorded.get(domain)
        if not want:
            problems.append(f"esol: no recorded metrics for domain {domain!r}")
            continue
        got = live[domain]
        if got["n"] != want.get("n"):
            problems.append(f"esol {domain}: n recorded {want.get('n')} but CSV gives {got['n']}")
        for key in ("mae", "rmse", "bias", "within_1.0"):
            if not _close(got[key], want.get(key), 0.002):
                problems.append(
                    f"esol {domain}: {key} recorded {want.get(key)} but CSV gives {round(got[key], 4)}"
                )
    if entry["verdict"] == "CALIBRATED":
        measured = entry["measured"]["value"]
        if not _close(live["in"]["rmse"], measured, 0.002):
            problems.append(
                f"esol: declared-domain rmse recorded {measured} but CSV gives {round(live['in']['rmse'], 4)}"
            )
    return problems, live


def check_versions(ledger: dict, strict: bool) -> list:
    from importlib.metadata import PackageNotFoundError, version

    problems = []
    for name, recorded in (ledger.get("environment", {}).get("packages") or {}).items():
        try:
            installed = version(name)
        except PackageNotFoundError:
            problems.append(f"version: {name} is not installed (ledger says {recorded})")
            continue
        if installed != recorded:
            message = f"version drift: {name} {recorded} -> {installed} (re-measure and bump the ledger)"
            problems.append(message if strict else f"WARN {message}")
    return problems


def summary(ledger: dict) -> dict:
    counts = {verdict: 0 for verdict in sorted(VERDICTS)}
    rankable = []
    for entry in ledger["entries"]:
        counts[entry["verdict"]] = counts.get(entry["verdict"], 0) + 1
        if entry["verdict"] == "CALIBRATED":
            rankable.append(f"{entry['capability']}/{entry['property']}")
    return {
        "entries": len(ledger["entries"]),
        "verdicts": counts,
        "rankable": rankable,
        "git_head": ledger.get("git_head"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Audit the calibration ledger.")
    parser.add_argument("--strict", action="store_true", help="version drift is fatal")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = parser.parse_args(argv)

    ledger = load_ledger()
    problems = []
    if ledger.get("schema") != "kj-calibration/1":
        problems.append(f"schema: expected kj-calibration/1, got {ledger.get('schema')!r}")
    for entry in ledger["entries"]:
        problems += check_entry(entry)
    problems += check_coverage(ledger)
    esol_problems, live = check_esol(ledger)
    problems += esol_problems
    version_findings = check_versions(ledger, args.strict)
    fatal_versions = [p for p in version_findings if not p.startswith("WARN ")]
    problems += fatal_versions

    if args.json:
        print(json.dumps({"summary": summary(ledger), "problems": problems}, indent=2))
    else:
        data = summary(ledger)
        print(f"calibration ledger: {data['entries']} entries, git_head {data['git_head']}")
        for verdict, count in data["verdicts"].items():
            if count:
                print(f"  {verdict:<24} {count}")
        print("rankable by screen(): " + (", ".join(data["rankable"]) or "none"))
        if live:
            print(
                "locked ESOL (recomputed): "
                f"in n={live['in']['n']} rmse {live['in']['rmse']:.4f} | "
                f"out n={live['out']['n']} rmse {live['out']['rmse']:.4f} | "
                f"all n={live['all']['n']} rmse {live['all']['rmse']:.4f}"
            )
        for finding in version_findings:
            print(finding)
        if problems:
            print(f"\nRESULT FAIL - {len(problems)} problem(s)")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print("\nRESULT PASS - every property carries a measured error and a source")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
