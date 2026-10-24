# SCHEMA.md · kuro-jikken data layer (v1)

One **record** = one (molecule, property) pair. A molecule appears once per property
(long format; never one row with many values). File encoding UTF-8, CSV with header.

## Fields (in this exact column order)

| # | Field | Type | Rules |
|---|-------|------|-------|
| 1 | `id` | string | Unique, lowercase, no spaces. Pattern: `<name>_<property>` (e.g. `benzene_molecular_weight`) |
| 2 | `name` | string | Common, harmless compound name (e.g. `benzene`) |
| 3 | `smiles` | string | The exact SMILES string fed to tools. Source-fetched and kept verbatim (PubChem canonical SMILES) |
| 4 | `source` | string | Which source supplied the value: `pubchem` or `rdkit` |
| 5 | `source_id` | string | Identifier within the source: PubChem `CID` (e.g. `CID 2244`) or RDKit function path (e.g. `rdkit.Chem.rdMolDescriptors.CalcMolFormula`) |
| 6 | `retrieved_at` | ISO 8601 date | UTC date the value was fetched: `YYYY-MM-DD` |
| 7 | `source_version` | string | Version of the source: PubChem database snapshot date/page version or RDKit version (`X.Y.Z`) |
| 8 | `property` | enum | One of: `formula`, `molecular_weight`, `heavy_atom_count`, `ring_count`, `hbond_donors`, `hbond_acceptors`, `rotatable_bonds` |
| 9 | `value` | scalar | String for `formula`; float for `molecular_weight`; int for the four counts. No units inside the value |
| 10 | `unit` | string | `g/mol` (molecular_weight), `formula` (formula), `count` (all count properties) |
| 11 | `definition_note` | string | The exact definition/method behind this value (see below). Never empty |

## `definition_note` conventions

- RDKit-derived values: name the exact RDKit function and rule, including the `rdkit_version`.
  The property functions in `mcp/rdkit_tool.py` spell out their definitions in docstrings;
  rows sourced from RDKit must repeat the same definition, abbreviated.
- PubChem-derived values: note the PubChem definition; for `molecular_weight` this is
  *"average mass of the molecule computed with IUPAC standard average atomic weights"*.
- Known algorithm-dependent properties (`hbond_donors`, `hbond_acceptors`, `rotatable_bonds`,
  `ring_count` variant) must state that the value is per the cited method only, and that
  cross-source disagreement is expected and handled in `validation/tool_vs_pubchem.md`,
  not silently reconciled.

## Rules

1. Values only from cited sources. If a value cannot be verified, the row is not written.
2. Raw source responses kept under `data/raw_pubchem/` with a retrieval timestamp; old files are never overwritten.
3. The SMILES string is stored exactly as fetched; canonicalization says which tool worked with which structure.
4. Disagreements are recorded, not averaged away.

## Sample record (illustrative)

| Field | Value |
|-------|-------|
| id | `caffeine_molecular_weight` |
| name | `caffeine` |
| smiles | `CN1C=NC2=C1C(=O)N(C(=O)N2C)C` |
| source | `pubchem` |
| source_id | `CID 2519` |
| retrieved_at | `2026-10-24` |
| source_version | `PubChem record page, CID 2519 as of 2026-10-24` |
| property | `molecular_weight` |
| value | `194.19` |
| unit | `g/mol` |
| definition_note | `average mass with IUPAC standard average atomic weights (PubChem definition); RDKit comparison uses Descriptors.MolWt on the same SMILES, agreement tolerance ±0.10 g/mol recorded in validation/tool_vs_pubchem.md` |

*(Sample values above are placeholders marked as such; real dataset rows are written from
fetched responses only, with the raw file stored in `data/raw_pubchem/`.)*
