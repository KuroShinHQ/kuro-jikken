"""Ask the S4 cosmetics pool one question at a time.

    python tools/cosmetics_lookup.py glycerin
    python tools/cosmetics_lookup.py --top 15
    python tools/cosmetics_lookup.py --unmatched 10
    python tools/cosmetics_lookup.py aqua --json

Answers: how many real labels carry this name, and what does CosIng say it is.
It does not answer -- and must not be read as answering -- "how much should I
use", "is it safe", or "make me a moisturiser". Those are not dataset rows.
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
POOL = ROOT / "data" / "cosmetics" / "cosmetics.json"


def load() -> dict:
    if not POOL.is_file():
        raise SystemExit(f"missing {POOL}; run tools/build_cosmetics.py")
    return json.loads(POOL.read_text(encoding="utf-8"))


def show(row: dict) -> str:
    cosing = row["cosing"]
    functions = ", ".join(cosing["functions"]) or "-"
    cas = ", ".join(cosing["cas"]) or "-"
    flags = []
    if cosing["restricted"]:
        flags.append("RESTRICTED")
    if cosing["annex"]:
        flags.append("annex " + "/".join(cosing["annex"]))
    return (f"{row['inci']}\n"
            f"  labels : {row['products']:,} products, {row['brands']:,} brands\n"
            f"  cosing : {cosing['inci'] or '-'} [{cosing['status'] or '?'}] "
            f"({cosing['item_type'] or '?'})\n"
            f"  function: {functions}\n"
            f"  cas    : {cas}\n"
            f"  flags  : {', '.join(flags) or 'none'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="look up one ingredient in the S4 pool")
    parser.add_argument("name", nargs="?", help="INCI name (case-insensitive)")
    parser.add_argument("--top", type=int, help="most frequent N ingredients")
    parser.add_argument("--unmatched", type=int, help="label names with no CosIng match")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()
    pool = load()
    entries = pool["entries"]

    if args.top:
        rows = entries[:args.top]
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
            return 0
        for row in rows:
            print(f"{row['products']:6,}  {row['brands']:5,}  {row['inci']:38} "
                  f"{', '.join(row['cosing']['functions'])[:52]}")
        return 0

    if args.unmatched:
        rows = pool["coverage"]["unmatched_examples"][:args.unmatched]
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
            return 0
        for row in rows:
            print(f"{row['products']:6,}  {row['inci']}  (no CosIng record)")
        return 0

    if not args.name:
        parser.error("give a name, --top N or --unmatched N")
    wanted = args.name.strip().upper()
    exact = [row for row in entries if row["inci"] == wanted]
    if not exact:
        exact = [row for row in entries if wanted in row["inci"]]
    if not exact:
        print(f"{wanted}: not in the pool "
              f"({pool['count']:,} names on at least "
              f"{pool['thresholds']['min_products']} labels)")
        return 1
    if args.json:
        print(json.dumps(exact, ensure_ascii=False, indent=1))
        return 0
    for row in exact[:10]:
        print(show(row))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
