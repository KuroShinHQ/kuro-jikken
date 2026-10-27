# Candidate pool (S2)

Generated 2026-10-27 by `tools/build_pool.py`; do not edit by hand.
`--check` fails when a file no longer matches its source.

| pool                                   | count | licence             | role                                                                                                               |
|----------------------------------------|-------|---------------------|--------------------------------------------------------------------------------------------------------------------|
| [hsp.json](hsp.json)                   | 1294  | MIT                 | reference-only: annotate or filter a candidate, never order it (R5 verdict REFERENCE_ONLY)                         |
| [melting.json](melting.json)           | 18    | MIT                 | range input for mixture.wax only: feasibility, never a single melting point or a ranking (R5 verdict UNCALIBRATED) |
| [alloy_phases.json](alloy_phases.json) | 3     | ODbL-1.0 + DbCL-1.0 | phase catalogue for alloy.phase: filter, never order (R5 verdict MEASURED_NOT_DECLARED)                            |

A pool entry is not a ranking right. `data/calibration.json` (R5) says
which properties may be ordered; today that is only aqueous logS and
gamma-infinity, so the HSP, wax and phase pools are filters/annotations.

Sources:

- HSP: chemicals 1.5.2 (MIT) Hansen tables; sources inside the package: HSPiPy, WDR Schrier 2020, Manuel-Ruben 2022, Alshehri-Hansen 2022 (MIT).
- Melting: chemicals 1.5.2 (MIT) Tm/Hfus tables (DIPPR/TRC compilations) (MIT); curated CAS list only.
- Phases: MatCalc open TDBs in data/alloy_tdb; only ELEMENT and PHASE names are recorded, no Gibbs coefficients (ODbL-1.0 + DbCL-1.0).
