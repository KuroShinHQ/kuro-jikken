# kuro-jikken · LLM modes A/B/C · Pre-registration (plan v1)

**Status:** DRAFT until registered on OSF. Written before any LLM run on benchmark questions.
**Author:** Yasin Yagci (ORCID 0009-0001-3456-4299), independent researcher
**Date:** 2026-10-25
**Repository:** https://github.com/KuroShinHQ/kuro-jikken
**Code version at writing:** v0.1.1 (DOI 10.5281/zenodo.23638653; concept DOI 10.5281/zenodo.23633858)

---

## 1. Question

When an LLM answers basic molecular-property questions from a SMILES string, how much does
(B) access to deterministic RDKit tools, and (C) tools plus an automatic consistency check,
reduce errors compared with (A) no tools? What kinds of errors remain?

## 2. Hypotheses

Confirmatory (tested per model):

- **H1.** Error rate of mode B is lower than that of mode A.
- **H2.** Error rate of mode C is lower than that of mode B.
- **H3.** In modes B and C, more than 50% of the remaining errors are *process errors*
  (`no_tool_call`, `bad_smiles_passed`, `parse_failure`, `unit_error`), not chemistry-knowledge errors.

Exploratory (reported as exploratory, no confirmatory test):

- **E1.** In mode A, error probability increases with molecule size (heavy-atom count).
- **E2.** In mode A, error rate differs between counting-type properties and formula/mass.

A hypothesis that fails will be reported as failed.

## 3. Materials

**3.1 Molecules.** Taken from the AqSolDB data already in this repository (CC0), restricted to the
in-domain rule used in the solubility study: neutral, single-component, no metal atoms, no phosphorus,
MW <= 500, parseable by RDKit. Random sample of N = 250, seed 20261026, SMILES only (no names).
- First 50 IDs = **pilot set** (debugging and throughput only; never reported as results).
- Next 200 IDs = **confirmatory set**.
- Both ID lists and their SHA-256 are committed before any run.

**3.2 Properties (7).** Molecular formula (Hill system), molecular weight, heavy-atom count,
ring count (SSSR), H-bond donors (Lipinski definition), H-bond acceptors (Lipinski definition),
rotatable bonds (strict; RDKit `CalcNumRotatableBonds` default). Reference values come from the tested functions in
`mcp/rdkit_tool.py` (rdkit 2026.09.1; pip package name `rdkit==2026.9.1` as pinned in requirements.txt).
Every question states the definition in plain words, so a correct answer is well defined.
Items per (model, mode): 200 x 7 = 1,400.

**3.3 Models.** One primary (confirmatory) model, local only, so version and settings are controllable:
- **Primary (confirmatory):** `Hermes3.6-35B-A3B-Uncensored-Genesis-MTP-APEX-Compact.gguf`, 18,339,420,608 bytes,
  SHA-256 `A60C9CA376578AC98FC419D12CD1FAD4D47C1CFEC1BBE75A162F6BBB86E554B2`;
  chat template `qwen-fixed-chat-template.jinja`, SHA-256 `E57684BAE4156211A55473C5A63BE976A405A37AB5BE5AE0E5ABF1DF5349C4B2`.
  llama.cpp build, context size, sampling parameters and draft/speculative settings (the draft model stays disabled)
  are fixed at Freeze 2.
- A standard open-weights ~7-9B instruct model MAY be run as a secondary, exploratory replication; its results are
  reported separately and are not part of the confirmatory tests.
Cloud models (if used) are **exploratory only**, with date and version logged; they are not part of the confirmatory tests.

## 4. Modes

- **A (bare):** no tools. The model answers from its own knowledge. No internet.
- **B (tools):** the model may call the RDKit tool functions (same set as the MCP server).
  Max 5 tool calls per question. No internet. The final answer is taken as given.
- **C (tools + verification):** as B, plus a deterministic check after the model answers:
  (1) a tool was called with a SMILES whose canonical form equals the question's molecule,
  (2) the answer matches the tool output within the scoring tolerance, (3) the answer has a valid format.
  If a check fails, the model gets one retry with the failure message. After the retry the answer is
  recorded as given and flagged `verification_failed` if it still fails. The verifier never writes the answer itself.

## 5. Procedure and freezes

- Fixed system prompt per mode; JSON answer format; temperature 0; fixed seed; fixed max tokens.
  Question order is shuffled once (seed recorded) and is the same for all modes.
- Every run is logged as append-only JSONL: prompt hash, raw response, tool trace, timing,
  model file hash, llama.cpp build, parameters.
- **Freeze 1:** this document registered on OSF before any run on benchmark questions.
- A pilot (50 molecules) is allowed after Freeze 1 for debugging and throughput measurement only.
- **Freeze 2** (dated OSF amendment, before the confirmatory run): final prompts (SHA-256), model file names
  and SHA-256, llama.cpp build, ID-list hashes, final N (see section 8). Prompts may change after the pilot
  until Freeze 2, never after.

## 6. Scoring

- Formula: equal after Hill-system normalization. Counts: exact match. Molecular weight: |difference| <= 0.05 g/mol.
- Missing or unparseable answer = wrong (`parse_failure`).
- The answer after the final retry is the one scored.
- The scoring script is deterministic and committed before any run.
- Error categories: `no_tool_call`, `bad_smiles_passed`, `parse_failure`, `unit_error`, `arithmetic_error`,
  `chemistry_knowledge_error`, `other`. Assigned by deterministic rules from the tool trace first; the rest
  by manual review, with the mode hidden where possible.

## 7. Analysis

- Primary: for the single primary model, error rate per mode; paired exact McNemar tests (A vs B, B vs C) over all items.
- 95% confidence intervals for differences by cluster bootstrap (resampling molecules).
- Holm correction across the two confirmatory tests (H1, H2); alpha = 0.05.
- H3: share of process errors among all errors in B and C, per model.
- Secondary: results by property, tool-call rate, latency, `verification_failed` rate.
- Everything not listed here is exploratory and will be labeled so.

## 8. Feasibility fallback

If the pilot shows that the confirmatory run of the primary model would take more than 48 hours, N is reduced to
the first 100 confirmatory IDs in the registered order. This decision uses pilot
throughput only, never accuracy.

## 9. Author's expectations (fill in BEFORE registering)

- Overall error rate, mode A: 89 %
- Overall error rate, mode B: 9 %
- Overall error rate, mode C: 6 %
- Property I expect to be hardest in mode A: molecular weight (tolerance 0.05 g/mol)
  and rotatable bonds
- Risk I see for H1: the local quantized model may call tools with broken formatting,
  which could make mode B worse than mode A

Written on 2026-10-25 before any LLM run on benchmark questions.

## 10. Deviations and transparency

- Any deviation from this plan is logged in `DEVIATIONS.md` with date and reason; primary analyses stay as registered.
- Negative and null results will be published (repository release with DOI, then a preprint).
- AI assistance: parts of code and text are drafted with AI assistants; design decisions, predictions,
  and interpretation are the author's responsibility. Commit history shows changes over time.

## 11. Scope and limitations

- Only common, benign molecules; no hazardous compounds, synthesis routes, or wet-lab protocols.
- AqSolDB is public, so models may have seen some molecules during training; SMILES-only questions reduce but do not remove this.
- Heavily quantized local models may behave differently from full-precision versions; results apply to the tested files only.
- Only one model is tested confirmatorily; results do not generalize to all LLMs.





