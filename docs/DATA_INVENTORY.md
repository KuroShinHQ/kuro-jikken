# Data inventory

Source of truth: `data/manifest.json` (built by `tools/build_manifest.py`, hashes
computed from the files). A dataset that is not in the manifest must not be read
by any engine; a number may not be produced from an unlisted file.

| id | licence | where | domain | not for |
|---|---|---|---|---|
| `aqsoldb_20261025` | CC0-1.0 | repo, 3.84 MB | 9,982 aqueous logS values, 298 K | non-aqueous, salts/metals, mixtures |
| `pubchemqc_sigma_profiles` | external-research | outside repo, 122.2 MB | 361,583 sigma profiles | molecules missing from index, charged species |
| `pubchemqc_sigma_index` | external-research | outside repo, 19.4 MB | InChIKey -> CID | named lookup outside PubChemQC |
| `sigma_refit_params` | MIT | outside repo | COSMO-SAC refit constants | other sigma tables |
| `matcalc_mc_al` | ODbL-1.0 | outside repo, 289 KB | Al CALPHAD Gibbs energy | creep, oxidation, corrosion |
| `matcalc_mc_fe` | ODbL-1.0 | outside repo, 378 KB | Fe CALPHAD | same |
| `matcalc_mc_ni` | ODbL-1.0 | outside repo, 389 KB | Ni CALPHAD | same |
| `hsp_chemicals` | MIT | inside `chemicals 1.5.2` | Hansen dD/dP/dH by CASRN | mixtures, polymers |
| `gamma_inf_literature` | citation-only | `tools/gamma_validation.py` | 9 measured gamma-infinity values, 298 K | redistribution, other solvents |

Rules:

1. External data stays outside the MIT repository (share-alike and research
   licences); only the manifest row and the hash live here.
2. A missing file is an error, not a silent fallback: `tools/tests/test_data_manifest.py`
   checks every in-repo hash and every external size that exists on this machine.
3. "not for" is part of the data, not a footnote: it drives the gate refusals in
   `docs/ENGINE_ROUTER_PLAN.md`.
