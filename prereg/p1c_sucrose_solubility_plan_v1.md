# P1c - Sucrose solubility: first physical measurement (pre-registration v1)

**Status:** pre-registered before any measurement. No data collected yet.
**Date:** 2026-10-28
**Author:** Yasin Yagci (ORCID 0009-0001-3456-4299), independent researcher
**Scope:** benign kitchen chemistry; no LLM and no model prediction are involved.
**Purpose:** calibrate the measurement chain (scale, thermometer, saturation
judgement) on a system with a well-known answer, before any claim is made.

## 1. Question

Can a kitchen-grade protocol (1 g scale, 0-100 C thermometer) reproduce the
published solubility of sucrose in water within +/-15%?

## 2. Hypotheses (fixed before measurement)

- **H1 - accuracy.** At each of five temperatures (20, 40, 60, 80, 90 C) the
  measured saturation midpoint lies within +/-15% of the literature value.
- **H2 - trend.** Measured solubility increases monotonically with temperature.
- **H3 - repeatability.** The two replicates at each temperature differ by no
  more than 10% of their mean.

## 3. Reference values (g sucrose per 100 g water)

| T (C) | 20 | 40 | 60 | 80 | 90 |
|---|---:|---:|---:|---:|---:|
| solubility | 203.9 | 238.1 | 287.3 | 362.1 | 415.7 |

Source: standard CRC Handbook sucrose solubility table (g/100 g water),
cross-checked against the Wikipedia solubility table (g/100 mL water) after
unit conversion; the two tables agree within 3%.

## 4. Materials

- 3.5 kg sucrose (table sugar), one brand for all points (the ten points need
  about 3.0 kg; 2 kg was an arithmetic error)
- water, 100 g weighed per point
- kitchen scale, 1 g resolution (verified with a 100 g test mass)
- thermometer 0-100 C, +/-2 C
- pot, stove, spoon, timer, heat-resistant surface
- the CSV sheet `data/measurements/p1c_sucrose.csv`

## 5. Procedure (one point)

1. Weigh **100 g water** into the pot (scale, not a measuring cup).
2. Heat to the target temperature +/-2 C; keep the pot covered on low heat.
3. Add sugar in **10 g increments**; stir 30 s and wait 60 s after each.
4. Record:
   - `last_dissolved_g` - the last total that dissolved completely (clear, no
     crystals after 60 s);
   - `first_residue_g` - the first total where crystals persist after 2 min of
     stirring.
5. The measured value is the midpoint `M = (last + first) / 2`, with an
   uncertainty of `+/-(first - last) / 2`.
6. Two replicates per temperature (10 points total). Wash and dry the pot
   between replicates; keep the same sugar brand and water source.

## 6. Analysis (fixed)

- relative error `e = (M - reference) / reference`; H1 passes at a point when
  `|e| <= 0.15`.
- H2 passes when the five midpoints are strictly increasing in T.
- H3 passes at a temperature when `|M1 - M2| / mean(M1, M2) <= 0.10`.
- Report: per-point table, mean absolute error, maximum absolute error, H1/H2/H3
  verdicts. A failure is reported as a failure; the reference values are not
  changed after seeing the data.

## 7. Exclusions and deviations

- A point is excluded only for: spillage, burned or caramelised sugar,
  thermometer failure, or visible water loss (dry pot edge). Every exclusion is
  written to `docs/DEVIATIONS.md` with a reason.
- No point is dropped because it disagrees with the reference.

## 8. Fallback declared before measurement

If no 0-100 C thermometer is available, measure at **ambient (~20 C)** and
**boiling (~95-100 C)**, two replicates each (4 points). H1 and H3 still apply;
H2 is not testable with two temperatures. The run is then reported as
"fallback 4-point", not as the 10-point protocol.

## 9. What this does not do

- It does not test the LLM and does not produce a model prediction.
- It does not claim a new chemical fact; it calibrates the measurement chain.
- It is not a publication; it is the first entry in the real-measurement track.

## 10. Amendment 1 (2026-10-28, before any measurement)

The single-phase 10 g procedure needs 40+ additions at 90 C (over 7 h for the
10 points). Amendment: sugar is added in two phases.

- **Bulk phase:** 50 g steps until about 80% of the reference value, stirring
  20 s per step, no waiting time.
- **Fine phase:** from 80% to the endpoint, 10 g steps with 30 s stirring and a
  60 s wait, exactly as in section 5.

The endpoint rule (`last_dissolved_g`, `first_residue_g`, midpoint), the
hypotheses H1/H2/H3, the thresholds, the reference values and the analysis are
unchanged. Only the addition rate changes, and only before any data exist.

## 11. Amendment 2 (2026-10-28, before any measurement)

Materials correction: section 4 said 2 kg sucrose, but the ten points need
1,507 g per replicate set (204 + 238 + 287 + 362 + 416), i.e. about 3.0 kg for
two replicates. The material list is corrected to 3.5 kg. No hypothesis,
procedure, threshold or analysis changes.


