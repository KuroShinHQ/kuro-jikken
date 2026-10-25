# AMENDMENT PROPOSAL (post-hoc · decided after seeing validation results)

**Date:** 2026-10-25
**Status:** PROPOSED — not applied. The locked set has not been opened; the
pre-registered results stand unchanged.

## Observation that motivated this proposal

The pre-registered run on AqSolDB (tune+validation) shows most of the RMSE is
carried by molecule classes outside ESOL's intended domain:

| group | n | MAE | RMSE |
|---|---|---|---|
| metal-containing | 60 | 3.868 | 4.554 |
| multi-component (salts/mixtures, contains ".") | 761 | 2.909 | 4.560 |
| MW>500 | 205 | 2.513 | 3.494 |
| charged species | 450 | 1.067 | 1.365 |
| **neutral single-component organic, MW<=500** | **5,718** | **0.928** | **1.222** |

On ESOL's actual target domain the predictor performs near the published
ballpark (RMSE ~1.0-1.2).

## Proposed applicability-domain rule (for a FUTURE round, not this one)

Report ESOL predictions only for molecules that are:
1. single-component (no "." in SMILES),
2. uncharged as written (no formal charges),
3. containing no metal atoms,
4. molecular weight <= 500.

Everything else is reported as "outside applicability domain" and excluded from
aggregate scores — but listed separately, never silently dropped.

**This text and the sentence "decided after seeing validation results" are the
record.** If the rule is adopted, it must be adopted in a dated amendment before
any new locked/practice evaluation, and both pre-registered and amended numbers
must be published side by side.
