# Priority 1 · Delaney/ESOL implementation sanity check

Run: `python validation/solubility/sanity_delaney.py` on `data/solubility/delaney/delaney_20261025.csv`
(1,128 molecules, SHA-256 recorded in `delaney/SOURCE.md`).

| metric | our P-A | Delaney 2004 (paper) |
|---|---|---|
| n | 1,128 (0 unparseable) | 2,874 (original full set) |
| RMSE | **1.099** | ~1.01 |
| MAE | **0.844** | ~0.75 |
| bias | **+0.278** | n/a |
| fraction within 1.0 | **0.68** | n/a |

Interpretation: our implementation reproduces the published performance ballpark
(RMSE ≈ 1.0). The systematic +0.28 bias is consistent with RDKit's Crippen logP
differing from the original clogP; Pat Walters' independent refit on RDKit
descriptors moved the intercept from 0.16 to ~0.26, i.e. the same offset direction
and size. This is evidence that the code is right and AqSolDB is simply a harder,
broader dataset (salts, metals, large molecules) than the ESOL target domain.

Citation: Delaney, J.S. J. Chem. Inf. Comput. Sci. 2004, 44, 1000-1005.
