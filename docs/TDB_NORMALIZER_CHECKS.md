# TDB normaliser checks (2026-10-26)

Scope: MatCalc files only (`mc_al`, `mc_fe`, `mc_ni`). Originals untouched;
SHA-256 kept in `docs/TARGET_ALLOY_HEAT_SURVEY.md` section 1.

Pipeline per file: `scripts/tdb_normalize.py` (vendor commands, latin-1,
`N REF:` tags, `HMVA`, abbreviations, inline PHASE prose) then
`scripts/tdb_merge_constituents.py` (merge split PHASE/CONSTITUENT commands),
then `pycalphad.Database(...)`.

## Result per file

| file | normalise | merge | load in pycalphad 0.11.2 | verdict |
|---|---|---|---|---|
| `mc_al.tdb` | OK | OK | **FAIL** at `PHASE SI_DIAMOND_A4 1 1 > AL,CR,CU,MG,SI,TI,ZN >> 4` | **FAIL** |
| `mc_fe.tdb` | OK | OK | **FAIL** at `PHASE BETA_RHOMBO_B 1 1 > B,CU,MN,NB,TI >> 1` | **FAIL** |
| `mc_ni.tdb` | OK | OK | **FAIL** at `PHASE BETA_RHOMBO_B 1 1 > B,NB,SI,TI >> 0` | **FAIL** |

The parser rejects the PHASE statement itself, after the constituent list has
been merged in. Missing CONSTITUENT commands: mc_al 1, mc_fe 1, mc_ni 4 (those
phases were left untouched and are named in the run log).

## Melting-point check

**BLOCKED, not run.** No MatCalc database loads, so there is no end-to-end
system to compute pure Al or pure Fe melting with. No number is reported here;
a number produced by a database that fails to parse would be fiction.

Reference values held for the day it runs (literature, not re-verified in this
task): Al 933.47 K, Fe 1811 K at 1 atm (CRC Handbook of Chemistry and Physics).

## Conclusion

`pycalphad 0.11.2` cannot read the MatCalc TDB dialect, even after removing
vendor commands and merging PHASE/CONSTITUENT. The blocker is the PHASE grammar,
not the data. Next options, in order of cost: (1) OpenCalphad, which reads these
files natively, as the engine; (2) a converter that rewrites PHASE statements to
the Thermo-Calc form pycalphad expects; (3) a different database source whose
dialect pycalphad already parses (the shipped `Al-Mg_Zhong.tdb` loads cleanly -
see the engine inventory, section 2).

