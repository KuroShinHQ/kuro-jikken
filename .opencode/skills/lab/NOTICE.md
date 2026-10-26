# NOTICE - vendored third-party code

## AirsupHQ/machine-skill

- Source: https://github.com/AirsupHQ/machine-skill
- Licence: MIT, Copyright (c) 2026 Airsup (full text in `LICENSE`)
- Vendored on: 2026-10-27, upstream commit `main` at clone time
- Copied: `kit/`, `scripts/`, `references/`, `LICENSE`
- Not copied: `examples/`, `film/`, `evals/`, `.github/` (upstream reference
  pages are 10 MB of rendered machines; they are not needed to run the skill)

### What we changed

| File | Change |
|---|---|
| `kit/lab-kit.js` | MIT header prepended; nothing else yet (L2 will add lab materials/geometry) |
| `scripts/*.mjs` | MIT header prepended; code unchanged |
| `SKILL.md` | **replaced** by our own lab skill (`SKILL.md`); upstream kept as `SKILL.upstream.md` for reference |
| `references/solvers.md` | kept as upstream reference; our engine map is `references/engines.md` |

### Why fork instead of depend

The upstream skill writes a small solver inside each page. kuro-jikken already
has validated, gated engines behind a ledger, so the page must **not** re-derive
physics in JavaScript. `scripts/bake.py` runs `mcp/pipeline.ask` over a grid at
build time and the page only interpolates between ledger-backed points.
