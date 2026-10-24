# Pre-registered evaluation plan (Task 8)

Written and committed BEFORE any evaluation. Dataset: AqSolDB (CC0-1.0, DOI 10.7910/DVN/OVHAW8), see data/solubility/SOURCE.md. Exclusions and split: data/solubility/EXCLUSIONS.md (seed 20261025; tune 4796 / validation 2398 / locked 2399).

## Predictors

**P-A (published ESOL coefficients).** logS = 0.16 - 0.63*clogP - 0.0062*MW + 0.066*RB - 0.74*AP
- Source: Delaney, J.S. *ESOL: Estimating Aqueous Solubility Directly from Molecular Structure*, J. Chem. Inf. Comput. Sci. 2004, 44, 1000-1005.
- Cross-checked 2026-10-25 against two independent reproductions (Pat Walters solubility repo; ChemAudit docs) which quote the same coefficients.

**P-B (refit on tune only).** Same equation form; ordinary least squares refit on the tune split; coefficients frozen before validation and locked runs.

## Metrics and traffic lights (stated in advance)

All errors in log units (logS, mol/L), error = predicted - measured. Aggregate metrics per split: RMSE, MAE, bias, fraction |error| <= 0.5, fraction |error| <= 1.0, and the same metrics per molecule class.

| metric | green | yellow | red |
|---|---|---|---|
| RMSE | <= 1.00 | 1.00-1.50 | > 1.50 |
| MAE | <= 0.75 | 0.75-1.00 | > 1.00 |
| abs(bias) | <= 0.15 | 0.15-0.35 | > 0.35 |
| frac within 0.5 | >= 0.55 | 0.40-0.55 | < 0.40 |
| frac within 1.0 | >= 0.80 | 0.65-0.80 | < 0.65 |

Molecule classes (documented SMARTS, priority order): acid `[#6](=O)[OX2H1]`, amine `[#7;X3;v3;!$(N-[#6]=O);!$(N=*)]`, alcohol `[OX2H1;!$(O-[#6]=O)]`, aromatic `a`, halogen `[#9,#17,#35,#53]`, else other.

## Evaluation order

1. tune: fit P-B coefficients, sanity-check both predictors.
2. validation: report both predictors (no tuning allowed after this point).
3. locked: `evaluate.py --final` exactly once, only after LOCK.sha256 matches; appends to LOCK_ACCESS_LOG.md.

The locked set is never used for any decision. No manual exclusions after this plan is committed.

## Predictions (to be filled by the author)

The author fills this section BEFORE the locked run (values are the author's forecasts, not results):

- P-A RMSE on validation: ____ log units
- P-B RMSE on validation: ____ log units
- P-B vs P-A (better / same / worse): ____
- fraction within 1.0 log units (P-A, validation): ____
- worst molecule class: ____

If predictions miss, that is reported, not hidden.
