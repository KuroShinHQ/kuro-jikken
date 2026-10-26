# Alloy heat-resistance scorecard - plan v0 (NOT registered, NOT run)

Status: plan only. No calculation, no result, no number written by an agent.
Every value marked [AUTHOR TO DECIDE] is the captain's to fill.

## 1. One question

For alloy compositions that lie inside the assessed range of one licensed TDB,
does pycalphad reproduce a published solidus (and liquidus) temperature within
a stated tolerance?

Directional, not confirmatory: we ask whether the engine tracks reality closely
enough to rank candidates, not whether it replaces an experiment.

## 2. Hypotheses

- H1: for in-domain compositions, |computed - published| solidus is below
  [AUTHOR TO DECIDE] K.
- H2: the error is smaller inside the assessed composition range than outside
  it. If H2 fails, the in-domain flag is useless and must be withdrawn.

## 3. Scoring (fixed before any run)

- one point = one (system, composition, quantity) triple;
- error = computed - published, in K; report mean absolute error and the count
  inside tolerance;
- a point is PASS if |error| <= [AUTHOR TO DECIDE] K;
- no weighting, no exclusions after the fact, no re-runs to improve a number.

## 4. Sets

- tune set: [AUTHOR TO DECIDE] points, used only to fix the calculation recipe;
- locked set: [AUTHOR TO DECIDE] points, opened once after the recipe is frozen;
- locked set hash recorded before opening; run is single-shot.

## 5. In-domain rule (input only)

A point is in-domain if and only if: every element of the composition appears in
the TDB, the composition lies inside the assessed range printed in the TDB
header, and every phase that the equilibrium returns is one the TDB models. No
knowledge of the published value may enter this rule.

## 6. Data

Only TDB files and reference points whose licence and SHA-256 are recorded in
the manifest. Today that is **no system**: see `docs/TARGET_ALLOY_HEAT_SURVEY.md`
section 3. This plan cannot start until that changes.

## 7. Out of scope

Corrosion, coating life, creep, oxidation, cost, manufacturability. The
scorecard says nothing about "better alloy", only "matches the published
solidus inside the stated range".

