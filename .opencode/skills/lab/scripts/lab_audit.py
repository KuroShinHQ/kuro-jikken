#!/usr/bin/env python
"""Audit the lab page model against the ledger (L10).

Checks, in order:
  1. model <-> bake file      the generated ANCHORS are the bake points, 1:1, exact floats
  2. model <-> ledger         every anchor id exists in runs/router/*.jsonl with the same value
  3. page <-> model           the page imports the model (no hand-typed XS/KS/IDS arrays)
  4. refusal                  the page's refusal branch shows no number, only the dash
  5. interpolation (--compute) every midpoint between anchors vs the live engine, <= TOLERANCE_K

    python scripts/lab_audit.py            # fast checks
    python scripts/lab_audit.py --compute  # + 20 pycalphad midpoints (~40 s)
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
LAB = ROOT / ".opencode/skills/lab"
MODEL = LAB / "labs/al_cu_model.mjs"
PAGE = LAB / "labs/al_cu_liquidus.html"
SRC = ROOT / "data/labs/al_cu_liquidus_r3.json"
LEDGER = sorted((ROOT / "runs/router").glob("*.jsonl"))

ANCHOR_RX = re.compile(r'\{ cu: ([\d.]+), k: ([\d.]+), e: (null|[\d.]+), id: "([^"]+)" \}')


def parse_model():
    text = MODEL.read_text(encoding="utf-8")
    tol = float(re.search(r"export const TOLERANCE_K = ([\d.]+)", text).group(1))
    anchors = [
        {"cu": float(a), "k": float(b), "e": None if c == "null" else float(c), "id": d}
        for a, b, c, d in ANCHOR_RX.findall(text)
    ]
    return tol, anchors


def load_ledger():
    ids = {}
    for f in LEDGER:
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            ids[e["id"]] = e
    return ids


def check_model_vs_bake(anchors):
    pts = json.loads(SRC.read_text(encoding="utf-8"))["points"]
    bad = []
    if len(anchors) != len(pts):
        bad.append(f"count {len(anchors)} != {len(pts)}")
    for a, p in zip(anchors, pts):
        if a["cu"] != p["x"] or a["k"] != p["value"] or a["id"] != p["ledger"]:
            bad.append(f"{a['cu']}: model {a['k']} / {a['id']} vs bake {p['value']} / {p['ledger']}")
    return bad


def check_model_vs_ledger(anchors, ledger):
    bad = []
    for a in anchors:
        e = ledger.get(a["id"])
        if e is None:
            bad.append(f"{a['id']}: not in any runs/router/*.jsonl")
            continue
        ans = e.get("answer") or {}
        v = ans.get("value")
        if not isinstance(v, (int, float)):
            bad.append(f"{a['id']}: ledger value is {v!r}, not a number")
        elif abs(v - a["k"]) > 1e-9:
            bad.append(f"{a['id']}: ledger {v} != model {a['k']}")
        if ans.get("unit") != "kelvin":
            bad.append(f"{a['id']}: unit {ans.get('unit')!r}")
    return bad


def check_page():
    bad = []
    pages = [PAGE, PAGE.parent / "al_cu_sheet.html"]
    for page in pages:
        if not page.exists():
            bad.append(f"{page.name}: missing")
            continue
        html = page.read_text(encoding="utf-8")
        if "from './al_cu_model.mjs'" not in html:
            bad.append(f"{page.name}: does not import ./al_cu_model.mjs")
        if "ANCHORS" not in html:
            bad.append(f"{page.name}: does not use ANCHORS")
        for hand in ("const XS = [", "const KS = [", "const IDS = [", "const ES = ["):
            if hand in html:
                bad.append(f"{page.name}: hand-typed array still in page: {hand}...")
    html = PAGE.read_text(encoding="utf-8")
    m = re.search(r"function showRefusal\(\) \{(.*?)\n\}", html, re.S)
    if not m:
        bad.append("showRefusal() not found")
    else:
        body = m.group(1)
        dash = "\u2014" in body or r"\u2014" in body
        if "_hv.textContent" not in body or not dash:
            bad.append("refusal does not overwrite the hero with a dash")
    return bad


def check_interpolation(anchors, tol):
    """Midpoints: the page model vs the live engine. This is the declared-tolerance check."""
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "mcp"))
    import pipeline  # noqa: E402  (mcp/ is a flat module dir, not a package)

    tpl = json.loads(SRC.read_text(encoding="utf-8"))["meta"]["payload_template"].replace("{cu}", "0")
    payload_tpl = json.loads(tpl)
    worst, bad, rows = 0.0, [], []
    for a, b in zip(anchors, anchors[1:]):
        cu = round((a["cu"] + b["cu"]) / 2, 4)
        payload = dict(payload_tpl, cu_wt_pct=cu)
        _plan, ans = pipeline.compute(f"Al-{cu} wt% Cu alasimi erir mi", payload)
        if ans.get("value") is None:
            bad.append(f"cu={cu}: engine refused ({ans.get('sentence')})")
            continue
        interp = a["k"] + (b["k"] - a["k"]) * (cu - a["cu"]) / (b["cu"] - a["cu"])
        d = abs(interp - ans["value"])
        worst = max(worst, d)
        rows.append((cu, ans["value"], interp, d))
        if d > tol:
            bad.append(f"cu={cu}: |{interp:.4f} - {ans['value']:.4f}| = {d:.4f} K > {tol} K")
    return bad, worst, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compute", action="store_true")
    a = ap.parse_args()
    if not MODEL.exists():
        print(f"FAIL model-missing {MODEL}")
        return 1
    tol, anchors = parse_model()
    ledger = load_ledger()

    checks = [
        ("model<->bake", check_model_vs_bake(anchors)),
        ("model<->ledger", check_model_vs_ledger(anchors, ledger)),
        ("page<->model", check_page()),
        ("tolerance", [] if 0 < tol <= 5 else [f"TOLERANCE_K={tol} outside (0, 5]"]),
    ]
    worst = None
    if a.compute:
        bad, worst, rows = check_interpolation(anchors, tol)
        checks.append(("interp<->engine", bad))
        for cu, eng, interp, d in rows:
            print(f"  cu={cu:<5} engine={eng:>12.4f}  model={interp:>12.4f}  d={d:.4f} K")

    ok = True
    for name, bad in checks:
        print(f"{'PASS' if not bad else 'FAIL'} {name}" + ("" if not bad else f" ({len(bad)})"))
        for b in bad:
            print(f"     {b}")
        ok = ok and not bad
    print(f"anchors={len(anchors)} tolerance={tol} K" + (f" worst_midpoint={worst:.4f} K" if worst is not None else ""))
    print("RESULT", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
