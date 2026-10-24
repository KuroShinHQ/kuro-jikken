# mcp/tests/

pytest known-answer tests for the RDKit tool module.

Ground rules (docs/FIRST_TASKS.md Task 4):
- 10-15 simple, harmless molecules.
- Expected values come from a cited source (PubChem), never from the function under test.
- Invalid SMILES must produce a clean error, not a crash.
