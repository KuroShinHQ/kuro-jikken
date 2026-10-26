# Alloy heat-resistance target: data survey (2026-10-26)

Survey + design only. No alloy calculation, no accuracy number, no model.
Everything below is VERIFIED from the file or the URL named, unless tagged.

## 1. Databases downloaded

| file | bytes | SHA-256 | elements | phases |
|---|---|---|---|---|
| `mc_fe.tdb` | 489,296 | `AA02077EAC3F602DD7479CBEAFB09B450E282716752B3AE2B1FC3A57D9C64865` | 25 | 136 |
| `mc_ni.tdb` | 416,720 | `84BA813156E1F7D8BDE495D74420319AFEC03572B981F6B56103807F305313AB` | 22 | 103 |
| `mc_al.tdb` | 308,711 | `87EC595F2CAAE189227ED11D5598C899B436B866CCFEFEA91304CA57188817C4` | 12 | 196 |
| `COST507.tdb` | 296,347 | `80363E1DE4AA1EE0750DF28EF48E1524EF64B7988D6517649FFF1C991E3ED641` | 27 | 241 |
| `solders.tdb` | 19,675 | `8A606FA52757EF39B9C696044986F8034C81E15A5F5A4C20C07EA0C29943FBEC` | 6 | 14 |

Sources: matcalc.at open-databases page (mc_*), opencalphad.com/databases.php
(COST507.zip, solders.zip). Element sets and phase counts extracted from the
files (regex over ELEMENT/PHASE lines), not from vendor claims.

Element sets:
- mc_fe: Al B C Co Cr Cu Fe H Hf La Mn Mo N Nb Ni O P Pd S Si Ta Ti V W Y
- mc_ni: Al B C Co Cr Cu Fe Hf La Mn Mo N Nb Ni O S Si Ti V W Y Zr
- mc_al: Al Cr Cu Fe Mg Mn Ni Sc Si Ti Zn Zr
- COST507: Al Ar B C Ce Cr Cu Fe Hf Li Mg Mn Mo N Nb Nd Ni O Si Sn Ta Ti V W Y Zn Zr
- solders: Ag Bi Cu Pb Sb Sn

## 2. Parser status: 0 / 5 load as shipped (pycalphad 0.11.2)

`Database(path)` fails on all five. Blockers are vendor syntax, not science:
`REFERENCE_ELEMENT`, `ADD_COMPOSITION_SET`, `ATTACH_CONTRIBUTION`,
`PARAMETER HMVA(...)`, `N REF:` tags, latin-1 bytes, legacy `FUN`/`PARA`
abbreviations, and free-text header lines.

A normaliser was written and iterated (drop vendor commands, decode latin-1,
strip `N REF:` tags, drop HMVA, expand abbreviations, strip inline prose).
Result: the parser advances further on every file but still stops, so **no
database is usable by pycalphad today without more conversion work**. The
converted copies live in `data/alloy_tdb_normalized/` and are marked
experimental, not scientific input.

## 3. Open reference data to score against later

| source | quantity | points | terms |
|---|---|---|---|
| NIST solder database (metallurgy.nist.gov/phase/solder/solder.html) | liquidus/solidus for solder systems | unknown | page offers data; explicit reuse licence **UNCLEAR** -> exclude until clarified |
| COST507 report (Ansara et al.) | the assessment behind COST507.tdb | n/a | **UNCLEAR**, report not openly licensed |
| TDBDB (avdwgroup.engin.brown.edu) | index of TDB sources + DOIs | n/a | hosts nothing; rights per source -> **UNCLEAR** |
| Crossref-indexed experimental papers | solidus/liquidus points | per paper | DOI is citeable, tables are not copied; licence per paper **UNCLEAR** |

**Verdict for section 3: no system currently has BOTH a clean TDB and clean
reference data.** The blockers are parser compatibility and reference-data
licence, in that order. Nothing here is a candidate for a scorecard yet.

## 4. ODbL note (not legal advice)

The MatCalc databases are under ODbL 1.0 (share-alike on the *database*).
Publishing a table of computed results is not obviously a derived database;
publishing a modified TDB would be. This must be settled before any release,
and the answer belongs in the prereg, not in code.



