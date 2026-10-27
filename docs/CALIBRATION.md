# Calibration ledger (R5)

Date: 2026-10-27. Git head `2e21943`. Machine copy: `data/calibration.json`.
Audit: `tools/calibration_check.py` (exit 0 = every property has a measured error, a source,
and a declared bar that matches the verdict).

## Why this file exists

`screen()` (Faz S) is allowed to rank candidate substances. A ranking without an error bar is
an invented answer. This ledger fixes, per **property** (not per engine), three things:

1. what was measured, against which dataset, with how many points;
2. what error the answer declares;
3. whether the declaration covers the measurement (`CALIBRATED`) or not.

Only `CALIBRATED` properties may be used for ranking. The rule is enforced in code, not by
memory: `calibration_check.py` recomputes every metric from the stored rows (or from the
2399-row locked solubility CSV) and fails when a bar is smaller than its measured error but
still labelled `CALIBRATED`.

## Verdicts

| Verdict | Meaning |
|---|---|
| `CALIBRATED` | measured error exists and the declared bar covers it (bar = typical error, not a bound) |
| `MEASURED_NOT_DECLARED` | error measured but the answer declares no comparable bar (e.g. only the bisection bracket) |
| `UNCALIBRATED` | no independent measurement in this repo; range/refusal use only, never ranking |
| `REFERENCE_ONLY` | value from a compilation, ranking heuristic only |
| `DEFINITION` | exact by definition, no model error |

## Ledger

| Property | Engine | Measured error | Declared bar | Verdict |
|---|---|---|---|---|
| logS, aqueous 25 C | ESOL (Delaney 2004) + RDKit | in-domain RMSE **1.2246** (n=1917, MAE 0.919); whole set RMSE 2.139; out-of-domain RMSE 4.099 (n=482) | ±1.2 in-domain / ±5.0 out | **CALIBRATED** |
| gamma-infinity in water | Dortmund UNIFAC (thermo 0.6.1) | median abs **21.3 %**, max 46.1 % (diacetyl), 7/9 within 30 % (n=9) | ±30 % | **CALIBRATED** |
| gamma-infinity, COSMO-SAC route | cCOSMO-SAC + PubChemQC sigma | median abs **36 %**, max 109 %, 3/9 within 30 % | none (not exposed) | MEASURED_NOT_DECLARED |
| liquidus / melting point | pycalphad 0.11.2 + MatCalc open DBs | MAE **2.17 K**, max **8.3 K** (7 points); pure elements 0.01-0.24 K | only the bisection bracket 0.02-0.34 K | MEASURED_NOT_DECLARED |
| wax appearance range | ideal SLE (gamma = 1), `chemicals` Tm/Hfus | none | physical range only | UNCALIBRATED |
| average molecular weight | RDKit `Descriptors.MolWt` | exact by definition | ±0 | DEFINITION |
| Crippen logP | RDKit `Crippen.MolLogP` | none in this repo | **no bar at all** | UNCALIBRATED |
| Hansen parameters and Ra | `chemicals` compilation | none | "ranking only" | REFERENCE_ONLY |

`screen()` may rank on exactly two properties: **aqueous logS** and **gamma-infinity
(Dortmund UNIFAC)**. Everything else is a range, a heuristic or a definition.

## What the audit found (new on 2026-10-27)

1. **The ESOL bar is real, but it is an in-domain bar.** The 2399-molecule locked set gives
   RMSE 2.139 overall; the 1.2 bar holds only for the in-domain group (n=1917, RMSE 1.2246,
   neutral, single component, no metal, MW <= 500, no phosphorus). Out-of-domain rows give
   RMSE 4.099 and the declared 5.0 covers them. Quoting 1.2 for a salt or a metal complex is
   wrong; the gate already refuses those, and the ledger now records why.
2. **The CALPHAD answer declares only the bisection bracket.** `±0.34 K` is numerical
   resolution, and the answer's own `limits` say so. The database error against published
   values is up to 8.3 K (Al-17.3 at% Cu, next to the eutectic, where a printed-diagram
   read-off is itself about ±2 K). Consequence: alloy liquidus may be reported, but adjacent
   compositions cannot be ranked at the 2 K level. A model-error bar for CALPHAD is a
   follow-up (R3b), not something this ledger may invent.
3. **UNIFAC's ±30 % is a median bar.** 7 of 9 solutes pass it; diacetyl (two adjacent
   carbonyls, a known UNIFAC gap) is 46 % low. Ranking is allowed, but ties inside 46 % are
   not separable.
4. **Crippen logP carries no error bar at all.** The adapter returns a number and no `error`
   field, while molecular weight gets a definitional zero-width bar. This is why logP is
   `UNCALIBRATED` here: it must not be ranked or presented as a measured partition
   coefficient until a measured logP set is added.
5. **Wax is unvalidated by construction** (gamma = 1). It stays a YELLOW range; the ledger
   makes that a machine-readable fact instead of a sentence in a document.

## Reproduce

```
.venv_inventory\Scripts\python.exe tools\calibration_check.py
.venv_inventory\Scripts\python.exe tools\calibration_check.py --strict
.venv_inventory\Scripts\python.exe tools\gamma_validation.py
.venv_inventory\Scripts\python.exe tools\alloy_liquidus.py
```

Last run (2026-10-27 16:36, `--strict` also exit 0): `8 entries`, `CALIBRATED 2`, `MEASURED_NOT_DECLARED 2`,
`UNCALIBRATED 2`, `REFERENCE_ONLY 1`, `DEFINITION 1`, `RESULT PASS`, exit 0.
Locked ESOL recomputed live: in n=1917 rmse 1.2246 | out n=482 rmse 4.0989 | all n=2399 rmse 2.1387.
Full suite after the ledger landed: `464 passed` (74.44 s), of which 10 are `tools/tests/test_calibration.py`.

## Limits

- One data source per property. UNIFAC is water at 298 K only; CALPHAD is Al-Cu plus three
  pure elements; ESOL is AqSolDB at 25 C. None of this is a general validation.
- A `CALIBRATED` bar is a typical error, not a worst case: ESOL misses 36 % of in-domain
  molecules by more than 1.0 log unit, and UNIFAC's tail reaches 46 %.
- Version-bound: changing RDKit, thermo, ugropy, pycalphad or a TDB invalidates the entry.
  The checker warns on drift (`--strict` makes it fatal).
- The ledger says what a number is worth, not what a material does. No occlusivity, TEWL,
  skin feel, emulsion stability, creep or corrosion follows from any entry here.
