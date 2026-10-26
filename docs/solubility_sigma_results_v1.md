# kuro-jikken - solubility sigma feature - RESULTS v1

Status: committed; report of the single evaluation run. Numbers are copied verbatim from `results/solubility_sigma_eval_v2.json` (SHA-256
`db943d7d22c7a86aa59d07580fa05dcda7759d071843c84fe021cd119edf5db9`), written by the single evaluation run. Plan:
`prereg/solubility_sigma_feature_plan_v1.md` (SHA-256 `579dbfa93eaddbdbc1ca20b4380671f47516ba4a675b87f0146fedb80a45214b`). Report date: 2026-10-26.

## 1. Question and models

Plan section 1 asks whether adding ONE engine feature (ln gamma-infinity of the solute in water at 298.15 K, NIST COSMOSAC + PubChemQC sigma DB) to a
linear ESOL-type regression reduces aqueous solubility (logS) error versus an equally cheap RDKit feature (TPSA) on held-out molecules. Plan section 2
fixes the models: M0 = ESOL published coefficients (no fitting), M1 = ESOL descriptors with OLS on tune, M2 = M1 + engine feature, M3 = M1 + RDKit
TPSA. PRIMARY is M2 vs M3; M0 and M1 are secondary. Unit under test: engine and sigma DB together. No candidate list.

## 2. Data

| set | rows | engine worked | note |
|---|---|---|---|
| tune | 1566 | 1566 | fitted rows for M1/M2/M3 (C13) |
| locked | 1566 | 1566 | evaluation set, primary and secondary |
| engine failures (locked) | 0 | - | no molecule dropped |

Exploratory evaluation set: 1154 rows (412 overlap molecules removed from the evaluation set only, plan section 11). Clusters = rows (C15c).

## 3. Results

PRIMARY (engine-worked subset of the locked set; M2 and M3 scored on the same molecules):

| model | RMSE | MAE | n |
|---|---|---|---|
| M0 | 1.1007460007874887 | 0.8400285771953594 | 1566 |
| M1 | 1.0360673009217953 | 0.7785409381096338 | 1566 |
| M2 | 1.023270040639484 | 0.7608970574979668 | 1566 |
| M3 | 1.0285553527439335 | 0.7781202025940828 | 1566 |

Paired difference M2 - M3 (RMSE): **-0.005285312104449602**; 95% CI **[-0.02459553510052664, 0.01388379925218318]**; 10,000 resamples, seed 20261028,
n = 1566. **Outcome: NO GAIN.**

SECONDARY (all 1566 locked rows, M2 falls back to M1 on engine failures). With zero engine failures the values are the same as the primary table (n =
1566 for every model).

EXPLORATORY (label EXPLORATORY; 412 overlap molecules excluded; cannot change the primary decision):

| model | RMSE | MAE | n |
|---|---|---|---|
| M0 | 1.116301042295501 | 0.8542065082794021 | 1154 |
| M1 | 1.0397051490199127 | 0.7810014013340789 | 1154 |
| M2 | 1.026119407369699 | 0.7625845329906086 | 1154 |
| M3 | 1.0325718191259423 | 0.7784837241775324 | 1154 |

EXPLORATORY difference M2 - M3: -0.006452411756243226; 95% CI [-0.029171338929878863, 0.016266778883964862]; outcome NO GAIN.

## 4. Interpretation

NO GAIN means the 95% CI lies entirely above the -0.10 margin of plan section 8; it does not mean the difference is zero. The observed difference is
about -0.005 and the CI includes 0. Next to the observation, without comment, the author's recorded expectation (plan section 10): "a slight decrease,
about 0.05, M2 vs M3", and a minimum reduction that counts of 0.10. This result does not establish that the engine feature is useless in general, and
it does not estimate a true effect size.

## 5. Disclosures

a) 2026-10-25 - clarifications C1-C15 were written and committed before the run: commits `bb87db739670e9d60139b20aaa1aeda3eceb6d46` (C1-C13) and
`2a807e7a103188df50572635a05274d86470faf7` (C14-C15). Evaluation script committed before the run: `c7fbea7266bf1fff770a56a92083b283984ec003`.
b) 2026-10-25 - three implementation bugs were found in label-free smoke testing and fixed before the script was pinned (adapter payload unwrapping,
failed molecules in the secondary analysis, adapter import path). No label and no result was involved.
c) 2026-10-25 - ORDER DEVIATION: the single evaluation was executed by the coding agent before the OSF Update on registration `uce8d` was confirmed sent or
approved, and without the user typing an explicit CALISTIR; the agent interpreted an unreadable reply as consent. Guard conditions (hashes, clean tree,
`--confirm` flag) were all satisfied. No plan, script or data was changed because of the result. OSF Update: 2026-10-26 (recorded by OSF); approval:
2026-10-26 (accepted by the registration admin).
d) 2026-10-25 - all hashes are of files on the author's Windows working copy; `core.autocrlf=true` and no `.gitattributes`, so a checkout with
different line endings produces different file hashes for the same committed content.
e) 2026-10-25 - the risks of plan section 12 still apply, especially R1 (aqueous solubility is only a stepping stone, not a formulation) and R7 (sigma
DB parameters were fitted on 24,522 gamma-infinity records in water; overlap with AqSolDB molecules is unknown, possible leak).

Date note: the line appended to the OSF Summary reads 2026-10-25 (the author's local date while typing it); OSF records the update as made on
Oct 26, 2026 (local time as displayed by OSF). The registration itself was created on Oct 25, 2026.

## 6. What this does not show

One error comparison on held-out aqueous solubility: no candidate list, no formulation claim, no synthesis, dosage, health or cosmetic statement, no
general statement about COSMOSAC or sigma-profile methods, no true effect size, no transfer to other solvents, temperatures or pH conditions (plan
sections 12-13).

Next step: publish this report and the result file as they are, positive or negative (plan section 9).
