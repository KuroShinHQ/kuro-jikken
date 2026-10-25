# kuro-jikken - solubility sigma feature - Pre-registration PLAN v1 (DRAFT)

Status: PLAN ONLY. No engine run, no error/RMSE/feature value computed, no AqSolDB
label used beyond counting.

Order rule: this plan -> OSF registration -> only then any evaluation.

Supersedes `prereg/formulation_screening_plan_v0.md` (archived, never registered).

## 1. Question

One narrow question:

> Does adding **one** feature from the NIST COSMOSAC engine (log gamma-infinity
> of the solute in water, from the precomputed PubChemQC sigma-profile DB) to a
> linear ESOL-type regression **reduce error in predicting aqueous solubility
> (logS)** on held-out molecules?

Unit under test: **engine + this new non-peer-reviewed sigma DB**, together.
This study produces **no candidate list**.

## 2. Models (fixed now)

| id | model |
|---|---|
| **M0** | ESOL with its **published coefficients** (no fitting) |
| **M1** | ESOL descriptors, **refit on the tune set** |
| **M2** | M1 + the **engine feature**, refit on the same tune set |

- **Primary comparison: M2 vs M1.** Secondary: **M0**.
- **One primary engine: NIST COSMOSAC.** Other engines are exploratory only.
- ESOL descriptors fixed: logP, molecular weight, rotatable bonds, aromatic
  proportion. M0 uses the published coefficients, not refit.

## 3. Data and identity rules (written before any test)

**Source labels:** AqSolDB (CC0 1.0, Harvard Dataverse DOI `10.7910/DVN/OVHAW8`),
9,982 molecules, aqueous solubility logS. **Source profiles:** PubChemQC
sigma-profile DB v1.0.0, Zenodo `10.5281/zenodo.20672192` (preprint-level).

**Matching key rule:** exact **full 27-character InChIKey**. No CID match
(AqSolDB has no CID column); no first-block match; no stereo/protonation
normalisation. Rows with empty InChIKey are excluded.

**One-profile-per-molecule rule (rule only, not tested):**

1. Identity = full InChIKey.
2. Prefer rows whose SMILES parses to **formal charge 0**; if no neutral row
   exists, keep all rows for that key and log the key.
3. Among eligible rows, take the **lowest PubChem CID**; tie -> lowest file row.
4. Water therefore uses **CID 962** (six rows share its InChIKey; the other five
   CIDs are logged, not used).
5. Every dropped duplicate is counted and reported; no profile averaging.

## 4. In-domain rule (depends on INPUT only)

A molecule enters the evaluation set only if **all** hold, checked before any
label comparison:

- neutral (formal charge 0) and **single component** (no `.` in SMILES);
- elements only from whitelist **C, H, N, O, S, F, Cl, Br, I** (no P, no metals);
- molecular weight <= **[AUTHOR TO DECIDE]** g/mol;
- present in the sigma DB after the one-profile rule;
- AqSolDB logS present and numeric.

**Engine numerical failure is not an exclusion.** For that molecule M2 falls
back to the M1 prediction; the failure count and affected keys are reported.
The word "benign" is not used; if ever used, it requires a machine-checkable
file committed with its SHA-256.

## 5. Split, tune set, locked set

- **Molecule-level split only** (never pair-level or row-level).
- **New seed: `20261027`.** The previous ESOL question used seed `20261026`.
- The **tune/development set** is for fitting M1/M2 and for all development
  choices; it is never reported as confirmation.
- **New locked set** `data/solubility/split_locked_v2.csv` is built at Freeze-2
  and committed with `LOCKED_V2.sha256` **before any evaluation**; it is opened
  **once**, after the plan is registered.
- **Disclosure:** the earlier ESOL locked set of this repo was already opened
  once. The molecule overlap between old and new locked sets is computed at
  Freeze-2 and declared in the lock file; overlapping molecules are not
  presented as new evidence.

## 6. Metrics and decision rule

- **Primary: RMSE** on the locked set, M2 vs M1.
- Secondary: MAE; **bootstrap CI clustered by molecule**; **paired difference
  M2 - M1** (negative favours the engine feature).
- **Success margin:** [AUTHOR TO DECIDE] (the minimum RMSE reduction that counts
  as a real difference).
- **Sample size / power reasoning:** the rule is to size the locked set from the
  paired-difference SD observed on the tune set, targeting 80% power at the
  chosen margin, with a minimum of [AUTHOR TO DECIDE] molecules; the resulting
  number is written before the lock is opened.
- Tune vs locked purpose: tune = fitting and pipeline development; locked =
  one-shot confirmation, no changes after opening.

## 7. Hypotheses

- **H1 only:** M2 RMSE is lower than M1 by at least the success margin on the
  locked set.
- Everything else is **EXPLORATORY**. Any exploratory claim must map to a
  pre-defined measurable category; otherwise it is not tested here.
- Failed hypotheses will be published.

## 8. Author expectations

**[AUTHOR TO DECIDE]**

- Expected RMSE reduction: [AUTHOR TO DECIDE]
- Minimum reduction that counts: [AUTHOR TO DECIDE]

No number is written by the agent in this section.

## 9. Deviations

This clause covers **all sections** of this plan, not only scoring: any change
to question, models, data, identity rules, in-domain rule, split, seed, locked
set, metrics, hypotheses or reporting must be recorded as a dated deviation
before it is applied, with its reason and its effect on the analysis.

## 10. Risks

- **R1** Aqueous solubility is only a stepping stone, not a formulation.
- **R2** Solids need melting data; AqSolDB lacks it.
- **R3** The sigma DB is a non-peer-reviewed, preprint-level source.
- **R4** Engine and DB are evaluated jointly (cannot separate their effects).
- **R5** LGPL engines run as separate processes; this is not legal advice.
- **R6** The earlier ESOL locked set was opened once; overlap must be declared.

## 11. Scope prohibitions

No candidate list in this study. No synthesis, dosage, health or cosmetic
claims. The output is an error comparison and a published result, positive or
negative.

## 12. Freeze and registration order

1. This plan (v1) -> 2. Freeze-1: OSF registration -> 3. Freeze-2: new seed,
locked set and SHA-256 committed -> 4. one evaluation -> 5. report, including
failures and deviation log.
