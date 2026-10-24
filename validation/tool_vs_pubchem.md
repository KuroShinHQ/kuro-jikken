# Tool vs PubChem - validation report (Task 6)

Provenance: raw PUG REST snapshots in data/raw_pubchem/ (2026-10-24); RDKit 2026.09.1 pinned; CIDs verified via name->CID lookup.

## 1) Structural identity and mass

| molecule | CID | formula pc | formula rd | MW pc | MW rd | dMW | heavy pc | heavy rd |
|---|---|---|---|---|---|---|---|---|
| water | 962 | H2O | H2O | 18.015 | 18.015 | +0.000 | 1 | 1 |
| ethanol | 702 | C2H6O | C2H6O | 46.07 | 46.069 | -0.001 | 3 | 3 |
| benzene | 241 | C6H6 | C6H6 | 78.11 | 78.114 | +0.004 | 6 | 6 |
| aceticacid | 176 | C2H4O2 | C2H4O2 | 60.05 | 60.052 | +0.002 | 4 | 4 |
| acetone | 180 | C3H6O | C3H6O | 58.08 | 58.080 | +0.000 | 4 | 4 |
| urea | 1176 | CH4N2O | CH4N2O | 60.056 | 60.056 | -0.000 | 4 | 4 |
| glycine | 750 | C2H5NO2 | C2H5NO2 | 75.07 | 75.067 | -0.003 | 5 | 5 |
| aspirin | 2244 | C9H8O4 | C9H8O4 | 180.16 | 180.159 | -0.001 | 13 | 13 |
| caffeine | 2519 | C8H10N4O2 | C8H10N4O2 | 194.19 | 194.194 | +0.004 | 14 | 14 |
| glucose | 5793 | C6H12O6 | C6H12O6 | 180.16 | 180.156 | -0.004 | 12 | 12 |
| citricacid | 311 | C6H8O7 | C6H8O7 | 192.12 | 192.123 | +0.003 | 13 | 13 |
| ibuprofen | 3672 | C13H18O2 | C13H18O2 | 206.28 | 206.285 | +0.005 | 15 | 15 |
| menthol | 1254 | C10H20O | C10H20O | 156.26 | 156.269 | +0.009 | 11 | 11 |
| vanillin | 1183 | C8H8O3 | C8H8O3 | 152.15 | 152.149 | -0.001 | 11 | 11 |

## 2) H-bond donors: Lipinski vs plain vs PubChem

| molecule | PubChem | Lipinski (NH/OH H count) | plain (donor atoms) | cause |
|---|---|---|---|---|
| water | 1 | 2 | 0 | definition gap: neither variant equals PubChem |
| ethanol | 1 | 1 | 1 | both variants match PubChem |
| benzene | 0 | 0 | 0 | both variants match PubChem |
| aceticacid | 1 | 1 | 1 | both variants match PubChem |
| acetone | 0 | 0 | 0 | both variants match PubChem |
| urea | 2 | 4 | 2 | plain/NonStrict variant matches PubChem |
| glycine | 2 | 3 | 2 | plain/NonStrict variant matches PubChem |
| aspirin | 1 | 1 | 1 | both variants match PubChem |
| caffeine | 0 | 0 | 0 | both variants match PubChem |
| glucose | 5 | 5 | 5 | both variants match PubChem |
| citricacid | 4 | 4 | 4 | both variants match PubChem |
| ibuprofen | 1 | 1 | 1 | both variants match PubChem |
| menthol | 1 | 1 | 1 | both variants match PubChem |
| vanillin | 1 | 1 | 1 | both variants match PubChem |

## 3) H-bond acceptors: Lipinski vs plain vs PubChem

| molecule | PubChem | Lipinski (N+O count) | plain (acceptor atoms) | cause |
|---|---|---|---|---|
| water | 1 | 1 | 0 | Lipinski/Default variant matches PubChem |
| ethanol | 1 | 1 | 1 | both variants match PubChem |
| benzene | 0 | 0 | 0 | both variants match PubChem |
| aceticacid | 2 | 2 | 1 | Lipinski/Default variant matches PubChem |
| acetone | 1 | 1 | 1 | both variants match PubChem |
| urea | 1 | 3 | 1 | plain/NonStrict variant matches PubChem |
| glycine | 3 | 3 | 2 | Lipinski/Default variant matches PubChem |
| aspirin | 4 | 4 | 3 | Lipinski/Default variant matches PubChem |
| caffeine | 3 | 6 | 3 | plain/NonStrict variant matches PubChem |
| glucose | 6 | 6 | 6 | both variants match PubChem |
| citricacid | 7 | 7 | 4 | Lipinski/Default variant matches PubChem |
| ibuprofen | 2 | 2 | 1 | Lipinski/Default variant matches PubChem |
| menthol | 1 | 1 | 1 | both variants match PubChem |
| vanillin | 3 | 3 | 3 | both variants match PubChem |

## 4) Rotatable bonds: default(strict) vs NonStrict vs PubChem

| molecule | PubChem | default | NonStrict | cause |
|---|---|---|---|---|
| water | 0 | 0 | 0 | both variants match PubChem |
| ethanol | 0 | 0 | 0 | both variants match PubChem |
| benzene | 0 | 0 | 0 | both variants match PubChem |
| aceticacid | 0 | 0 | 0 | both variants match PubChem |
| acetone | 0 | 0 | 0 | both variants match PubChem |
| urea | 0 | 0 | 0 | both variants match PubChem |
| glycine | 1 | 1 | 1 | both variants match PubChem |
| aspirin | 3 | 2 | 3 | plain/NonStrict variant matches PubChem |
| caffeine | 0 | 0 | 0 | both variants match PubChem |
| glucose | 1 | 1 | 1 | both variants match PubChem |
| citricacid | 5 | 5 | 5 | both variants match PubChem |
| ibuprofen | 4 | 4 | 4 | both variants match PubChem |
| menthol | 1 | 1 | 1 | both variants match PubChem |
| vanillin | 2 | 2 | 2 | both variants match PubChem |

## 5) Ring counts (manual count)

PubChem PUG REST has no RingCount property (probe: HTTP 400). Values below are labelled manual counts from structure; RDKit CalcNumRings (SSSR) is compared against them.

| molecule | rings (manual count) | rings (RDKit) |
|---|---|---|
| water | 0 | 0 |
| ethanol | 0 | 0 |
| benzene | 1 | 1 |
| aceticacid | 0 | 0 |
| acetone | 0 | 0 |
| urea | 0 | 0 |
| glycine | 0 | 0 |
| aspirin | 1 | 1 |
| caffeine | 2 | 2 |
| glucose | 1 | 1 |
| citricacid | 0 | 0 |
| ibuprofen | 1 | 1 |
| menthol | 1 | 1 |
| vanillin | 1 | 1 |
## 6) CID 1253 - CID assignment error

First seed fetch assigned CID 1253 to menthol from memory; the returned compound was C15H18N2O, not menthol (C10H20O). Name->CID resolution gives 1254. Raw cid_1253_*.json is retained as evidence; data/sample_set.json records the corrected CID.

## 7) Reproduce

    .venv\Scripts\python data/pubchem_fetch.py --verify-existing
    .venv\Scripts\python validation/build_tool_vs_pubchem.py
