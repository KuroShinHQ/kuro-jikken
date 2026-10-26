"""One call from a free-text request to a gated, stored answer (P5a CLI).

    python tools/ask.py "etanol suda ne kadar cozunur" --payload '{"smiles":"CCO"}'

Exit codes: 0 = a number was produced (GREEN/YELLOW), 1 = refusal (RED),
2 = bad input. ``--no-write`` recomputes without touching the ledger, which is
what every answer's ``reproduce`` command uses.
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

import pipeline  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="plan -> gate -> engine -> build -> ledger")
    parser.add_argument("request", help="free-text request")
    parser.add_argument("--payload", default=None, help="JSON identifiers, e.g. '{\"smiles\":\"CCO\"}'")
    parser.add_argument("--no-write", action="store_true", help="compute only, no ledger record")
    parser.add_argument("--session", default=None, help="session label stored in the ledger")
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.payload) if args.payload else None
    except json.JSONDecodeError as exc:
        print(f"payload is not valid JSON: {exc}", file=sys.stderr)
        return 2

    out = pipeline.ask(
        args.request, payload, write=not args.no_write, session=args.session
    )
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out["answer"]["verdict"] != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
