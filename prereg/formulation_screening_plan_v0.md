# kuro-jikken · formulation-screening · Pre-registration PLAN (v0 — DRAFT, not registered yet)

Working name: **formulation-screening**.
Status: **PLAN ONLY.** No model has been run, no error has been computed.
Order rule: **this plan → OSF registration → only then any benchmark run.**

Written 2026-10-25, before any engine evaluation on this question.

## 1. Question

One narrow question:

> **Can an open-source thermodynamic engine rank simple two-component
> liquid mixtures (miscible / partially miscible / immiscible) more
> accurately than a naive baseline, for small benign molecules that are
> in-domain for the engine?**

It is a *screening* question: the engine produces a ranked shortlist of
testable hypotheses for later lab work. It does **not** produce
formulations, synthesis routes, or any health/cosmetic claim.

## 2. Hypotheses

Directions are fixed now. If the data contradict them, the contradiction
is published too.

- **H1.** Engine-based ranking beats a naive baseline (see §6) on the
  locked test set, by at least the margin defined in §6.
- **H2.** Engine errors are smaller for pairs where both components are
  covered by the precomputed sigma-profile database than for pairs where
  at least one component is missing (the latter are expected to be
  excluded by the in-domain rule anyway — H2 is a check that the rule is
  not silently dropping hard cases).
- **H3.** Most remaining failures are *domain/coverage* failures
  (missing component, unsupported electrolyte/ionic species), not
  sign errors on well-covered neutral organic pairs.

Failed hypotheses are written up and released as well.

## 3. Materials (data — only what was verified in discovery)

| item | version / size | identifier or hash | licence |
|---|---|---|---|
| PubChemQC sigma-profile DB | **1.0.0** (2026-06-12) | Zenodo `10.5281/zenodo.20672192` | **CC-BY-4.0** |
| └ `sigma_profiles_main.parquet` | 122,228,196 B | sha256 `8e1c4d21acee25b04ad5e63b0c846f98524b0b5d1554d1426b9616de5a62da2c` | CC-BY-4.0 |
| └ `sigma_profiles_main_raw.tar.gz` | 267,004,610 B | sha256 `c43eb96b087da5a1de29b5acc0769965b9cb26501e87f0a7c0946ef7bfdd71fe` | CC-BY-4.0 |
| └ `sigma_profile_index.parquet` | 18.54 MB | **sha256 computed by us after download** (absent from publisher MANIFEST) | CC-BY-4.0 |
| └ `sequential_final_params.json` | — | **sha256 computed by us**; parameter pairing **not stated in README → must be confirmed before use** | CC-BY-4.0 |
| NIST COSMOSAC reference impl. | GitHub `usnistgov/COSMOSAC`, 2026-07 | licence **MIT** | MIT |
| RDKit + ESOL | 2026.9.1 | licence **BSD-3-Clause** (ESOL card already in repo) | BSD-3-Clause |
| Experimental reference data for scoring | **NOT DECIDED** | R3: Fingerhut 2017 data location/licence unverified → **do not use until clear** | unknown |

Peer-review status of the sigma DB: the Zenodo record carries **no
journal/preprint identifier**, README says "Paper 1" → treat as
**preprint / not peer-reviewed** until shown otherwise.

## 4. Engines (each runs as a separate tool process; the agent interprets)

- **E1** NIST COSMOSAC (MIT) — activity-coefficient reference engine.
- **E2** openCOSMO-RS_py / _cpp (LGPL-3.0) — independent second engine.
- **E3** COSMOPharm (MIT) — solubility/miscibility wrapper.
- **E4** RDKit + ESOL (BSD-3) — already in repo; miscibility proxy only.
- **B0** baseline, no engine: a fixed lookup rule written down in §6.

LGPL engines are invoked as **separate processes (MCP/subprocess)**, not
linked into closed code. This is a working interpretation, not legal
advice.

## 5. Procedure and freezes

1. **Data freeze.** Download the sigma DB files in §3, record our own
   SHA-256 for the two files missing from MANIFEST, confirm which
   parameter file pairs with them. Any mismatch → stop and report.
2. **In-domain rule freeze.** Written down in §8 *before* any error is
   computed: a pair is in-domain only if (a) both components are neutral
   organics present in the sigma DB, (b) no salt/ionic species, (c) both
   are in the benign list used by this repo. The rule is **not** tuned
   afterwards.
3. **Seeded split.** A random seed is fixed and committed; pairs are
   split into a development part and a **locked test set**.
4. **Lock hash committed BEFORE any evaluation.** The locked set is
   written to a file, its SHA-256 is committed to git, and the file is
   then not opened until the single evaluation run.
5. **The locked set is opened once.** One run, one report; no re-runs
   with changed settings on the locked set.
6. **Order rule:** plan → OSF registration → only then any benchmark run.

