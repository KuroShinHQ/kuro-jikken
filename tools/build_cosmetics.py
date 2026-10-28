"""S4 builder: join real label frequencies with CosIng identity, offline.

The pool answers one question and refuses the next:

* it can say: "on 79,010 real product records, GLYCERIN appears on 10,627
  labels from 3,042 brands; CosIng lists it as HUMECTANT/SOLVENT with CAS
  56-81-5";
* it cannot say: "use 5 % glycerin in a moisturiser". A formulation is not a
  dataset row. That request stays a permanent RED (ROADMAP S4).

    python tools/build_cosmetics.py             # write data/cosmetics/*
    python tools/build_cosmetics.py --check     # exit 1 when a file is stale

Every number comes from the two raw sources named in ``data/manifest.json``;
the build refuses to run when a source is missing instead of emitting a
smaller, quieter pool.
"""
import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cosmetics_sources as S  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "cosmetics"
SCHEMA = "kj-cosmetics/1"
MIN_PRODUCTS = 5

ROLE = ("reference-only: INCI identity, CosIng function and label frequency; "
        "never a formulation, never a safety claim, never a ranking")
NOT_FOR = [
    "making a formulation (a concentration needs a lab, not a label count)",
    "safety, efficacy or medical claims",
    "market share: OBF is crowd-sourced, not a sales panel",
    "ordering ingredients by performance",
]


def _split(values) -> list:
    out = []
    for value in values or []:
        for part in str(value).replace("/", ";").split(";"):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


def _pick(records: list) -> dict | None:
    """One record per name: ingredient before substance, active before not."""
    if not records:
        return None
    def key(record):
        types = record.get("itemType") or []
        return (
            0 if "ingredient" in types else 1,
            0 if (record.get("status") or [""])[0].lower() == "active" else 1,
            -len(record.get("functionName") or []),
            record.get("substanceId") or record.get("reference") or "",
        )
    return sorted(records, key=key)[0]


def _cosing_row(record: dict | None) -> dict | None:
    if not record:
        return None
    restrictions = _split(record.get("cosmeticRestriction"))
    annex = _split(record.get("annexNo"))
    limits = _split(record.get("maximumConcentration"))
    return {
        "inci": (record.get("inciName") or [None])[0],
        "cas": _split(record.get("casNo")),
        "ec": _split(record.get("ecNo")),
        "functions": _split(record.get("functionName")),
        "status": (record.get("status") or [None])[0],
        "item_type": (record.get("itemType") or [None])[0],
        "restricted": bool(restrictions or annex or limits),
        "restriction": restrictions,
        "annex": annex,
        "max_concentration": limits,
    }


def build(min_products: int = MIN_PRODUCTS) -> dict:
    obf = S.RAW_DIR / S.OBF_NAME
    if not obf.is_file():
        raise SystemExit(f"missing {obf}; run tools/fetch_cosmetics.py --obf")
    cosing = S.load_cosing()
    counts, brands, stats = S.count_tokens(S.iter_products(obf))
    index = cosing["index"]

    entries, unmatched = [], []
    for token, count in counts.items():
        if count < min_products:
            continue
        record = _pick(index.get(S.match_key(token), []))
        if record is None:
            unmatched.append((count, token))
            continue
        row = {"inci": token, "products": count, "brands": len(brands.get(token, ()))}
        row["cosing"] = _cosing_row(record)
        entries.append(row)

    entries.sort(key=lambda row: (-row["products"], row["inci"]))
    unmatched.sort(reverse=True)
    document = cosing["document"]
    generated = (document.get("fetched") or "")[:10] or "unknown"

    pool = {
        "schema": SCHEMA,
        "pool": "cosmetics",
        "generated": generated,
        "role": ROLE,
        "not_for": NOT_FOR,
        "count": len(entries),
        "thresholds": {"min_products": min_products},
        "sources": {
            "obf": {
                "file": obf.name,
                "bytes": obf.stat().st_size,
                "sha256": S.sha256(obf),
                "licence": S.OBF_LICENCE,
                "attribution": "Open Beauty Facts contributors, ODbL-1.0 / DbCL-1.0",
            },
            "cosing": {
                "file": cosing["path"].name,
                "bytes": cosing["path"].stat().st_size,
                "sha256": S.sha256(cosing["path"]),
                "licence": S.COSING_LICENCE,
                "attribution": S.COSING_ATTRIBUTION,
                "fetched": document.get("fetched"),
                "names_queried": document.get("names_queried"),
                "names_matched": document.get("names_matched"),
                "records": document.get("count"),
            },
        },
        "coverage": {
            "products_total": stats["products"],
            "products_with_inci": stats["with_inci"],
            "distinct_tokens": stats["tokens_total"],
            "tokens_in_pool": len(entries) + len(unmatched),
            "matched_cosing": len(entries),
            "match_rate": round(len(entries) / max(1, len(entries) + len(unmatched)), 4),
            "unmatched_examples": [{"inci": token, "products": count}
                                   for count, token in unmatched[:10]],
        },
        "entries": entries,
    }
    return pool


