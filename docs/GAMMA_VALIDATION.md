# Gamma validation: UNIFAC and COSMO-SAC against measured gamma-infinity

Date: 2026-10-26. Offline. No LLM, no benchmark run, no solubility label used.

## 1. Reference data

| Field | Value |
|---|---|
| Source | Straver & de Loos (2005), *J. Chem. Eng. Data* **50**, 1171-1176 |
| DOI | 10.1021/je0495942 |
| Values taken from | NIST/TRC ThermoML record, https://trc.nist.gov/ThermoML/10.1021/je0495942.html |
| Conditions | 298 K, water as solvent, infinite dilution |
| Replicates | the paper reports 1-8 points per solute; averaged in `tools/gamma_validation.py`, spread kept in the table |
| Uncertainty | the paper's combined uncertainty, 1-5 % relative |

The values are measured activity coefficients at infinite dilution
(gamma-infinity), not solubility, not a prediction.

## 2. What was compared

| Column | Engine | Settings |
|---|---|---|
| `unifac_original` | UNIFAC, original (Fredenslund 1975) | ugropy UNIFAC groups, thermo 0.6.1 `UFSG` + `UFIP`, version 0 |
| `unifac_dortmund` | Dortmund UNIFAC (Gmehling; temperature dependent) | ugropy Dortmund groups, thermo 0.6.1 `DOUFSG` + `DOUFIP2016`, version 1 |
| `cosmo_sac` | cCOSMO-SAC (NIST `cCOSMO`, COSMOSAC-2010) | PubChemQC sigma profiles + the refit constants already stored with the sigma data |

Commands:

```
.venv_inventory\Scripts\python.exe tools\gamma_validation.py
.venv_inventory\Scripts\python.exe tools\gamma_validation.py --cosmo
.venv_inventory\Scripts\python.exe tools\cosmosac_sanity.py
```

## 3. Result (298 K, in water)

| Solute | Measured | sd | n | UNIFAC original | err | Dortmund UNIFAC | err | COSMO-SAC | err |
|---|---|---|---|---|---|---|---|---|---|
| ethanol | 3.77 | - | 1 | 7.624 | +102 % | 4.792 | +27 % | 7.895 | +109 % |
| 1-propanol | 13.34 | 0.05 | 5 | 20.067 | +50 % | 13.941 | +5 % | 21.20 | +59 % |
| acetone | 7.68 | 0.04 | 7 | 11.472 | +49 % | 8.043 | +5 % | 9.046 | +18 % |
| 2-butanone | 25.95 | 0.21 | 2 | 55.322 | +113 % | 33.831 | +30 % | 37.26 | +44 % |
| 2-pentanone | 138.50 | 13.44 | 2 | 164.629 | +19 % | 105.453 | -24 % | 93.40 | -33 % |
| 2-hexanone | 292.00 | 38.18 | 2 | 489.774 | +68 % | 334.861 | +15 % | 280.73 | -4 % |
| diacetyl | 13.22 | 0.08 | 6 | 5.230 | -60 % | 7.125 | -46 % | 14.41 | +9 % |
| dimethyl sulfide | 176.12 | 5.72 | 8 | REFUSED | n/a | 141.572 | -20 % | 112.67 | -36 % |
| acetaldehyde | 4.13 | 0.04 | 5 | 6.957 | +69 % | 5.010 | +21 % | 6.314 | +53 % |

| Summary | median abs err | max abs err | within +/-30 % | refused |
|---|---|---|---|---|
| UNIFAC original | 64 % | 113 % | 1 / 8 | 1 |
| **Dortmund UNIFAC** | **21 %** | 46 % | **7 / 9** | 0 |
| COSMO-SAC (PubChemQC) | 36 % | 109 % | 3 / 9 | 0 |

## 4. Findings that changed the code

1. **Original UNIFAC is not usable for aqueous oxygenates.** It overshoots every
   alcohol and ketone in this set by +19 to +113 %. It is kept only for
   comparison; Dortmund is the default (`DEFAULT_VERSION = 1`).
2. **Original UNIFAC has holes in its interaction matrix.** The thioether-water
   pair (main groups 48/7) does not exist in `UFIP`. thermo fills a missing pair
   with a zero interaction and returns a plausible, wrong number (13.8 instead
   of 176). `tools/unifac_gamma.py` now raises `MissingInteraction` instead.
3. **Group names differ between ugropy and thermo, and one name is ambiguous.**
   ugropy spells the aldehyde group `HCO`; thermo calls it `CHO`, and the thermo
   table contains two subgroups named `CHO` (aldehyde, main group CHO; and a CH2O
   unit, main group CH2O). Mapping by name alone silently picked the wrong one
   (acetaldehyde gamma-infinity 14.98 instead of 6.96). The name map now breaks
   the tie by main-group name and refuses any other conflict.
4. **Dortmund subgroups have to come from ugropy's Dortmund model.** Dortmund
   separates primary/secondary/tertiary OH (`OH(P)`, `OH(S)`, `OH(T)`); the
   original table has one `OH`. Using original group ids for a Dortmund run
   also mis-mapped id 102 (`CH3S` vs `AMCH3CH2`), which produced gamma-infinity
   0.95 for dimethyl sulfide. Fixed by per-version grouping.
5. **The cOSMO-SAC sanity script could not run as shipped.** It added the cCOSMO
   build directory to `sys.path` only in check 3, so check 1 failed with
   `ModuleNotFoundError` (found 2026-10-26). Fixed; all three checks now pass.
6. **Diacetyl is a real model gap, not a bug.** Two adjacent carbonyls are two
   `CH3CO` groups in UNIFAC and the model has no neighbour correction; both
   versions are ~50 % low. Report diacetyl-like molecules with that caveat.

## 5. Limits (YELLOW)

- Infinite-dilution limit only. Nothing here validates the full composition
  range, an azeotrope, a liquid-liquid split or a wax/solvent mixture.
- Water as solvent only, one temperature (298 K), one data source (one paper).
- COSMO-SAC numbers use PubChemQC sigma profiles and the refit constants in
  `_hub/data/formulation_sigma`; the profiles are a re-parameterisation, so the
  comparison is "our pipeline", not "COSMO-SAC in general".
- A gamma is not a performance claim: no occlusivity, no TEWL, no skin feel, no
  emulsion stability follows from these numbers.

## 6. Reproduce

```
.venv_inventory\Scripts\python.exe tools\gamma_validation.py --cosmo
.venv_inventory\Scripts\python.exe -m pytest tools\tests\test_unifac_gamma.py -q
.venv_inventory\Scripts\python.exe -m pytest mcp\tests\test_tools_server.py -q
.venv_inventory\Scripts\python.exe tools\cosmosac_sanity.py
```
