# FIRST TASKS for the coding agent (opencode)

Context: read `README.md` first. This repo is a reproducible research project.
Rules: numbers come only from tested code. Never invent data. Keep every step reproducible.

## Task 1 · Folder skeleton
Create the folders listed in README section 3. Add a short `README.md` or `.gitkeep` in each.
Add `LICENSE` (MIT, copyright "Yasin Yagci").

## Task 2 · Data schema
Write `data/SCHEMA.md` describing one record:
`id, name, smiles, source, source_id, retrieved_at (ISO date), source_version, property, value, unit, definition_note`.

## Task 3 · RDKit tool (`mcp/`)
Python module with pure functions, no network access, deterministic:
- `parse_smiles(smiles)` returns canonical SMILES or a clear error
- `formula`, `molecular_weight`, `heavy_atom_count`, `ring_count`, `hbond_donors`, `hbond_acceptors`, `rotatable_bonds`
- Each function returns `{value, unit, method, rdkit_version}`; never a bare number.
- Write the exact definition used for every property in the docstring.

## Task 4 · Tests (`mcp/tests/`)
pytest known-answer tests with 10-15 simple molecules (water, ethanol, benzene, aspirin, caffeine, glucose...).
Expected values must come from a cited source, not from the function under test.
Invalid SMILES must produce a clean error.

## Task 5 · PubChem fetcher (`data/`)
Script that fetches reference values for a list of molecule names/CIDs.
- Max ~5 requests per second, with retry and backoff.
- Save raw responses plus `retrieved_at`.
- Do not overwrite old raw files.

## Task 6 · Validation report
Script that compares RDKit tool output vs PubChem for the sample set and writes
`validation/tool_vs_pubchem.md` listing every disagreement and the likely reason (definition difference vs error).

## Do NOT
- Do not add any toxic, hazardous or weapons-relevant compounds.
- Do not run any LLM benchmark yet. Predictions must be frozen on OSF first.
- Do not edit files in `runs/` once written.

When done, summarize what you built, what the tests cover, and what is still uncertain.