def _dump(obj) -> str:
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def build_files(pool: dict) -> dict:
    files = {"data/cosmetics/cosmetics.json": _dump(pool)}
    payload = files["data/cosmetics/cosmetics.json"].encode("utf-8")
    index = {
        "schema": SCHEMA,
        "generated": pool["generated"],
        "builder": "tools/build_cosmetics.py",
        "check": "python tools/build_cosmetics.py --check",
        "pools": {
            "cosmetics": {
                "file": "data/cosmetics/cosmetics.json",
                "count": pool["count"],
                "licence": f"{S.OBF_LICENCE} (labels) + {S.COSING_LICENCE} (CosIng)",
                "role": pool["role"],
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        },
        "note": "generated file: edit the builder, not the JSON",
    }
    files["data/cosmetics/index.json"] = _dump(index)

    coverage = pool["coverage"]
    lines = [
        "# Cosmetics pool (S4)",
        "",
        f"Generated {pool['generated']} by `tools/build_cosmetics.py`; do not edit by hand.",
        "`--check` fails when a file no longer matches its sources.",
        "",
        "| pool | count | licence | role |",
        "|---|---|---|---|",
        f"| [cosmetics.json](cosmetics.json) | {pool['count']:,} | "
        f"{S.OBF_LICENCE} + {S.COSING_LICENCE} | {pool['role']} |",
        "",
        "## What the numbers mean",
        "",
        f"- {coverage['products_total']:,} product records in the Open Beauty Facts dump; "
        f"{coverage['products_with_inci']:,} carry a readable INCI list.",
        f"- {coverage['distinct_tokens']:,} distinct label tokens; "
        f"{coverage['tokens_in_pool']:,} occur on at least "
        f"{pool['thresholds']['min_products']} products.",
        f"- {coverage['matched_cosing']:,} of those match a CosIng record "
        f"({coverage['match_rate'] * 100:.1f} %). Unmatched tokens are label noise "
        "or names outside CosIng, and are counted, not dropped.",
        "",
        "## What it is not",
        "",
        *[f"- {item}" for item in pool["not_for"]],
        "",
        "Sources:",
        "",
        f"- Open Beauty Facts dump: {pool['sources']['obf']['sha256'][:16]}... "
        f"({S.OBF_LICENCE}).",
        f"- CosIng: {pool['sources']['cosing']['sha256'][:16]}... "
        f"({S.COSING_LICENCE}), {pool['sources']['cosing']['records']:,} records.",
        "",
    ]
    files["data/cosmetics/README.md"] = "\n".join(lines)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="build the S4 cosmetics pool")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if a generated file differs from a fresh build")
    parser.add_argument("--min-products", type=int, default=MIN_PRODUCTS)
    args = parser.parse_args()

    pool = build(args.min_products)
    files = build_files(pool)
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
        print(f"wrote {relative} ({len(text.encode('utf-8')):,} B)")

    if args.check:
        if stale:
            print("STALE: " + ", ".join(stale))
            return 1
        print(f"OK: {len(files)} files match a fresh build")
    else:
        coverage = pool["coverage"]
        print(f"pool: {pool['count']:,} entries, match rate "
              f"{coverage['match_rate'] * 100:.1f} % "
              f"({coverage['matched_cosing']:,}/{coverage['tokens_in_pool']:,})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
