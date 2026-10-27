"""S2 candidate-pool builder: offline, deterministic, licence-stamped.

A pool entry is only useful if an engine can answer for it. So every pool is
built from the *same* source the engine reads, never typed by hand:

* ``hsp.json``          Hansen dD/dP/dH from ``chemicals`` 1.5.2 (the table
                        ``hsp_lookup`` uses; same priority order, same rounding),
                        enriched with name/formula/SMILES/MW from the same
                        package. Licence: MIT.
* ``melting.json``      Tm and Hfus for a curated list of n-alkanes, fatty acids
                        and fatty alcohols (the ``mixture.wax`` inputs). The
                        curated part is only the CAS list; every number comes
                        from ``chemicals``. Mixtures without Hfus are recorded
                        as skipped, not silently dropped. Licence: MIT.
* ``alloy_phases.json`` ELEMENT and PHASE *names* parsed from the MatCalc open
                        TDBs in ``data/alloy_tdb``. No Gibbs coefficients are
                        copied. Licence: ODbL-1.0 + DbCL-1.0.

    python tools/build_pool.py           # write data/pool/*.json + README.md
    python tools/build_pool.py --check   # exit 1 when a file is stale

The index carries the licence line, the count and the role of every pool. A
pool never grants a ranking right: that is ``data/calibration.json`` (R5).
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
POOL = ROOT / "data" / "pool"
SCHEMA = "kj-pool/1"
GENERATED = "2026-10-27"

HSP_LICENCE = "MIT"
HSP_SOURCE = (
    "chemicals 1.5.2 (MIT) Hansen tables; sources inside the package: "
    "HSPiPy, WDR Schrier 2020, Manuel-Ruben 2022, Alshehri-Hansen 2022"
)
MELTING_LICENCE = "MIT"
MELTING_SOURCE = "chemicals 1.5.2 (MIT) Tm/Hfus tables (DIPPR/TRC compilations)"
TDB_LICENCE = "ODbL-1.0 + DbCL-1.0"
TDB_SOURCE = (
    "MatCalc open TDBs in data/alloy_tdb; only ELEMENT and PHASE names are "
    "recorded, no Gibbs coefficients"
)

ROLE = {
    "hsp": "reference-only: annotate or filter a candidate, never order it "
           "(R5 verdict REFERENCE_ONLY)",
    "melting": "range input for mixture.wax only: feasibility, never a "
               "single melting point or a ranking (R5 verdict UNCALIBRATED)",
    "alloy_phases": "phase catalogue for alloy.phase: filter, never order "
                    "(R5 verdict MEASURED_NOT_DECLARED)",
}

# Curated CAS list: the only hand-typed part. Each group says why it is here.
MELTING_CAS = [
    # n-alkanes: the wax model's natural components (C16..C32)
    ("544-76-3", "n-alkane", "hexadecane"),
    ("593-45-3", "n-alkane", "octadecane"),
    ("112-95-8", "n-alkane", "eicosane"),
    ("629-97-0", "n-alkane", "docosane"),
    ("646-31-1", "n-alkane", "tetracosane"),
    ("630-02-4", "n-alkane", "octacosane"),
    ("630-03-5", "n-alkane", "nonacosane"),
    ("638-68-6", "n-alkane", "triacontane"),
    ("544-85-4", "n-alkane", "dotriacontane"),
    # fatty acids: polar waxes, the other half of a real candle/cream base
    ("143-07-7", "fatty acid", "lauric acid"),
    ("544-63-8", "fatty acid", "myristic acid"),
    ("57-10-3", "fatty acid", "palmitic acid"),
    ("57-11-4", "fatty acid", "stearic acid"),
    ("112-80-1", "fatty acid", "oleic acid"),
    ("112-85-6", "fatty acid", "behenic acid"),
    # fatty alcohols: consistency agents next to the acids
    ("112-53-8", "fatty alcohol", "1-dodecanol"),
    ("36653-82-4", "fatty alcohol", "1-hexadecanol"),
    ("112-92-5", "fatty alcohol", "1-octadecanol"),
    # mixtures: kept in the list so their omission is recorded, not hidden
    ("8002-74-2", "wax mixture", "paraffin wax"),
    ("8009-03-8", "wax mixture", "petrolatum"),
]

PHASE_LINE = re.compile(r"^\s*PHASE\s+([A-Za-z0-9_#\-]+)")
ELEMENT_LINE = re.compile(r"^\s*ELEMENT\s+([A-Z][A-Z0-9]*)")


def _normalised_bytes(path: pathlib.Path) -> bytes:
    """Content bytes with CRLF folded to LF.

    The TDB files are text; a checkout on a machine with different line-ending
    settings must not change the pinned size or hash (first seen on the Linux CI
    runner). The databases themselves are parsed by pycalphad, which does not
    care about the ending.
    """
    return path.read_bytes().replace(b"\r\n", b"\n")


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(_normalised_bytes(path)).hexdigest()


def _dump(path: pathlib.Path, obj) -> str:
    text = json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return text


def _metadata(casrn: str) -> dict:
    """Name/formula/SMILES/MW from the chemicals package; missing -> None."""
    try:
        from chemicals import search_chemical

        meta = search_chemical(casrn)
    except Exception:  # noqa: BLE001 - a missing name must not kill the build
        return {}
    name = getattr(meta, "common_name", None) or getattr(meta, "iupac_name", None)
    mw = getattr(meta, "MW", None)
    return {
        "name": name,
        "formula": getattr(meta, "formula", None),
        "smiles": getattr(meta, "smiles", None),
        "mw_g_mol": round(float(mw), 2) if isinstance(mw, (int, float)) else None,
    }


def build_hsp() -> dict:
    from chemicals import hansen_delta_d, hansen_delta_h, hansen_delta_p
    from chemicals import solubility as S

    S._load_solubility_data()
    casrns = sorted({str(c) for frame in S.solubility_sources.values()
                     for c in frame.index if c})
    entries, skipped = [], []
    for casrn in casrns:
        delta_d, delta_p, delta_h = (
            hansen_delta_d(casrn), hansen_delta_p(casrn), hansen_delta_h(casrn)
        )
        if None in (delta_d, delta_p, delta_h):
            skipped.append({"casrn": casrn, "reason": "incomplete dD/dP/dH"})
            continue
        values = [round(v / 1000.0, 2) for v in (delta_d, delta_p, delta_h)]
        if not (10.0 <= values[0] <= 30.0 and 0.0 <= values[1] <= 50.0
                and 0.0 <= values[2] <= 60.0):
            skipped.append({"casrn": casrn, "reason": f"implausible dD/dP/dH {values}"})
            continue
        methods = [S.hansen_delta_d_methods(casrn), S.hansen_delta_p_methods(casrn),
                   S.hansen_delta_h_methods(casrn)]
        shared = [m for m in methods[0] if all(m in other for other in methods[1:])]
        entry = {"casrn": casrn}
        entry.update(_metadata(casrn))
        entry.update({
            "delta_d": values[0],
            "delta_p": values[1],
            "delta_h": values[2],
            "unit": "MPa^0.5",
            "method": shared[0] if shared else "mixed",
        })
        entries.append(entry)

    return {
        "schema": SCHEMA,
        "pool": "hsp",
        "generated": GENERATED,
        "source": HSP_SOURCE,
        "licence": HSP_LICENCE,
        "role": ROLE["hsp"],
        "count": len(entries),
        "skipped": skipped,
        "entries": entries,
    }


def build_melting() -> dict:
    from chemicals import Hfus, Tm

    entries, skipped = [], []
    for casrn, group, name in MELTING_CAS:
        tm = Tm(CASRN=casrn)
        hfus = Hfus(CASRN=casrn)
        if tm is None or hfus is None:
            missing = "Tm" if tm is None else "Hfus"
            skipped.append({
                "casrn": casrn,
                "name": name,
                "group": group,
                "reason": f"{missing} missing: ideal SLE needs both",
            })
            continue
        if not 100.0 <= float(tm) <= 500.0 or not 1000.0 <= float(hfus) <= 120000.0:
            skipped.append({"casrn": casrn, "name": name, "group": group,
                            "reason": f"implausible Tm/Hfus {tm}/{hfus}"})
            continue
        meta = _metadata(casrn)
        entries.append({
            "casrn": casrn,
            "name": meta.get("name") or name,
            "curated_name": name,
            "group": group,
            "tm_k": round(float(tm), 2),
            "hfus_j_mol": round(float(hfus), 1),
            "formula": meta.get("formula"),
            "smiles": meta.get("smiles"),
            "mw_g_mol": meta.get("mw_g_mol"),
        })

    return {
        "schema": SCHEMA,
        "pool": "melting",
        "generated": GENERATED,
        "source": MELTING_SOURCE,
        "licence": MELTING_LICENCE,
        "role": ROLE["melting"],
        "count": len(entries),
        "curated_cas": len(MELTING_CAS),
        "skipped": skipped,
        "entries": entries,
    }


def build_alloy_phases() -> dict:
    entries = []
    for path in sorted((ROOT / "data" / "alloy_tdb").glob("*.tdb")):
        elements, phases = set(), set()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            element = ELEMENT_LINE.match(line)
            if element and element.group(1) != "VA":
                elements.add(element.group(1))
            phase = PHASE_LINE.match(line)
            if phase:
                phases.add(phase.group(1))
        entries.append({
            "database": path.stem,
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": len(_normalised_bytes(path)),
            "sha256": _sha256(path),
            "elements": sorted(elements),
            "element_count": len(elements),
            "phases": sorted(phases),
            "phase_count": len(phases),
            "licence": TDB_LICENCE,
        })
    return {
        "schema": SCHEMA,
        "pool": "alloy_phases",
        "generated": GENERATED,
        "source": TDB_SOURCE,
        "licence": TDB_LICENCE,
        "role": ROLE["alloy_phases"],
        "count": len(entries),
        "entries": entries,
    }


def build_all() -> dict:
    """Build every pool in memory; returns {relative path: text}."""
    files = {}
    for name, builder in (
        ("hsp", build_hsp),
        ("melting", build_melting),
        ("alloy_phases", build_alloy_phases),
    ):
        pool = builder()
        files[f"data/pool/{name}.json"] = json.dumps(
            pool, indent=1, sort_keys=True, ensure_ascii=False
        ) + "\n"

    pools = {}
    for name in ("hsp", "melting", "alloy_phases"):
        rel = f"data/pool/{name}.json"
        payload = json.loads(files[rel])
        pools[name] = {
            "file": rel,
            "count": payload["count"],
            "licence": payload["licence"],
            "role": payload["role"],
            "bytes": len(files[rel].encode("utf-8")),
            "sha256": hashlib.sha256(files[rel].encode("utf-8")).hexdigest(),
        }
    index = {
        "schema": SCHEMA,
        "generated": GENERATED,
        "builder": "tools/build_pool.py",
        "check": "python tools/build_pool.py --check",
        "pools": pools,
        "ranking": "a pool entry is not a ranking right: see data/calibration.json (R5)",
        "note": "generated file: edit the builder, not the JSON",
    }
    files["data/pool/index.json"] = json.dumps(
        index, indent=1, sort_keys=True, ensure_ascii=False
    ) + "\n"

    rows = [("pool", "count", "licence", "role")]
    for name in ("hsp", "melting", "alloy_phases"):
        item = pools[name]
        rows.append((f"[{name}.json]({name}.json)", str(item["count"]),
                     item["licence"], item["role"]))
    widths = [max(len(row[i]) for row in rows) for i in range(4)]
    lines = [
        "# Candidate pool (S2)",
        "",
        f"Generated {GENERATED} by `tools/build_pool.py`; do not edit by hand.",
        "`--check` fails when a file no longer matches its source.",
        "",
        "| " + " | ".join(head.ljust(widths[i]) for i, head in enumerate(rows[0])) + " |",
        "|" + "|".join("-" * (widths[i] + 2) for i in range(4)) + "|",
    ]
    for row in rows[1:]:
        lines.append("| " + " | ".join(row[i].ljust(widths[i]) for i in range(4)) + " |")
    lines += [
        "",
        "A pool entry is not a ranking right. `data/calibration.json` (R5) says",
        "which properties may be ordered; today that is only aqueous logS and",
        "gamma-infinity, so the HSP, wax and phase pools are filters/annotations.",
        "",
        "Sources:",
        "",
        f"- HSP: {HSP_SOURCE} (MIT).",
        f"- Melting: {MELTING_SOURCE} (MIT); curated CAS list only.",
        f"- Phases: {TDB_SOURCE} (ODbL-1.0 + DbCL-1.0).",
        "",
    ]
    files["data/pool/README.md"] = "\n".join(lines)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="build the S2 candidate pool")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if a generated file differs from a fresh build")
    args = parser.parse_args()

    files = build_all()
    stale = []
    for relative, text in files.items():
        path = ROOT / relative
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if args.check:
            if current != text:
                stale.append(relative)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {relative} ({len(text.encode('utf-8'))} B)")

    if args.check:
        if stale:
            print("STALE: " + ", ".join(stale))
            return 1
        print(f"OK: {len(files)} files match a fresh build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
