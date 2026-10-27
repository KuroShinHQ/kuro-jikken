#!/usr/bin/env python
"""Generate .opencode/skills/lab/labs/al_cu_model.mjs from a bake file.

Why a generator: the page used to carry hand-typed XS/KS/IDS arrays. A hand copy can drift
from the ledger and nobody notices (block 260 measured 0.0048 K of drift from rounding).
Here the anchors are machine-copied from the bake output, and scripts/lab_audit.py checks
the module against the same file and against the engine.

    python scripts/gen_model.py                     # regenerate the module
    python scripts/gen_model.py --check             # fail if the module is stale
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
SRC = ROOT / "data/labs/al_cu_liquidus_r3.json"
OUT = ROOT / ".opencode/skills/lab/labs/al_cu_model.mjs"
SRC_REL = SRC.relative_to(ROOT).as_posix()
TOLERANCE_K = 0.5


def build():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    pts = d["points"]
    if not pts:
        raise SystemExit("bake file has no points")
    prov = pts[0]["provenance"]
    engine = (d["meta"].get("engines") or [prov["engine"]])[0]
    out = []
    out.append("// GENERATED FILE - do not edit by hand.")
    out.append("// Generator: .opencode/skills/lab/scripts/gen_model.py")
    out.append(f"// Source:    {SRC_REL} (baked {d['meta'].get('created')}, head {d['meta'].get('repo_head')})")
    out.append("// Every anchor below is one ledger entry produced by bake.py -> mcp/pipeline.ask.")
    out.append("")
    out.append(f"export const TOLERANCE_K = {TOLERANCE_K}")
    out.append("")
    out.append("export const META = {")
    out.append(f"  engine: {json.dumps(engine)},")
    out.append(f"  dataset: {json.dumps(prov['dataset'])},")
    out.append(f"  created: {json.dumps(d['meta'].get('created'))},")
    out.append(f"  head: {json.dumps(d['meta'].get('repo_head'))},")
    out.append(f"  source: {json.dumps(SRC_REL)},")
    out.append(f"  points: {len(pts)},")
    out.append("}")
    out.append("")
    out.append("// e = half of the bisection bracket (numerical resolution), null when the point")
    out.append("// was solved on the pure-element path and no bracket exists.")
    out.append("export const ANCHORS = [")
    for p in pts:
        err = p.get("error")
        e = None if not err else round((err["upper"] - err["lower"]) / 2, 9)
        out.append(f"  {{ cu: {p['x']!r}, k: {p['value']!r}, e: {e!r}, id: {json.dumps(p['ledger'])} }},")
    out.append("]")
    out.append("")
    out.append("export const REFUSAL = {")
    out.append('  sentence: "Bu madde/veri seti elimizde yok; en yakin kapsam: alloy.phase",')
    out.append('  ledger: "20261026T225932-91f72739",')
    out.append('  gate: "RED",')
    out.append('  reason: "no data",')
    out.append("}")
    out.append("")
    rep = next((p for p in pts if p["x"] == 2.0), pts[-1])
    out.append("// What the answer does not say, verbatim from the ledger entry (limits are not prose we invented).")
    out.append("export const LIMITS = [")
    for lim in rep.get("limits") or []:
        out.append(f"  {json.dumps(lim)},")
    out.append("]")
    out.append("")
    out.append("export function inDomain(cu) {")
    out.append("  return Number.isFinite(cu) && cu >= ANCHORS[0].cu && cu <= ANCHORS[ANCHORS.length - 1].cu")
    out.append("}")
    out.append("")
    out.append("/**")
    out.append(" * The page model. An anchor is returned untouched (k, e, id come from the ledger).")
    out.append(" * Between anchors it interpolates linearly and says so: `exact: false` and a")
    out.append(" * declared +-TOLERANCE_K. Out of domain it returns null - the page then shows the")
    out.append(" * refusal sentence and no number at all.")
    out.append(" */")
    out.append("export function liquidus(cu) {")
    out.append("  if (!inDomain(cu)) return null")
    out.append("  const exact = ANCHORS.find((a) => a.cu === cu)")
    out.append("  if (exact) return { k: exact.k, exact: true, e: exact.e, id: exact.id, tol: 0 }")
    out.append("  for (let i = 1; i < ANCHORS.length; i++) {")
    out.append("    const a = ANCHORS[i - 1], b = ANCHORS[i]")
    out.append("    if (cu > a.cu && cu < b.cu) {")
    out.append("      const t = (cu - a.cu) / (b.cu - a.cu)")
    out.append("      return {")
    out.append("        k: a.k + t * (b.k - a.k), exact: false, tol: TOLERANCE_K,")
    out.append("        kLow: a.k, kHigh: b.k, idLow: a.id, idHigh: b.id,")
    out.append("      }")
    out.append("    }")
    out.append("  }")
    out.append("  return null")
    out.append("}")
    out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    body = build()
    if a.check:
        old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if old != body:
            print(f"STALE {OUT} - run python scripts/gen_model.py")
            return 1
        print(f"OK {OUT} ({len(body)} B)")
        return 0
    OUT.write_text(body, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(body)} B, {body.count('{ cu:')} anchors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
