"""S5: "vazelin benzeri" vertical slice (target -> screen -> refusal boundary).

Renders docs/S5_PETROLATUM_SLICE.md. `--check` fails when the document drifts.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

import gates  # noqa: E402
import screen  # noqa: E402
import target as targets  # noqa: E402

TARGET = "Vazelin benzeri cilt koruyucu"
LIMIT = 5
MAX_SCAN = 200
OUT = ROOT / "docs" / "S5_PETROLATUM_SLICE.md"


def render() -> str:
    result = screen.screen(TARGET, limit=LIMIT, max_scan=MAX_SCAN)
    screen.validate(result)
    order = result["order"]
    lines = [
        '# S5 - "vazelin benzeri" first vertical slice',
        "",
        f"Target: `{TARGET}` -> application `{result['application']}`.",
        "",
        f"Order: **{order['by']} {order['direction']}**, verdict "
        f"`{order['verdict']}` from `{order['source']}` (R5). Not an HSP match.",
        "",
        f"Pool: `{result['pool']['name']}.json` ({result['pool']['count']} entries, "
        f"licence {result['pool']['licence']}); scanned {result['scanned']}.",
        "",
        "| # | CAS | name | logS | +/- | gates |",
        "|---|---|---|---|---|---|",
    ]
    for index, row in enumerate(result["candidates"], 1):
        trace = ", ".join(
            f"{gate['gate'].replace('gate.', '')}:{gate['verdict']}" for gate in row["gates"]
        )
        half = round((row["error"]["upper"] - row["error"]["lower"]) / 2, 2)
        lines.append(
            f"| {index} | {row['casrn']} | {row['name']} | {row['value']:.2f} | "
            f"+/-{half} | {trace} |"
        )
    lines += [
        "",
        "## Why this order",
        "",
        "- The only calibrated property that fits this goal is aqueous logS; ascending",
        "  means **most hydrophobic first** (petrolatum-like, not water-loving).",
        "- Every row shows `gate.structure` + `gate.esol`; a RED gate never reaches the",
        "  table.",
        "- logS is a model value with a measured in-domain RMSE bar; it is not a",
        "  measurement of the candidate in petrolatum.",
    ]
    hsp = gates.check("gate.hsp", "8009-03-8")
    probes = [
        ("TEWL claim", "Vazelin benzeri ama TEWL dusuk olsun"),
        ("carcinogen claim", "Kanserojen olmayan bir yag yap"),
        ("unknown goal", "Bana guzel bir sey yap"),
    ]
    lines += [
        "",
        "## Refusal boundary (measured, not prose)",
        "",
        f"- `gate.hsp('8009-03-8')` -> **{hsp['verdict']}**: {hsp['reason']} (R4).",
    ]
    for label, text in probes:
        parsed = targets.parse(text)
        lines.append(f"- {label}: `{text}` -> **{parsed['status']}**: {parsed['reason']}")
    lines.append("- No occlusivity, TEWL, skin feel, stability, safety or cost follows.")
    return "\n".join(lines) + "\n"


def document() -> str:
    return render() + (
        "\n## Reproduce\n\n```\n"
        "python tools/vertical_slice.py --check\n"
        'python mcp/screen.py "Vazelin benzeri cilt koruyucu" --limit 5\n'
        "python tools/build_pool.py --check\n```\n"
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = document()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.is_file() else None
        if current != text:
            print("STALE: docs/S5_PETROLATUM_SLICE.md")
            return 1
        print("OK: S5 document matches a fresh render")
        return 0
    if args.write:
        OUT.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {OUT.relative_to(ROOT)} ({len(text.encode('utf-8'))} B)")
        return 0
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
