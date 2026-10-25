# Standards & data-access research note — 2026-10-25

Preparation note only. **No engine was run. No error, F1, accuracy or benchmark
score was computed.** `prereg/formulation_screening_plan_v0.md` was not edited.

Three checks were requested: (1) IUPAC-NIST Solubility Database terms and
coverage, (2) AqSolDB ↔ PubChemQC sigma-profile overlap counts, (3) publication
rules for ChemRxiv, Polaris Hub and arXiv.

---

## 1. IUPAC-NIST Solubility Database (NIST SRD 106)

| item | finding |
|---|---|
| Official page | https://srdata.nist.gov/solubility/ |
| Version / DOI | **Version 1.1**, NIST Standard Reference Database 106, DOI `10.18434/T4QC79`; data content last update **2012**, page last updated 2015-02-18 |
| Scope | mutual solubilities and liquid–liquid equilibria of **binary, ternary and quaternary** systems |
| Size | **> 67,500** solubility measurements, **18 volumes**, ~**1,800** substances, **5,200** systems (473 critically evaluated), >1,800 references (Introduction page, web v1.0, March 2006) |
| Compounds | water, sea water, heavy water, inorganic compounds, hydrocarbons, halogenated hydrocarbons, alcohols, acids, esters, nitrogen compounds |
| Temperature / pressure | no fixed range: "solubilities at elevated and low temperatures and at elevated pressures have also been included" (original data units; mass and mole fractions) |
| Access format | HTML search interface by CAS number / name / formula / system. IUPAC SDS volumes **1–65 as PDF files** (https://srdata.nist.gov/solubility/IUPAC/iupac.aspx); volumes 66–105 published in *J. Phys. Chem. Ref. Data* |
| Bulk download / API | **none found** on the official pages: no CSV/JSON export, no API. Only the search interface and PDF volumes |
| PubChem CID match | components are identified by **IUPAC name, formula and CAS Registry Number**; no CID or InChIKey field. CAS/name → CID mapping would be an external, unverified step |
| Terms of use | https://www.nist.gov/srd/public-law — *"Standard Reference Data (SRD) are copyrighted by the U.S. Secretary of Commerce on behalf of the United States of America. All rights reserved. None of our SRD may be reproduced, stored in a retrieval system or transmitted, in any form or by any means, electronic, mechanical, photocopying, recording or otherwise, without prior permission."* |
| Disclaimer | no warranty of quality/completeness; not a reuse licence |

**Verdict: NOT CLEARED for reuse/redistribution in our publication.** The SRD
terms require **prior permission**; there is no open licence text on the site.
Therefore the liquid–liquid mutual-miscibility question currently has **no
cleared label source** from this database. Do not download-and-redistribute it;
a written permission request (NIST SRD contact form) would be required first.

---

## 2. AqSolDB ↔ PubChemQC sigma-profile DB — counts only

Method: exact **InChIKey** intersection (AqSolDB has no PubChem CID column; the
sigma index has both CID and InChIKey). Local files:

- AqSolDB: `data/solubility/raw/aqsoldb_20261025.tab` (CC0 1.0; Harvard Dataverse
  DOI `10.7910/DVN/OVHAW8`; SHA-256 in `data/solubility/SOURCE.md`).
- PubChemQC index: `C:\KuroshinHQ\_hub\data\formulation_sigma\sigma_profile_index.parquet`
  (v1.0.0, sha256 `810e18592807da962a718753abfafaa32bf423ac6afa87dbbd9707267cea73f0`).

| count | value |
|---|---|
| AqSolDB rows | **9,982** |
| AqSolDB rows with InChIKey | 9,982 |
| AqSolDB unique InChIKeys | **9,982** |
| PubChemQC sigma rows | **361,583** |
| sigma rows with non-null InChIKey | 356,268 |
| sigma unique InChIKeys | **334,714** (21,554 duplicate rows) |
| **matched unique molecules** | **3,416** = **34.22 %** of AqSolDB |
| liquids at 25 °C | **not countable** — AqSolDB has no phase, melting-point or temperature column; 0 counted is *not* 0 liquids |

Notes:

- AqSolDB columns include InChIKey, SMILES, Solubility (logS), SD, MolWt,
  MolLogP, TPSA and RDKit descriptors, plus a `Group` label (G1–G5). None of
  these is a physical-state or melting-point field.
- The intersection is by identifier only. No engine was run and no prediction
  was compared with any label.
- The 3,416 molecules are a **candidate universe** for an AqSolDB-based
  question (sigma engine vs ESOL-style baseline), not evidence for a
  liquid–liquid miscibility question.

---

## 3. Publication rules (official pages)

### 3.1 ChemRxiv

Official pages: https://chemrxiv.org/submission-guide · https://chemrxiv.org/faqs

**Access note:** `chemrxiv.org` returned **HTTP 403 / Cloudflare challenge** to
direct fetch, the project's stealth fetcher and a real Chrome session. The
statements below are therefore taken from the **indexed excerpts of the official
pages**, not from a full page read on this machine. Treat this subsection as
**KISMI (partial) evidence** until the pages are opened manually.

- **ORCID iD is required** before submitting.
- **No institutional-affiliation requirement is stated**; ORCID is the named
  prerequisite. An independent researcher can submit with an ORCID iD.
- **Licence options:** CC BY 4.0, CC BY-NC 4.0, CC BY-NC-ND 4.0.
- **No copyright transfer:** "ChemRxiv does not require authors to assign
  copyright."
- **Screening:** submissions are screened by ChemRxiv moderators; screening is
  **not peer review** and typically takes **2–3 business days**.

### 3.2 Polaris Hub

Official pages: https://polarishub.io/legal/terms-of-use ·
https://polaris-hub.github.io/polaris/stable/quickstart.html ·
https://polaris-hub.github.io/polaris/stable/api/utils.types.html ·
https://polaris-hub.github.io/polaris/stable/api/benchmark.html

- **Anyone can create an account** (sign-up link in the official quickstart);
  login is required to upload artifacts. Upload is done with
  `Dataset.upload_to_hub(owner=...)` / `Benchmark.upload_to_hub(...)`.
- **Individuals can upload datasets and benchmarks.** The platform agreement
  puts the responsibility on the user ("User may upload…", "User is solely
  responsible for the content"); no institutional requirement is stated.
- **Licence requirements:** each dataset must select a licence from the
  supported list:
  **CC-BY-4.0, CC-BY-SA-4.0, CC-BY-NC-4.0, CC-BY-NC-SA-4.0, CC0-1.0, MIT**
  (`SupportedLicenseType`). **No-ND licences are not supported.**
- The user must have the right to redistribute the data; if no licence is
  chosen, the terms grant other users only a platform-scoped use right.

**Implication:** AqSolDB (CC0) is acceptable on Polaris; IUPAC-NIST SRD data is
not, because redistribution requires prior permission.

### 3.3 arXiv

Official pages: https://info.arxiv.org/help/endorsement.html ·
https://arxiv.org/category_taxonomy

- **Endorsement is required** before a first submission, or before submitting to
  a new category.
- An institutional email (with claimed papers) can produce endorsement
  automatically; otherwise a **personal endorsement** by an established arXiv
  author in that category is needed (at least one positive endorsement per
  endorsement category).
- **Physics is special:** individual physics subject classes are endorsement
  domains (the official page gives `phys.acc-phys`, `phys.med-ph` as examples).
  Therefore **`physics.chem-ph` is its own endorsement domain**.
- `physics.chem-ph` (Chemical Physics) explicitly includes **chemical
  thermodynamics**, so it is the natural category for this work.

**Verdict: it affects us.** With no institutional email, a preprint in
`physics.chem-ph` needs an endorser in that class. This is a real gate that
should be resolved before announcing an arXiv preprint (ChemRxiv has no such
gate).

---

## 4. What this changes for the next decision

1. **IUPAC-NIST is out** unless written permission is obtained. The
   liquid–liquid miscibility question has **no cleared label source** today.
2. **AqSolDB is clean (CC0) and overlaps 3,416 molecules** with the sigma DB,
   but it measures **aqueous solubility**, not liquid–liquid miscibility. A
   plan built on it answers a different question ("sigma engine vs ESOL
   baseline"), and the liquid-at-25 °C count cannot be derived from the file.
3. **ChemRxiv is the independent-friendly venue** (ORCID only, no copyright
   transfer, CC BY option). **Polaris accepts individuals** but only the listed
   licences. **arXiv needs a `physics.chem-ph` endorser.**
4. The plan should not be rewritten until the label source is chosen; the
   author's §9 numbers are still the captain's to give.

---

## 5. Reproduction

- Overlap script (temporary, this machine):
  `C:\Users\pc\AppData\Local\Temp\opencode\count_aqsoldb_overlap.py`
  Run with the system Python that has `pyarrow` (24.0.0); the repo venv does
  not include `pandas`/`pyarrow`.
- Counts were produced by streaming the TSV with `csv.DictReader` and reading
  only `CID` + `InChIKey` from the Parquet index; exact string equality, no
  normalisation of InChIKey case beyond `strip()`.
- No network call was made for the counts; no engine installation or run.
