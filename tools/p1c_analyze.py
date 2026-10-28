"""P1c - analyse the sucrose solubility measurements.

Reads ``data/measurements/p1c_sucrose.csv`` and prints the per-point table,
the H1/H2/H3 verdicts and a machine-readable summary. No numbers are invented:
a row without both ``last_dissolved_g`` and ``first_residue_g`` is skipped.

Reference values (g sucrose per 100 g water) come from the pre-registration:
``prereg/p1c_sucrose_solubility_plan_v1.md``.

Usage:
    python tools/p1c_analyze.py [csv path] [--json]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "measurements" / "p1c_sucrose.csv"

REFERENCE = {20.0: 203.9, 40.0: 238.1, 60.0: 287.3, 80.0: 362.1, 90.0: 415.7}
ACCURACY = 0.15
REPEATABILITY = 0.10
FALLBACK_POINTS = 4


def _num(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def load_points(path: Path) -> list[dict]:
    points = []
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            last = _num(row.get("last_dissolved_g"))
            first = _num(row.get("first_residue_g"))
            if last is None or first is None:
                continue
            temp = _num(row.get("temp_measured_c")) or _num(row.get("temp_target_c"))
            water = _num(row.get("water_g")) or 100.0
            if temp is None or first < last:
                continue
            # normalise to 100 g water
            scale = 100.0 / water
            last *= scale
            first *= scale
            points.append(
                {
                    "point_id": row.get("point_id") or "",
                    "rep": row.get("rep") or "",
                    "temp": temp,
                    "mid": (last + first) / 2.0,
                    "unc": (first - last) / 2.0,
                    "notes": row.get("notes") or "",
                }
            )
    return points


def analyse(points: list[dict]) -> dict:
    per_point = []
    for point in points:
        ref = REFERENCE.get(point["temp"])
        entry = dict(point)
        entry["reference"] = ref
        entry["rel_error"] = None if ref is None else (point["mid"] - ref) / ref
        entry["pass"] = (
            None if entry["rel_error"] is None else abs(entry["rel_error"]) <= ACCURACY
        )
        per_point.append(entry)

    by_temp: dict[float, list[float]] = {}
    for point in points:
        by_temp.setdefault(point["temp"], []).append(point["mid"])
    means = {temp: sum(values) / len(values) for temp, values in by_temp.items()}

    h2 = None
    ordered = [means[t] for t in sorted(means)]
    if len(ordered) >= 3:
        h2 = all(b > a for a, b in zip(ordered, ordered[1:]))

    h3 = None
    spreads = {}
    if all(len(v) == 2 for v in by_temp.values()) and by_temp:
        spreads = {
            temp: abs(v[0] - v[1]) / (sum(v) / 2.0) for temp, v in by_temp.items()
        }
        h3 = all(value <= REPEATABILITY for value in spreads.values())

    errors = [abs(p["rel_error"]) for p in per_point if p["rel_error"] is not None]
    complete = len(points) >= 10
    fallback = (
        len(points) == FALLBACK_POINTS
        and len(by_temp) == 2
        and min(by_temp) <= 25.0
        and max(by_temp) >= 90.0
    )
    h1 = (
        all(p["pass"] for p in per_point if p["pass"] is not None)
        if complete and per_point
        else None
    )

    if not points:
        verdict = "NO DATA"
    elif complete and h1 and h2 and h3:
        verdict = "PASS"
    elif fallback and all(p["pass"] for p in per_point if p["pass"] is not None) and h3:
        verdict = "PASS (fallback 4-point)"
    elif not complete and not fallback:
        verdict = "INCOMPLETE"
    else:
        verdict = "FAIL"

    return {
        "points": len(points),
        "complete": complete,
        "fallback": fallback,
        "per_point": per_point,
        "means": means,
        "spreads": spreads,
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "mean_abs_error": (sum(errors) / len(errors)) if errors else None,
        "max_abs_error": max(errors) if errors else None,
        "verdict": verdict,
    }


def print_report(result: dict) -> None:
    print("P1c sucrose solubility - analysis")
    print(f"points measured: {result['points']}")
    print("")
    print("| point | T (C) | mid (g/100g) | +/- | ref | rel.err | H1 |")
    print("|---|---:|---:|---:|---:|---:|---|")
    for point in result["per_point"]:
        ref = point["reference"]
        rel = point["rel_error"]
        print(
            "| {pid} | {temp:.0f} | {mid:.1f} | {unc:.1f} | {ref} | {rel} | {ok} |".format(
                pid=point["point_id"],
                temp=point["temp"],
                mid=point["mid"],
                unc=point["unc"],
                ref="-" if ref is None else f"{ref:.1f}",
                rel="-" if rel is None else f"{rel:+.1%}",
                ok="-" if point["pass"] is None else ("PASS" if point["pass"] else "FAIL"),
            )
        )
    print("")
    for name in ("h1", "h2", "h3"):
        value = result[name]
        print(f"{name.upper()}: {'not tested' if value is None else ('PASS' if value else 'FAIL')}")
    if result["mean_abs_error"] is not None:
        print(f"mean |error|: {result['mean_abs_error']:.1%}")
        print(f"max  |error|: {result['max_abs_error']:.1%}")
    print(f"VERDICT: {result['verdict']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P1c sucrose solubility analysis")
    parser.add_argument("csv", nargs="?", default=str(DEFAULT_CSV))
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = parser.parse_args(argv)

    path = Path(args.csv)
    if not path.is_file():
        print(f"ERROR: csv not found: {path}", file=sys.stderr)
        return 2

    result = analyse(load_points(path))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print_report(result)
    return 0 if result["verdict"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
