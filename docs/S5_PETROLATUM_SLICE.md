# S5 - "vazelin benzeri" first vertical slice

Target: `Vazelin benzeri cilt koruyucu` -> application `formulation.petrolatum_like`.

Order: **logS asc**, verdict `CALIBRATED` from `data/calibration.json` (R5). Not an HSP match.

Pool: `melting.json` (18 entries, licence MIT); scanned 9.

| # | CAS | name | logS | +/- | gates |
|---|---|---|---|---|---|
| 1 | 544-85-4 | dotriacontane | -8.74 | +/-1.2 | structure:PASS, esol:PASS |
| 2 | 638-68-6 | triacontane | -8.21 | +/-1.2 | structure:PASS, esol:PASS |
| 3 | 630-03-5 | nonacosane | -7.94 | +/-1.2 | structure:PASS, esol:PASS |
| 4 | 630-02-4 | octacosane | -7.67 | +/-1.2 | structure:PASS, esol:PASS |
| 5 | 646-31-1 | tetracosane | -6.61 | +/-1.2 | structure:PASS, esol:PASS |

## Why this order

- The only calibrated property that fits this goal is aqueous logS; ascending
  means **most hydrophobic first** (petrolatum-like, not water-loving).
- Every row shows `gate.structure` + `gate.esol`; a RED gate never reaches the
  table.
- logS is a model value with a measured in-domain RMSE bar; it is not a
  measurement of the candidate in petrolatum.

## Refusal boundary (measured, not prose)

- `gate.hsp('8009-03-8')` -> **RED**: no Hansen entry for CAS 8009-03-8 (mixtures such as petrolatum have none) (R4).
- TEWL claim: `Vazelin benzeri ama TEWL dusuk olsun` -> **RED**: claim 'tewl' has no engine (product.performance)
- carcinogen claim: `Kanserojen olmayan bir yag yap` -> **RED**: claim 'kanserojen' has no engine (biology.toxicity)
- unknown goal: `Bana guzel bir sey yap` -> **CLARIFY**: no application matches
- No occlusivity, TEWL, skin feel, stability, safety or cost follows.

## Reproduce

```
python tools/vertical_slice.py --check
python mcp/screen.py "Vazelin benzeri cilt koruyucu" --limit 5
python tools/build_pool.py --check
```
