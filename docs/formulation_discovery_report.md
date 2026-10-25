# formulation-screening · discovery report (2026-10-25)

Preparation jobs only. **No engine was run, no error/F1/accuracy was computed,
no engine output was compared with any label.** Plan file untouched.

## JOB 1 — PubChemQC sigma files: hashes

Downloaded to `C:\KuroshinHQ\_hub\data\formulation_sigma\` (NOT committed).

| file | bytes | our SHA-256 | reference | verdict |
|---|---|---|---|---|
| `sigma_profiles_main.parquet` | 122,228,196 | `8e1c4d21acee25b04ad5e63b0c846f98524b0b5d1554d1426b9616de5a62da2c` | MANIFEST.txt sha256 (identical) | **OK** |
| `sigma_profile_index.parquet` | 19,440,344 | `810e18592807da962a718753abfafaa32bf423ac6afa87dbbd9707267cea73f0` | Zenodo md5 `d57d3ad2…` = our md5 | **OK** |
| `sequential_final_params.json` | 1,186 | `b210b1687dec8ebe93aa60b6946ed2b3b6d57dbf542fb1d6ce2ae0edaa13a536` | Zenodo md5 `784b7086…` = our md5 | **OK** |

`sigma_profiles_main_raw.tar.gz` (267 MB) not downloaded: only needed to
regenerate the parquet. Publisher publishes md5 only; MANIFEST publishes
sha256 for the two big artifacts and nothing for index/params — the hashes
above are ours.

## JOB 2 — which COSMO-SAC parameter set belongs to these profiles

**CONFIRMED**, from the parameter file itself (`sequential_final_params.json`):

- `"method": "Hsieh-2010 sequential refit (NLLS soft_l1 on γ∞)"`
- `"cosmosac_version": "COSMO3 (Hsieh 2010, 3-profile)"`
- `"sigma_source": "PySCF BP86/def2-SVP + COSMO ε=∞ + Klamt cavity (vdw_scale=1.0)"`

Recalibrated constants: `A_ES=5798.8547`, `B_ES=3.6114548e8`,
`c_OH_OH=2449.8772`, `c_OH_OT=1834.9399`, `c_OT_OT=1347.9013` (Hsieh
defaults are listed in the same file for comparison). Fitted on **24,522**
γ∞ records (no_hb 3,261 / hb_oh 18,118 / hb_ot 3,143, `split_seed: 42`).
So: profiles = COSMO3 3-profile with **recalibrated** constants, not Hsieh
defaults. README does not state this; the parameter file does.

## JOB 3 — labelled data search (the decisive one)

| source | what it holds | access / size | licence / terms | verdict |
|---|---|---|---|---|
| **NIST ThermoML Archive** (trc.nist.gov/ThermoML) | experimental thermophysical data: LLE, VLE, γ∞, mutual solubility; IUPAC ThermoML XML per article | public, per-article files | public + **citation requested**; **no formal open-licence text found** | **UNRESOLVED** — usable only after terms are read and accepted |
| **MixtureSolDB** (github.com/levakrasnovs/MixtureSolDB) | 175,166 solubility values, 810 compounds, binary solvents, 252–383 K | `MixtureSolDB.csv` 41,107,737 B | paper CC-BY-4.0; **repo has no LICENSE file** | **UNCLEAR → not used** |
| **usnistgov/COSMOSAC** | sigma profiles (UD, VT2005, ORCA/G09/GAMESS/DMol3) + generators | MIT | MIT | **no experimental labels** |
| **Fingerhut 2017** (IECR 56:9868; doi 10.1021/acs.iecr.7b01360) | the "29,173 γ∞ + 139,921 VLE" source | paywalled article; SI not verified | unknown | **UNCLEAR → not used** |
| **DDBST LLE** | large LLE data bank | commercial | paid | **excluded** |

Heterogeneity: ThermoML = many independent papers; MixtureSolDB = one
curated compilation; DDB = curated, commercial.

## JOB 4 — novelty count

**Not possible yet, and here is why:** no labelled source is cleared for use
(all four are UNRESOLVED/UNCLEAR/excluded), so there is no pair list to
compare against and nothing was downloaded to intersect with the sigma-DB
index (361,583 CIDs). **Count performed: 0.**

Rule proposed for later (to be frozen before the plan is rewritten):
a candidate pair is "novel" only if **any** of these holds —
(a) no measurement for that pair is found in the chosen open source,
(b) the engines disagree on the class (or on sign of ln γ∞),
(c) the engine's own reported confidence is low (down-weighted).
Everything else is "already known" and must not be sold as a new test.

## What this report changes

- JOB 1: hashes of all three files we use are now recorded — **OK**.
- JOB 2: parameter set is **CONFIRMED** (COSMO3 / Hsieh-2010 refit).
- JOB 3: **no labelled dataset is cleared yet** → the plan's primary task
  (classification vs γ∞ accuracy) still cannot be fixed.
- JOB 4: novelty counting blocked on JOB 3.

Nothing was run; no error, F1 or accuracy was computed; no engine output was
compared with any label; the plan file was not edited.
