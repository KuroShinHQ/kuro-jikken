# Cosmetics pool (S4)

Generated 2026-10-28 by `tools/build_cosmetics.py`; do not edit by hand.
`--check` fails when a file no longer matches its sources.

| pool | count | licence | role |
|---|---|---|---|
| [cosmetics.json](cosmetics.json) | 2,560 | ODbL-1.0 + DbCL-1.0 + CC-BY-4.0 | reference-only: INCI identity, CosIng function and label frequency; never a formulation, never a safety claim, never a ranking |

## What the numbers mean

- 79,010 product records in the Open Beauty Facts dump; 20,185 carry a readable INCI list.
- 47,215 distinct label tokens; 3,600 occur on at least 5 products.
- 2,560 of those match a CosIng record (71.1 %). Unmatched tokens are label noise or names outside CosIng, and are counted, not dropped.

## What it is not

- making a formulation (a concentration needs a lab, not a label count)
- safety, efficacy or medical claims
- market share: OBF is crowd-sourced, not a sales panel
- ordering ingredients by performance

Sources:

- Open Beauty Facts dump: 9173863ea9f52a3a... (ODbL-1.0 + DbCL-1.0).
- CosIng: cf16c156286ed1be... (CC-BY-4.0), 4,065 records.
