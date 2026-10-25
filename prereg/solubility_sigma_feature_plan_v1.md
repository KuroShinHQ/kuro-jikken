# kuro-jikken - solubility sigma feature - PLAN v1 (DRAFT)

Status: PLAN ONLY. No study engine run, no error/RMSE/feature value used in any
design decision, no comparison with AqSolDB logS. Row counts and file hashes
only; the label-free sanity run is disclosed in section 16.

SCOPE: at most about one third of AqSolDB; exact count fixed in section 15.

Order: this plan, with all hashes written inside it -> adapter written and
label-free sanity tests pass, SHA-256 committed -> ONE OSF registration -> one
evaluation -> report. There is no separate freeze step and no dated note.
Nothing that defines the feature is written after registration. Supersedes
`prereg/formulation_screening_plan_v0.md` (archived, never registered).

## 1. Question

Does adding ONE engine feature (ln gamma-infinity of the solute in water at
298.15 K, NIST COSMOSAC + PubChemQC sigma DB) to a linear ESOL-type regression
reduce aqueous solubility (logS) error versus an equally cheap RDKit feature
(TPSA) on held-out molecules?

Unit under test: engine + sigma DB together. No candidate list.

## 2. Models

| id | model |
|---|---|
| M0 | ESOL published coefficients (no fitting) |
| M1 | ESOL descriptors, OLS on tune |
| M2 | M1 + engine feature, OLS on same tune |
| M3 | M1 + RDKit TPSA, OLS on same tune |

**PRIMARY: M2 vs M3.** M1 and M0 are secondary. One primary engine: NIST
COSMOSAC. Other engines are exploratory only.

TPSA call: `rdkit.Chem.rdMolDescriptors.CalcTPSA(mol)` with defaults
(`force=False, includeSandP=False`; S and P not counted). RDKit 2026.09.1.

## 3. Engine feature (frozen now)

ln gamma-infinity of the solute in **water** at **298.15 K**, composition
`[1e-12, 1-1e-12]`. Code: `usnistgov/COSMOSAC`, commit
`1b82456be38026719b16cad4076109bef3fcb309` (2026-07-03), module
`easy_COSMOSAC`, method `COSMOSAC-2010` (COSMO3).

Stock `calc_LNAC` loads only its UD/VT profile folders; our profiles are the
PubChemQC parquet, so the frozen call is the COSMO3 core with an adapter
`PubChemQCProfiles` (written and committed BEFORE registration, with its SHA-256):

`cosmo = COSMO3(names=[solute,"WATER"], db=PubChemQCProfiles)`
`ln_gamma_inf = cosmo.get_lngamma_comb(298.15, comp) + cosmo.get_lngamma_resid(298.15, comp)`

- params `sequential_final_params.json` sha256 `b210b1687dec8ebe93aa60b6946ed2b3b6d57dbf542fb1d6ce2ae0edaa13a536`
- sigma main `8e1c4d21acee25b04ad5e63b0c846f98524b0b5d1554d1426b9616de5a62da2c`
- index `810e18592807da962a718753abfafaa32bf423ac6afa87dbbd9707267cea73f0`
- water profile: CID 962.

Models are linear, so log base is a scaling only.

## 4. Fitting rule

Ordinary least squares; no regularisation, no feature selection, no outlier
removal, no transforms beyond those written here. Fixed ESOL descriptors:
Crippen `MolLogP`, `Descriptors.MolWt`, `CalcNumRotatableBonds` (strict
default), aromatic proportion = aromatic atoms / heavy atoms. RDKit 2026.09.1.

M0 coefficients are the published ESOL ones, not refit.

## 5. Data and identity

AqSolDB (CC0 1.0, DOI `10.7910/DVN/OVHAW8`), 9,982 molecules. PubChemQC sigma
DB v1.0.0 (Zenodo `10.5281/zenodo.20672192`).

