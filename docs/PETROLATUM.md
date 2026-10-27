# Petrolatum and Hansen parameters (R4 decision)

Date: 2026-10-27. Decision id: `DEC-20261027-R4`.
Status: **permanent RED** until a sourced dataset exists.

## Question

`screen()` and the "vazelin benzeri" target (S5) need a Hansen reference to rank
candidates by distance (`Ra`). Petrolatum is the natural reference
(CAS `8009-03-8`). Does this repository have a Hansen entry for it?

## Sources checked (2026-10-27)

| Source | Petrolatum 8009-03-8 | Paraffin wax 8002-74-2 | Mineral oil 8042-47-5 |
|---|---|---|---|
| `chemicals` 1.5.2 - MANUEL_RUBEN_2022 | none | none | none |
| `chemicals` 1.5.2 - ALSHERI_HANSEN | none | none | none |
| `chemicals` 1.5.2 - HSPIPY | none | none | none |
| `chemicals` 1.5.2 - WDR_SCHRIER | none | none | none |
| `_hub/data` | no HSP dataset (sigma profiles are COSMO) | - | - |

`hansen_delta_d/p/h` return `None` for all three; `data/pool/melting.json` records
petrolatum and paraffin wax as `skipped` (no `Hfus`), and `data/pool/hsp.json`
contains neither.

## Decision

1. **`gate.hsp("8009-03-8")` stays RED** ("no Hansen entry ... mixtures such as
   petrolatum have none"). No number is invented.
2. **No surrogate.** Using a single alkane, squalane or mineral-oil guess as
   "petrolatum" would move an unmeasured number into a ranking; R5 forbids
   ordering on uncalibrated properties, and a surrogate is not petrolatum.
3. **S5 must not claim an HSP match.** The first "vazelin benzeri" slice may use
   the CALIBRATED logS ordering (hydrophobicity) and must show the R4 blocker,
   exactly as `screen()` already does (`reference: gate.hsp RED`).

## What would change this decision

A dataset that gives, for a **defined** petrolatum (CAS or composition range):
dD/dP/dH with units, temperature/method, a licence that allows use here, a
variability statement (it is a mixture, not a compound), and an entry in
`data/manifest.json`. Then the gate flips to PASS, the pool gains a row, and the
calibration ledger must still say whether Ra may order anything (today it may
not: HSP is `REFERENCE_ONLY`).

## Test pin

`mcp/tests/test_petrolatum.py` pins the RED verdict, the `chemicals` gap, the
resolver mapping (`vazelin` -> `8009-03-8`) and the screen reference gate, so
this decision cannot silently drift.



