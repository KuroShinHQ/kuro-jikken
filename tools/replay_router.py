"""Replay one router ledger entry: `python tools/replay_router.py <entry-id>`.

Exit codes: 0 = plan+gate+answer reproduce, 1 = drift detected, 2 = entry or
ledger missing. The engines are not invoked here, so the number is only compared
when a compute function is supplied by the caller (later phase).
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "mcp"))

import ledger  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay one ledger entry.")
    parser.add_argument("entry_id", help="ledger id, e.g. 20261026T203312-1a2b3c4d")
    parser.add_argument("--dir", default=None, help="ledger directory (default: runs/router)")
    parser.add_argument("--list", action="store_true", help="only list the newest entries")
    args = parser.parse_args()

    if args.list:
        for path in ledger.files(args.dir)[:5]:
            for entry in ledger.read(path)[-10:]:
                print(f"{entry['id']}  {entry['capability']:<20} {entry['answer']['verdict']:<7} {entry['request'][:50]}")
        return 0

    try:
        result = ledger.replay(args.entry_id, root=args.dir)
    except KeyError as exc:
        print(f"[MISSING] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