Matching: exact **full 27-character InChIKey**; no CID, first-block, stereo or
protonation normalisation; empty keys excluded. **Recount: 3,416 matched
molecules (34.22% of 9,982).** Counts only; no label values.

One profile per molecule: identity = full InChIKey; prefer rows parsing to
formal charge 0; among those take the lowest CID (tie: lowest file row). **If no
neutral row exists, the molecule is out of domain.** Water uses CID 962. Dropped
duplicates are counted; no profile averaging.

## 6. In-domain rule (input only)

All must hold before any label comparison:

- neutral (formal charge 0), single component (no `.`);
- elements only C,H,N,O,S,F,Cl,Br,I (no P, no metals);
- **no MW limit** (500 is not used and was not borrowed from the earlier ESOL analysis);
- present in the sigma DB after the one-profile rule;
- AqSolDB logS present and numeric.

Engine worked = finite number and no physically impossible value (NaN,
infinite, negative activity coefficient). Anything else = engine failure.
Failure is not an exclusion: M2 falls back to M1 on the locked set; failure
count reported.

## 7. Split, tune and locked sets

Molecule-level split, **50/50**, seed **20261027**. Tune = fitting only; locked
= one-shot confirmation. One script `data/solubility/make_split_v2.py` builds
the locked set from (pool file SHA-256, seed 20261027): rows sorted by InChIKey,
seeded Fisher-Yates with Python `random.Random(20261027)`, first half tune,
second half locked. No other sorting or library choice. The registration only
carries the output hash (section 15).

GATE: count the in-domain pool (counts only). If the locked half is **< 800
molecules, STOP and report**; do not change the rule. If >= 800 but the CI is
too wide to exclude the margin, report **inconclusive**. The locked set size is
whatever 50% gives; it is not inflated. No separate power calculation: the 50%
split plus the 800 gate are the rule.

Locked set `data/solubility/split_locked_v2.csv` was generated before
registration and is committed with `LOCKED_V2.sha256` **before any evaluation**,
opened once. The earlier ESOL locked set was already opened once; molecule
overlap with the new set is computed and declared before the evaluation (counts
only). The same hash is written into the registered plan (section 15).

Engine failures: tune excludes failed molecules from M2/M3 fitting and counts
them; locked falls back to M1. Report **two numbers**: all in-domain molecules,
and engine-worked subset.

## 8. Metrics and decision

PRIMARY: engine-worked subset of the locked set, M2 and M3 scored on the SAME
molecules. SECONDARY: all in-domain molecules (M2 falls back to M1 on engine
failures). Metric: RMSE, M2 vs M3; MAE secondary. Bootstrap: 10,000 resamples,
clustered by molecule, percentile method, fixed seed 20261028, two-sided 95% CI.

Three outcomes (primary set):

- **SUCCESS:** observed M2-M3 RMSE difference <= **-0.10** AND 95% CI entirely
  below 0.
- **NO GAIN:** 95% CI entirely above **-0.10**.
- **INCONCLUSIVE:** everything else.

SUCCESS means only "observed difference passed the margin and is distinguishable
from zero", NOT "the true effect is at least 0.10".

Margin **0.10** comes from literature, not our data: Palmer & Mitchell 2014
doi:10.1021/mp500103r (experimental uncertainty 0.6-0.7 logS); AqSolDB paper
PMC6687799 (SD up to 0.5); Sluga et al. 2020 doi:10.5562/cca3776 (external RMSE
0.8-1.1); Avdeef 2019 doi:10.5599/admet.698.

## 9. Hypotheses

H1 only: the SUCCESS rule in section 8, exactly (no second wording). All else
is EXPLORATORY and must map to a pre-defined measurable category. Failed
hypotheses will be published.

## 10. Author expectations (author-stated, 2026-10-25)

- Expected: "a slight decrease, about 0.05, M2 vs M3".
- Minimum reduction that counts: **0.10** (above).

