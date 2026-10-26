# AGENTS.md — how to answer a plain request in this repository

Read this before answering a user question with numbers. It routes a spoken
request to an engine and states what the engine **cannot** answer.

Project memory (session log, rules, current state): `C:\KuroshinHQ\_hub\docs\DEVAM.md`.
That file wins over this one in a conflict. Every claim needs a command output,
a file hash or a test result; an untested statement is marked `DOGRULANMADI`.

## 1. Two environments, do not mix them

| Environment | Purpose | Rule |
|---|---|---|
| `.venv` | the confirmatory LLM experiment (bench/, mcp/server.py) | **frozen**; do not install into it before the run |
| `.venv_inventory` | physics engines: pycalphad, chemicals, thermo, HSPiT | free to use, git-ignored |

`mcp/server.py` (RDKit + ESOL) runs on `.venv`.
`mcp/tools_server.py` (CALPHAD + Hansen) runs on `.venv_inventory`.

## 2. Engines: what they answer, what they refuse

| Engine | Answers | Refuses |
|---|---|---|
| RDKit (`mcp/rdkit_tool.py`) | formula, MW, heavy atoms, rings, HBD/HBA, canonical SMILES | any property that needs data or a model (solubility, viscosity, melting point, toxicity) |
| ESOL (`mcp/esol.py`) | aqueous logS for neutral single-component molecules, MW <= 500 | salts, metals, mixtures, polymers, out-of-domain (error bar ~5 log units) |
| cOSMO-SAC (`mcp/cosmosac_pubchemqc.py`) | sigma profile -> activity coefficient, mixture ranking | performance claims; it is a model, not a measurement |
| pycalphad + MatCalc TDB (`mcp/tools_server.py`) | phase stability, melting/solidus of an alloy from a TDB | creep, oxidation, corrosion, "stronger/durable" |
| `chemicals` HSP (`mcp/tools_server.py`) | Hansen dD/dP/dH, Ra distance, compatibility **ranking** | occlusivity, TEWL, skin feel, stability, any performance claim |
| `thermo` | UNIFAC activity coefficients, mixture equilibria | anything outside group-contribution validity |
| HSPiT | HSP fitting, phase stability in Hansen space | measured values; unvalidated package, use for ordering only |

No engine here measures anything. Every output is a **prediction with an error
bar**, and every report must say so.

## 3. Routing table (request -> measurable stand-in -> engine)

| Spoken request | Measurable stand-in | Engine | Verdict |
|---|---|---|---|
| "which solvent dissolves X" | logS at 25 C | ESOL | GREEN in domain, YELLOW otherwise |
| "make petrolatum compatible with a moisturiser" | Hansen distance / activity coefficient | chemicals HSP, cOSMO-SAC | YELLOW: ranking only |
| "emulsion will be stable?" | binodal/spinodal in HSP space | HSPiT | YELLOW ranking, RED for droplet size |
| "alloy that survives higher temperature" | melting/solidus temperature | pycalphad + TDB | GREEN with a licensed TDB; RED for creep/oxidation |
| "which oxide forms on this steel" | oxide formation energy | pymatgen / mp_api (needs key) | YELLOW |
| "coating that sticks" | modulus/CTE mismatch shortlist | pymatgen | RED for adhesion |
| "protein binder" | binding free energy | none | RED, no engine |

A RED row means: say "no engine for this" and stop. Do not approximate a RED
request with a YELLOW engine and do not invent a number.

## 4. Data and licences

- CALPHAD databases live **outside** the repository: `KJ_TDB_DIR`
  (default `C:\KuroshinHQ\_hub\data\alloy_tdb_mgf`). MatCalc open databases are
  ODbL 1.0 + DbCL 1.0 (share-alike); the pycalphad-readable copies come from the
  Materials Genome Foundation 2023 workshop repository. Never commit them here.
- Files with no licence text stay `UNCLEAR` and are not used (this is why
  OpenCalphad and the vendor solder TDBs are excluded).
- AqSolDB (`data/solubility/raw/aqsoldb_20261025.tab`) is CC0 and stays.
- Only official APIs and recorded SHA-256 files enter a data manifest. No scraping.

## 5. Validation gates already passed

| Gate | Result | Command |
|---|---|---|
| MatCalc Al TDB loads | 183 phases | `Database(mc_al_v2.032.pycalphad.tdb)` |
| pure Al melting | 933.47 K (lit. 933.47) | `alloy_melting_point(...)` |
| pure Fe melting | 1810.95 K (lit. 1811) | same |
| pure Ni melting | 1728.26 K (lit. 1728) | same |
| Hansen water/toluene/hexane | 15.5/16.0/42.3, 18.0/1.4/2.0, 14.9/0/0 MPa^0.5 | `hsp_lookup` |

A new database or a new element must pass the same known-value gate before its
numbers are reported.

## 6. Answer format

1. One line: which engine, which input, which conditions.
2. The number with its unit and its error bar or bracket width.
3. What the number does **not** say (the RED row).
4. The command that reproduces it.

Pilot figures and debug runs are never reported as results. `/kj` applies this
file; the OSF registrations (`8pbnu`, `uce8d`) override it for anything they
cover.
