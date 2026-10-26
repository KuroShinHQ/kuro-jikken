# Engine inventory (2026-10-26)

Design + smoke tests only. No benchmark, no accuracy numbers, no data downloads.

Method: licence from the `LICENSE` file in the official repository (first line
quoted); version and release date from PyPI JSON; last commit from the official
repository API; every smoke test ran offline in `.venv_inventory` with data
shipped inside the package or built in code.

Tags: **VERIFIED** = source quoted, **ASSUMPTION** = inference, **UNCLEAR** =
could not establish - do not use.

## 1. RDKit (already in the repo)

| item | value |
|---|---|
| Licence, first line | `BSD 3-Clause License` (VERIFIED, raw.githubusercontent.com/rdkit/rdkit/master/license.txt) |
| Version / release | **2026.9.1**, 2026-10-09 (VERIFIED, pypi.org/pypi/rdkit/json) |
| Last commit | 2026-10-26 (VERIFIED, api.github.com/repos/rdkit/rdkit/commits) |

**Can answer:** algorithmic graph facts - formula (Hill), molecular weight,
heavy atoms, ring count (SSSR), H-bond donors/acceptors, rotatable bonds,
canonical SMILES, InChIKey, substructure matches.
**Cannot answer:** anything needing data or a thermodynamic model - solubility,
melting point, viscosity, toxicity, stability, "is this a good moisturizer".
**Data needed:** none; input is a SMILES/InChI.
**Validation:** no peer-reviewed validation paper for RDKit itself found
(VERIFIED absence: rdkit.org has no citation page). Descriptor definitions
follow published algorithms and are unit-tested in the repository.
**Smoke test:** PASS - `.\.venv\Scripts\python.exe -c "from rdkit import Chem;
from rdkit.Chem import Descriptors, rdMolDescriptors, Lipinski;
m=Chem.MolFromSmiles('CCO'); print(rdMolDescriptors.CalcMolFormula(m),
Descriptors.MolWt(m), m.GetNumHeavyAtoms())"` -> `C2H6O 46.07 3`
(rings 0, HBD 1, HBA 1, rotatable 0), 2026-10-26.

## 2. pycalphad

| item | value |
|---|---|
| Licence, first line | `pycalphad, a Python library for the CALculation of PHAse Diagrams` then `The MIT License (MIT)` (VERIFIED, raw.githubusercontent.com/pycalphad/pycalphad/develop/LICENSE.txt) |
| Version / release | **0.11.2**, 2026-06-05 (VERIFIED, pypi.org/pypi/pycalphad/json) |
| Last commit | 2026-10-24 (VERIFIED, api.github.com/repos/pycalphad/pycalphad/commits) |

**Can answer:** with a TDB database - which phases are stable at given T, P and
composition; phase boundaries; melting/solidus ranges; Gibbs energy of a phase;
driving force for precipitation; Scheil solidification.
**Cannot answer:** anything the database does not model. No TDB = no answer. It
does not create thermodynamic data, does not predict kinetics, creep,
oxidation or corrosion rates, and says nothing about database quality.
**Data needed:** a TDB file. Bulk data licence is the real blocker:
- MatCalc open databases `mc_fe`, `mc_ni`, `mc_al`: **ODbL 1.0 + DbCL 1.0**
  (VERIFIED, matcalc.at/index.php/databases/open-databases). ODbL is
  share-alike, so a derived database must stay ODbL.
- OpenCalphad lists COST507 and a NIST solder TDB as "available for free" with
  no licence text (VERIFIED, opencalphad.com/databases.php) -> **UNCLEAR, do not
  use**.
- NIMS database: registration required (VERIFIED, TDBDB credits page) -> not an
  open licence -> **UNCLEAR, do not use**.
- TDBDB indexes databases and links to the source, it does not host them
  (VERIFIED, avdwgroup.engin.brown.edu/help.html) -> per-source rights ->
  **UNCLEAR unless the source states a licence**.
- 38 TDBs ship inside the pycalphad package (VERIFIED, `pycalphad/tests/
  databases`). The package is MIT, but the file headers carry no licence
  statement (e.g. `Al-Mg_Zhong.tdb` header = assessment reference only) ->
  **UNCLEAR for the data**.

