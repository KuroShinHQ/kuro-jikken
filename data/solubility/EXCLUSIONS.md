# data/solubility/ · EXCLUSIONS and split (decided before any results)

Fixed exclusion rule, written before any evaluation:

1. Any molecule containing **phosphorus** (`[#15]` SMARTS match) is excluded.
2. Any SMILES that **RDKit cannot parse** is excluded.

No manual exclusions were made afterwards.

## Counts (from `prepare.py` run, 2026-10-25)

| item | count |
|---|---|
| input rows (AqSolDB) | 9,982 |
| excluded — phosphorus | 387 |
| excluded — unparseable | 2 |
| **kept** | **9,593** |

## Deterministic split

- Seed: **20261025**, method: sort by AqSolDB `ID`, then `random.Random(seed).shuffle`, then slice.
- tune: 4,796 · validation: 2,398 · **locked: 2,399**.
- Locked ID list: `locked_ids.txt`; its SHA-256 is committed in
  `validation/solubility/LOCK.sha256` **before** any evaluation:

```
9f8ccc5d69e4accc4dece2f07cd9588345dc812d051f4ba39a7f588bcca2da64  locked_ids.txt
```