These are recorded as author words, not agent numbers.

## 11. Deviations

Covers ALL sections: question, models, data, identity, in-domain, split, seed,
locked set, metrics, hypotheses, reporting. Any change is recorded as a dated
deviation before it is applied, with reason and effect.

## 12. Risks

- R1 aqueous solubility is only a stepping stone, not a formulation.
- R2 solids need melting data; AqSolDB lacks it.
- R3 sigma DB is non-peer-reviewed, preprint-level.
- R4 engine and DB are evaluated jointly.
- R5 LGPL engines run as separate processes; not legal advice.
- R6 earlier ESOL locked set was opened once.
- R7 sigma DB parameters were fitted on 24,522 gamma-infinity records in water;
  overlap with AqSolDB molecules is unknown (possible leak).
- R8 M0 uses published ESOL coefficients from an older dataset; some of those
  molecules may be in AqSolDB, so M0 may have seen test molecules (secondary).
- R9 M0 uses Crippen logP; original ESOL used a different logP, so RDKit-based
  M0 is not identical to the published ESOL.
- R10 AqSolDB mixes temperatures and pH conditions; the engine assumes 298.15 K.
- R11 conflicting measurements and label noise for the same compound.

## 13. Scope prohibitions

No candidate list, no synthesis, dosage, health or cosmetic claims. Output is an
error comparison, positive or negative. No use of the word "benign".

## 14. Registration order

1. this plan, with the hashes in section 15 written inside it -> 2. adapter and
label-free sanity tests (SHA-256 committed) -> 3. ONE OSF registration -> 4. one
evaluation -> 5. report with failures and the deviation log.

The locked set was generated before registration and was not inspected: only row
counts and the file hash were used, and the hash is part of the registered plan
text (section 15), so the registration timestamp covers it. There is no separate
freeze step and no dated note; the hash lives in the registered plan text.

## 15. Hashes fixed in this plan

| item | value |
|---|---|
| locked set `data/solubility/split_locked_v2.csv` | `6d624855e2e570e12484e7becb69d7522600ee13a14d6a49b1db6dfa6215be0c` |
| pool `data/solubility/pool_v2.csv` | `1ba6d5b33e9f9dd5d168f452ab204f74ba1b31fd12f94352851b55e849c51a3f` |
| split script `data/solubility/make_split_v2.py` | `b6807e41e98778da8146c29bb0ef1583ca4ef9f8092b8cdfc352a8331e7ec927` |
| adapter `mcp/cosmosac_pubchemqc.py` | `86a1174bfd0445b19ddf2953c187dfa7ca6d9e46c3ce83485fb1ba71183239a3` |
| engine commit `usnistgov/COSMOSAC` | `1b82456be38026719b16cad4076109bef3fcb309` |
| cCOSMO wheel (cp312, win_amd64) | `1bbf8fe5ae8be1e5b54c536190b9660b7a07b4fd6515f21402ef021e28e90fbb` |

Pool counts, in order: **9,982** AqSolDB rows -> **3,416** matched on the full
27-character InChIKey -> **3,132** in domain (dropped: 238 charged, 45 with P,
1 multi-component) -> **1,566** tune / **1,566** locked; the 800 gate passes.
Data-file hashes (sigma parquet, index, parameter file) are in section 3.

## 16. Disclosures before registration

The label-free sanity check ran the engine for water-water and for seven solutes
(ethanol, benzene, toluene, caffeine, aspirin, acetic acid, urea). The three data
files (`pool_v2.csv`, `split_tune_v2.csv`, `split_locked_v2.csv`) carry the
AqSolDB `logS` column unchanged, so a label column is present in them; it was
carried through as row data and never examined. No label value was printed,
summarized, compared or used for any design decision, and every number reported
in this plan is a row count or a file hash. The BioVia-restricted UD profiles
were used only for the local equivalence check; they are not redistributed and
are not part of the study data.
