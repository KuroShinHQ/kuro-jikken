# Cosmetics dataset (S4) - labels x CosIng

**One line:** 2,560 INCI names that really occur on product labels, joined to
their EU CosIng record (identity, CAS/EC, function, restriction) and to the
number of labels and brands that carry them.

**It is not a formulation engine.** "Make me a moisturiser" is a permanent RED
(ROADMAP S4). Measured 2026-10-28: `pipeline.compute("nemlendirici yap", {})`
-> `verdict RED`, `reason no engine`. A dataset row is not a recipe, a dose or
a safety verdict.

## Sources

| id | what | licence | size |
|---|---|---|---|
| `obf_products_20261028` | Open Beauty Facts dump: 79,010 product records, 20,185 with a readable INCI list | ODbL-1.0 + DbCL-1.0 | 104,231,691 B |
| `cosing_labels_20261028` | CosIng records for 8,663 label names: 4,065 records, 4,060 names matched | CC-BY-4.0 (Decision 2011/833/EU) | 2,337,454 B |

Raw files stay outside the repository (`C:\KuroshinHQ\_hub\data\cosmetics`);
`data/manifest.json` pins size and hash. The derived pool is
`data/cosmetics/cosmetics.json` (1,136,445 B): ODbL-1.0 + DbCL-1.0 for the label
counts, CC-BY-4.0 for the CosIng fields, attribution inside the file.

## Method, and why the label text wins

Open Beauty Facts also ships a parsed `ingredients` field. It splits on `/` and
inside parentheses: *Caprylic/Capric Triglyceride* becomes `CAPRYLIC` +
`CAPRIC TRIGLYCERIDE`; *Ricinus Communis (Castor) Seed Oil* becomes
`RICINUS COMMUNIS` + `SEED OIL`. Against one index the parsed field matched
CosIng on 51.4 % of names, the printed text on 57.6 %.

The builder reads `ingredients_text` first and falls back to the parsed field
only when the text is missing. Seven declared aliases collapse naming
conventions, not data: `AQUA/WATER`, `AQUA/WATER/EAU`, `EAU` -> `AQUA`;
`FRAGRANCE`, `PARFUM/FRAGRANCE`, `PERFUME` -> `PARFUM`. CosIng keeps the period
in `ALCOHOL DENAT.`, so a dotted second pass asks for that form.

## Coverage (2026-10-28 build)

- 79,010 product records; 20,185 carry a readable INCI list.
- 47,215 distinct label tokens; 3,600 occur on at least 5 products.
- 2,560 of those (71.1 %) match a CosIng record; 1,040 do not and are listed
  as `coverage.unmatched_examples` (US colour names, "FLAVOR", fragments).

## What a row means

`{"inci": "GLYCERIN", "products": 10045, "brands": 2914, "cosing": {...}}`
reads: 10,045 product records in this dump carry GLYCERIN on the label, from
2,914 brands; CosIng lists it as HUMECTANT/SOLVENT with CAS 56-81-5.

- `products` is a label count, not market share: OBF is crowd-sourced.
- `functions` are regulatory descriptors, not efficacy claims.
- `restricted: true` means the CosIng record carries a restriction, annex
  entry or maximum concentration. It is not a safety verdict.

## What it cannot do

- No formulation, no dose, no "moisturiser recipe" (permanent RED).
- No concentration, safety or efficacy claim; no ranking of ingredients.
- Exact-name join only. No fuzzy matching; the only synonym resolution is the
  seven declared aliases above.
- CosIng `status` is the database's own field, not a legal authorisation.

## Rebuild

```
python tools/fetch_cosmetics.py --obf      # 104 MB dump, outside the repo
python tools/fetch_cosmetics.py --cosing   # 4,065 records for 8,663 names
python tools/build_cosmetics.py            # data/cosmetics/*
python tools/build_cosmetics.py --check    # exit 1 when stale
python tools/cosmetics_lookup.py --top 15
```

The CosIng search API caps deep paging at 10,000 of its 36,197 records, so the
fetch asks for the names that occur on labels instead of crawling the whole
database. `names_queried` / `names_matched` are stored with the raw file.

Files: `tools/cosmetics_sources.py` (readers, tokeniser, aliases),
`tools/fetch_cosmetics.py`, `tools/build_cosmetics.py`,
`tools/cosmetics_lookup.py`, `tools/tests/test_cosmetics_pool.py`.

## Honest limits

- OBF labels are user-entered, multilingual and uneven; the dump is not a
  sales panel and its counts are not market data.
- 28.9 % of recurring label names have no CosIng record; they are counted, not
  silently dropped.
- CosIng is a reference database, not a legal text; read the regulation itself
  before any compliance statement.