**Validation:** Otis, R. & Liu, Z-K. (2017), *pycalphad: CALPHAD-based
Computational Thermodynamics in Python*, Journal of Open Research Software 5:1,
DOI **10.5334/jors.140** (VERIFIED, api.crossref.org/works/10.5334/jors.140).
The paper reports regression tests against known systems and ~80% code
coverage - software validation, not an independent physics benchmark.
**Smoke test:** PASS - offline equilibrium on the shipped `Al-Mg_Zhong.tdb`:
`equilibrium(db, ['AL','MG','VA'], ['FCC_A1','LIQUID','HCP_A3'],
{X(MG):0.3, T:600, P:101325})` -> single phase `FCC_A1`, GM =
-22594.0507 J/mol (2026-10-26).

## 3. pymatgen

| item | value |
|---|---|
| Licence, first line | `The MIT License (MIT)` (VERIFIED, raw.githubusercontent.com/materialsproject/pymatgen/master/LICENSE) |
| Version / release | **2026.10.24**, 2026-10-23 (VERIFIED, pypi.org/pypi/pymatgen/json) |
| Last commit | 2026-10-24 (VERIFIED, api.github.com/repos/materialsproject/pymatgen/commits) |

**Can answer:** structure handling and analysis - build/convert structures (CIF,
POSCAR, JSON), symmetry and space groups, density, composition, coordination,
diffraction patterns, band-structure and DOS post-processing, phase-diagram
construction from formation energies, interface/surface slabs.
**Cannot answer:** anything without input data. It is an analysis library, not a
database: no formation energies, no elastic tensors, no band gaps by itself.
It does not predict device performance, durability or biological effects.
**Data needed:** structure files or computed results supplied by the user. Data
licence is therefore the user's; for Materials Project values it is CC BY 4.0
(see section 4).
**Validation:** Ong et al. (2013), *Python Materials Genomics (pymatgen): A
robust, open-source python library for materials analysis*, Computational
Materials Science 68:314-319, DOI **10.1016/j.commatsci.2012.10.028** (VERIFIED,
api.crossref.org). Independent physics validation is not claimed; correctness
rests on its unit tests and published use.
**Smoke test:** PASS - structure built in code, no data file:
`Structure(Lattice.cubic(5.43), ['Si','Si'], [[0,0,0],[0.25,0.25,0.25]])` ->
formula `Si`, volume 160.103 A^3, density 0.5826, space group `R-3m`, CIF header
`# generated using pymatgen` (2026-10-26).

## 4. mp_api (official Materials Project client + MCP server)

| item | value |
|---|---|
| Licence, first line | `Copyright (c) 2017, The Regents of the University of` / `California, through Lawrence Berkeley National Laboratory ...` then a 3-clause BSD text = **BSD-3-Clause-LBNL** (VERIFIED, raw.githubusercontent.com/materialsproject/api/main/LICENSE; PyPI classifier `BSD-3-Clause-LBNL`) |
| Version / release | **0.47.0**, 2026-10-19 (VERIFIED, pypi.org/pypi/mp-api/json) |
| Last commit | 2026-10-22 (VERIFIED, api.github.com/repos/materialsproject/api/commits) |
| MCP server | official, shipped inside the client since **0.46.0**; tools `search` and `fetch` (VERIFIED, docs.materialsproject.org/services/ml-and-ai-applications/mcp) |

**Can answer:** retrieval of computed materials data from the Materials Project -
structure, formula, band gap, formation energy, elastic tensor, phase diagram
entries; the MCP `search`/`fetch` pair does bulk retrieval and single-material
detail.
**Cannot answer:** nothing physical by itself. It retrieves computed values; it
does not validate them, does not measure anything, and cannot answer about
materials outside the database or about unrelaxed/hypothetical phases.
**Data needed:** an MP API key and network. Data licence: **CC BY 4.0** with
terms - no scraping, API key must not be shared, contact MP before repackaging
(VERIFIED, legacy.materialsproject.org/terms). Exception: the **GNoME** subset
is **CC BY-NC 4.0**, non-commercial only (VERIFIED, docs.materialsproject.org/
materials-project-data-lakehouse/access-controlled-data).
**Validation:** none found for the client itself. The database behind it is
described in the Materials Project papers; that is provenance, not an accuracy
benchmark of the API client.
**Smoke test:** PASS (import only, no key, no network) - after
`pip install "mp-api[mcp]"`: `import mp_api.mcp.server` -> module loaded from
`...\site-packages\mp_api\mcp\server.py`; client import prints
`MPRestWarning: No API key found` and makes no request (2026-10-26).

## 5. OPTIMADE client (+ MCP status)

