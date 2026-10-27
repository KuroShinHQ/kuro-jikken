# V1 - binary VLE and the azeotrope

**Question.** For two named components at a fixed pressure: is there an azeotrope, and at
what temperature and composition?

**Method.** Modified Raoult's law,

```
y_i * P = x_i * gamma_i(T, x) * Psat_i(T)
```

* `gamma` from Dortmund UNIFAC (`tools/unifac_gamma.py`, DOUFIP2016 through `thermo` 0.6.1),
  composition and temperature dependent;
* `Psat` from `thermo`'s pure-component correlation;
* bubble temperature by bisection, azeotrope by scanning `x1` and bisecting where
  `y1 - x1` changes sign.

**Validation at 1 atm.**

| pair | literature T (K) | literature x1 | model T (K) | model x1 | dT |
|---|---|---|---|---|---|
| ethanol / water | 351.32 | 0.894 | 351.40 | 0.894 | **+0.08 K** |
| propan-2-ol / water | 353.52 | 0.681 | 353.52 | 0.680 | **0.00 K** |
| methanol / water | no azeotrope | - | none | - | negative control |

**Source status (honest).** The two literature rows are the commonly tabulated azeotrope
values (CRC Handbook / Dortmund Data Bank). The page-level citation still has to be pinned
before this table is used in a publication; until then the calibration ledger records the
property as `UNCALIBRATED`, so `screen()` may not rank on it.

**What the answer does not say.** Ternary azeotropes, pressure dependence, vapour-phase
non-ideality, distillation design, energy use, or whether a real mixture behaves this way
at another pressure.

**Reproduce.**

```powershell
.venv_inventory\Scripts\python.exe mcp\vle.py ethanol water
.venv_inventory\Scripts\python.exe -m pytest mcp/tests/test_vle.py -q
.venv_inventory\Scripts\python.exe tools\calibration_check.py --strict
```

**Refusal boundary.** One component, three components, an unknown component, a pair whose
UNIFAC groups or main-group interactions are missing, or a mixture with no bubble point in
250-500 K all refuse; they never return a number. A pair outside the table above is a model
prediction and the gate says `YELLOW`.