## 6. Scoring (defined in advance)

- **Labels.** Each test pair has an experimental class from the chosen
  reference source: `miscible`, `partially_miscible`, `immiscible`.
- **Baseline B0 (fixed now):** "both components in the same polarity
  class (defined by a published logP/functional-group table) →
  miscible, otherwise immiscible", with `partially_miscible` never
  predicted. Any tie is broken by the lexicographic order of the CIDs.
- **Primary metric:** macro-F1 over the three classes, on in-domain
  pairs only.
- **Success margin (H1):** engine must beat B0 by **≥ 0.05 macro-F1**.
  A tie or a smaller margin is reported as *no gain*.
- **Secondary metrics:** per-class recall; coverage = fraction of pairs
  the engines claim to handle (must be reported next to accuracy —
  accuracy on a cherry-picked subset is not a result).
- **Tolerances for continuous outputs** (where an engine returns a
  number, e.g. activity coefficient): absolute error threshold and
  relative error threshold are fixed here — **|Δ ln γ∞| ≤ 0.3** counts
  as correct for ranking purposes; anything else is a miss.
- Every engine result carries a **confidence mark**: 🟢 in-domain, 🔴
  out-of-domain (never scored), plus its error bar.

## 7. Analysis

- **Main result:** the pre-registered comparison of E1–E4 vs B0 on the
  locked set, all hypotheses H1–H3, all engines, no exclusions.
- **Exploratory analyses** (pairwise engine disagreement, outlier
  molecules, sensitivity to the parameter file, subgroup cuts) are
  reported in a **separate, clearly labelled section** and are never
  presented as confirmation of H1–H3.
- Nothing that fails is deleted; deviations are logged under §10.

## 8. In-domain rule (freeze BEFORE any error is computed)

An engine may claim a pair only if **all** of the following hold:

1. Both components are present in the sigma-profile DB (by PubChem CID);
2. Both are **neutral** organics (no counter-ions, no salts, no
   strong electrolytes, no surfactant micelle modelling);
3. Both are on this repo's benign, small-molecule list;
4. The engine does not return a numerical failure or a physically
   impossible value (e.g. negative activity coefficient).

Everything else is marked **OUT-OF-DOMAIN (🔴)**, excluded from scoring,
and reported as coverage. Molecules missing from the DB are
**OUT-OF-DOMAIN — not computed with ORCA** (see R1).

## 9. Author's expectations (written before any run)

These are my predictions, recorded 2026-10-25, before any evaluation:

| id | expectation |
|---|---|
| E1 | E1 (NIST COSMOSAC) macro-F1 on the locked set: **0.72** |
| E2 | best engine beats B0 by **0.10 ± 0.05** macro-F1 (H1 direction: yes) |
| E3 | coverage of the in-domain rule: **≥ 60 %** of candidate pairs |
| E4 | of the failures, **≥ 50 %** are coverage/domain failures (H3) |
| E5 | the two engines disagree on **< 15 %** of in-domain pairs |

If the measured values differ, the expectations are reported as missed —
they are not adjusted after the fact.

## 10. Deviations and transparency

- ORCA is **not used**: its free licence is "academic and personal use,
  if you qualify", and I am an independent researcher without an
  institution. Qualification is not assumed (R1).
- The sigma DB may be a preprint (§3). If it is later superseded, the
  version and hashes used here stay on record.
- Any change to §6/§8 after this file is a **deviation**, is appended to
  this document with a date, and the original text is never rewritten.

## 11. Scope and limitations

- **R1** ORCA licence status unconfirmed for my case → open path only;
  DB-missing molecules are OUT-OF-DOMAIN, never computed.
- **R2** recalibrated COSMO-SAC parameters: the exact parameter file
  pairing must be confirmed before any run.
- **R3** the 29,173 γ∞ points attributed to Fingerhut 2017: download
  location and licence unverified → not used until clear.
- **R4** γ∞ benchmarks **do not measure real cream/ointment
  compositions**. Nothing here is a formulation, a recipe, or a
  health/cosmetic claim.
- **R5** LGPL engines run as separate processes; interpretation, not
  legal advice.

## 12. Candidate-list skeleton (output format)

Each candidate is a **testable hypothesis**, never a recipe:

```
- hypothesis: "<pair> is immiscible at 25 °C"   # direction stated
  engine: E1 (COSMOSAC)                          # which engine
  in_domain: true|false                          # 🔴/🟢
  prediction + error bar: "<value> ± <bar>"      # from the engine
  evidence: "<gamma-inf / class, source + version>"
  lab test: "<which measurement would decide it>"   # e.g. turbidity /
                                                    # cloud point / DSC
  excluded: "no synthesis route, no dosage, no
             health or cosmetic claim"
```

Order again: **plan → OSF registration → only then any benchmark run.**