| item | value |
|---|---|
| Licence, first line | `Copyright (C) 2019 OPTIMADE Development Team` then MIT text = **MIT** (VERIFIED, raw.githubusercontent.com/Materials-Consortia/optimade-python-tools/main/LICENSE) |
| Version / release | **1.5.0**, 2026-06-21 (VERIFIED, pypi.org/pypi/optimade/json) |
| Last commit | 2026-10-25 (VERIFIED, api.github.com/repos/Materials-Consortia/optimade-python-tools/commits) |
| MCP status | **no official OPTIMADE MCP found**. Official project ships a client (`optimade-get`) and a validator (VERIFIED, optimade.org docs). The MCP server on PyPI (`optimade-mcp-server` 0.1.0) is a **community** package -> **YELLOW at best, not in the trusted manifest** |

**Can answer:** one query across many OPTIMADE providers - "which structures
contain Li and Fe", "give me entries by chemical formula", "filter by space
group"; returns standardized JSON validated against the OPTIMADE schema.
**Cannot answer:** it is a postal service, not an engine. No properties of its
own, no energies, no predictions; and results are only as good, and as
licensed, as each provider.
**Data needed:** network + provider URLs. **Each provider's data licence must be
recorded separately** - the API spec licence says nothing about the data. For
Materials Project via OPTIMADE, the CC BY 4.0 terms of section 4 apply.
**Validation:** Andersen et al. (2021), *OPTIMADE, an API for exchanging
materials data*, Scientific Data 8:217, DOI **10.1038/s41597-021-00974-z**
(VERIFIED, api.crossref.org). Further implementation report: *Developments and
applications of the OPTIMADE API*, Digital Discovery, DOI
**10.1039/d4dd00039k** (2024, VERIFIED).
**Smoke test:** PASS (offline, no network) - a minimal structure record parsed
by the official model: `StructureResource(**record)` with 3 sites ->
`PASS parsed smoke-1 O2Si 3`. The validator also raised a spec warning that
`species` is required when `species_at_sites` is given (2026-10-26). That
warning is useful: the schema catches sloppy records.

## 6. HSPiT

| item | value |
|---|---|
| Licence, first line | `MIT License` (VERIFIED, raw.githubusercontent.com/Emil-Kongsbach/HSPiT/main/LICENSE) |
| Version / release | **0.1.2**, 2026-07-30 (VERIFIED, pypi.org/pypi/HSPiT/json); only two releases exist (0.1.1, 0.1.2) |
| Last commit | 2026-07-30 (VERIFIED, api.github.com/repos/Emil-Kongsbach/HSPiT/commits) |

**Can answer:** Hansen-space questions given HSP triplets and molar volumes -
Hansen distance, activity coefficients from an HSP model, local/global
(sPinodal/binodal) stability of a mixture, and an optimizer that proposes
additive HSP parameters that would stabilise a mixture; `stefanis_gc` estimates
HSP from SMILES (Stefanis-Panayiotou group contribution); `hsp_fit` fits HSP
using UNIFAC-Dortmund.
**Cannot answer:** it cannot measure. It does not know the true HSP of your
material unless you supply or fit them; it says nothing about occlusivity,
TEWL, skin feel, emulsion droplet size, pH, preservative efficacy or any
performance claim.
**Data needed:** HSP triplets (MPa^0.5) and molar volumes per component, or a
fit set. The library embeds Stefanis-Panayiotou group values in code
(VERIFIED: README states the group data is embedded) and uses `ugropy`
(MIT, 3.2.5, 2026-09-30) for UNIFAC groups. There is **no bundled curated HSP
database** in the package.
**Validation:** **none found**. The repository README and the PyPI description
contain no validation study and no citation section (VERIFIED absence, checked
2026-10-26). The methods it implements come from published group-contribution
work, but the implementation itself is unvalidated -> treat as **YELLOW**, and
never as a source of measured values.
**Smoke test:** PASS - offline, values from the README style call:
`stefanis_gc('CCO')` -> dD 15.98, dP 6.55, dH 13.98; a two-component mixture of
identical HSPs gives gamma = 1.0 and `is_stable_local() == True` (2026-10-26).

## 7. Translation table: user request -> measurable property -> engine

Design proposal, not a measurement. "Support" is about the *stand-in*, not the wish.

