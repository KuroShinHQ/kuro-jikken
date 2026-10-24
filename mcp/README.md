# mcp/

RDKit-based tool server for Mode B of the study, plus pure computation functions and their tests.

- Pure functions only: no network access, deterministic.
- Each property function returns `{value, unit, method, rdkit_version}` — never a bare number.
- Known-answer tests live in `tests/`.
