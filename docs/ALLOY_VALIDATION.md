# Alloy validation (2026-10-26)

Engine: `pycalphad 0.11.2` + MatCalc open aluminium database, pre-modified for
pycalphad by the Materials Genome Foundation workshop repository.
Database file: `mc_al_v2.032.pycalphad.tdb`, 289.410 B,
SHA-256 `BBA064BB858E03348CA7D0455391E3527E5DBD9FAC1F4C0B6BC284DA2BADA4AB`.

The database is **not** in this repository: MatCalc open databases are
ODbL 1.0 + DbCL 1.0 (share-alike). It lives in `KJ_TDB_DIR`
(default `C:\KuroshinHQ\_hub\data\alloy_tdb_mgf`).

## Reproduce

```
.venv_inventory\Scripts\python.exe tools\alloy_liquidus.py
```

## Results

| element / alloy | computed | published | difference |
|---|---|---|---|
| pure Al melting | 933.47 K | 933.47 K | 0.00 |
| pure Fe melting | 1810.95 K | 1811 K | 0.05 |
| pure Ni melting | 1728.26 K | 1728 K | 0.26 |
| Al-1 at% Cu liquidus | 926.4 K | ~928 K | ~1.6 |
| Al-5 at% Cu liquidus | 900.4 K | ~903 K | ~2.6 |
| Al-10 at% Cu liquidus | 867.6 K | ~870 K | ~2.4 |
| Al-17.3 at% Cu liquidus | 829.3 K | ~821 K | ~8.3 |

Method: equilibrium over seven Al-Cu phases (LIQUID, FCCAL, THETA_AL2CU,
ALCU_E, ALCU_ETA, AL2CU3_D, AL9CU11_Z); liquidus = temperature where the last
solid disappears, bisection with 9 steps.

## Limits

Melting and liquidus only. Creep, oxidation, corrosion and mechanical strength
are not modelled by CALPHAD. Published values are read from the Al-Cu phase
diagram; the 17.3 at% point sits next to the eutectic, where a small database
difference moves the number most.