| # | Request (as spoken) | Measurable stand-in | Engine | Support |
|---|---|---|---|---|
| 1 | metal more heat resistant | melting/solidus T, stable phase at T | pycalphad + **licensed** TDB | **YELLOW**: green only inside a TDB whose licence is recorded. Creep/oxidation = RED |
| 2 | metal more corrosion resistant | oxide formation energy, aqueous potential | pymatgen/mp_api (oxides); no aqueous engine | **RED** for corrosion. YELLOW only for "which oxide is favoured" |
| 3 | coating for a metal | elastic/CTE mismatch, surface energy, adhesion work | pymatgen + mp_api (elastic tensors); no adhesion model | **RED** for "will it stick". YELLOW for modulus/structure shortlist |
| 4 | petrolatum must not suppress a richer moisturizer | Hansen distance, activity coefficient, mixture stability | HSPiT (unvalidated) + COSMO-SAC profiles already in this repo | **YELLOW**: ranking only. Occlusivity/TEWL/skin feel = RED |
| 5 | emulsion stability | binodal/spinodal separation in HSP space, HLB | HSPiT phase stability; no interfacial-tension engine | **YELLOW** for ranking; **RED** for droplet size and interfacial tension |
| 6 | protein binder for a benchmark target | binding free energy, pose, structure | **none in inventory** | **RED**: no docking/structure-prediction engine licensed and recorded here |

Notes: rows 1-3 rest on **ASSUMPTION** that the user's wish maps to the listed
stand-in; that mapping must be confirmed by the captain per target, in writing,
before any number is reported. Rows 4-6 are the honest boundary: the engine can
rank, it cannot promise performance.

## 8. Rules that follow from this inventory

1. Scraping is out. Only official APIs, official MCP servers and data files with
   a recorded licence **and** SHA-256 enter the future data manifest.
2. No licence text = no use. TDBs whose header is silent stay `UNCLEAR`.
3. MP data is CC BY 4.0 (attribution, no scraping, no key sharing); the GNoME
   subset is CC BY-NC 4.0 and must be excluded from any commercial path.
4. pycalphad can only be sold as a capability where a licensed TDB exists; today
   that means the MatCalc open databases (ODbL 1.0, share-alike).
5. HSPiT is unvalidated: usable for ordering hypotheses, never for a claim.

## 9. Verdict for kuro-jikken

| Engine | Verdict | Reason |
|---|---|---|
| RDKit | **GREEN** | BSD-3, no data needed, deterministic, already the repo's motor |
| pymatgen | **GREEN** (analysis only) | MIT, but it computes nothing without input data |
| mp_api (+ official MCP) | **YELLOW** | licence is usable (CC BY 4.0), but needs a key, network, and excludes GNoME for commercial use |
| pycalphad | **YELLOW** | MIT engine, **data licensing is the blocker**; only MatCalc open TDBs are clearly usable |
| OPTIMADE client | **YELLOW** | official client MIT; no official MCP; each provider's data licence must be recorded |
| HSPiT | **YELLOW** | MIT but v0.1.x, no validation, no bundled HSP data |

## 10. Additions 2026-10-26 (engines wired, sources checked live)

- **MatCalc TDBs usable in pycalphad**: the vendor files do not parse; the
  pre-modified copies from the Materials Genome Foundation 2023 workshop
  repository do (`mc_al_v2.032`, `mc_fe_v2.059`, `mc_ni_v2.034`). Kept outside
  this repository (ODbL 1.0 + DbCL 1.0). Validation: `docs/ALLOY_VALIDATION.md`.
- **Installed for engines** (`.venv_inventory`, all MIT): `chemicals 1.5.2`,
  `thermo 0.6.1`, `HSPiPy 1.1.8`; `ugropy 3.2.5` already present.
- **Excluded**: OpenCalphad (GitHub API reports no licence file); NIST phase
  pages are a pointer only, no open data download.
- **Candidates, not installed**: `openCOSMO-RS_py` (LGPL-3.0, needs ORCA COSMO
  files), NeqSim (Apache-2.0, Java runtime, wax/WAT models).
- **Known gap**: petrolatum, mineral oil and white wax have no Hansen entries
  (they are mixtures). `hsp_rank` therefore ranks small molecules only.
- **UNIFAC**: `unifac_groups` returns subgroups and r/q (ugropy); the group
  interaction matrix that turns them into activity coefficients is not wired.

## 11. Environment record

- venv: `.venv_inventory` (isolated, created 2026-10-26).
- installed: `pycalphad 0.11.2`, `pymatgen 2026.10.24`, `mp-api 0.47.0`
  (+`[mcp]` extra), `optimade 1.5.0`, `HSPiT 0.1.2`, `ugropy 3.2.5`,
  `numpy 2.5.4`, `scipy 1.18.1`; `rdkit 2026.9.1` from the repo venv.
- no LLM, no server, no benchmark, no accuracy number was produced in this task.


