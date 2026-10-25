# COSMO-SAC engine pin (for prereg Freeze-2)

Engine used by `mcp/cosmosac_pubchemqc.py`. The engine is not vendored in this
repo and is not modified; it is built from the pinned commit and imported.

| Item | Value |
|---|---|
| Source | https://github.com/usnistgov/COSMOSAC |
| Commit | `1b82456be38026719b16cad4076109bef3fcb309` (2026-07-03) |
| Submodule Eigen | `cf794d3b741a6278df169e58461f8529f43bce5d` |
| Submodule pybind11 | `3cc7e4258c15a6a19ba5e0b62a220b1a6196d4eb` |
| Built wheel | `ccosmo-1.0.3-cp312-cp312-win_amd64.whl`, sha256 `1bbf8fe5ae8be1e5b54c536190b9660b7a07b4fd6515f21402ef021e28e90fbb` |
| Python | 3.12.9 (repo `.venv`) |
| Method | `COSMOSAC-2010` = `cCOSMO.COSMO3`, `ln(gamma) = get_lngamma_comb + get_lngamma_resid` |

Build (Windows, VS 2022 Build Tools + CMake):

```
git clone https://github.com/usnistgov/COSMOSAC.git
cd COSMOSAC
git checkout 1b82456be38026719b16cad4076109bef3fcb309
git submodule update --init --depth 1 externals/Eigen externals/pybind11
.venv\Scripts\python.exe -m pip install . --no-deps
```

Engine license: MIT (NIST). The `profiles/UD` and `profiles/VT2005` `.cosmo`
files are BioVia-restricted (academic, non-commercial); they are used only in
the local equivalence check in `tools/cosmosac_sanity.py` and are not
redistributed. Our study uses the PubChemQC parquet profiles, not UD/VT.

Location on this machine: `C:\KuroshinHQ\_hub\data\formulation_sigma\engine\COSMOSAC`
(outside the repo, like the parquet data).
