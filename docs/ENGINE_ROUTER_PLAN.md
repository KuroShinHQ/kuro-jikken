# Engine Router Plan v1 - from a sentence to a number, or an honest "no"

Date: 2026-10-26. Status: **plan only, no code yet**. Written after web research
and an inventory of what this repository already has.

## 0. One sentence

A free-text request ("will this alloy survive 600 C", "is vaseline compatible
with this cream") must become **one gated number** with unit, method, error bar,
limits and a reproduce command - or an explicit, reasoned **refusal**. The LLM
never computes and never invents: it may only normalise the sentence and fill a
fixed schema.

## 1. Why this is the right shape (external evidence)

| Finding | Source | Consequence for us |
|---|---|---|
| LLM + 18 expert tools beats the same LLM alone on chemistry tasks | ChemCrow, arXiv:2304.05376 / Nat. Mach. Intell. 2024 | value is in the tools and in their wiring, not in the chat |
| Autonomous systems work when the LLM plans and **tools execute** | Coscientist, Nature 614, 214 (2023) | plan/execute split, execution is deterministic code |
| Top LLMs answer textbook chemistry well but still fail numeric/unit tasks; benchmarks need semantic scoring of values and units | ChemBench, Nat. Chem. 2025 (s41557-025-01815-x) | every number must come from code; units must be checked, not trusted |
| Biology agent capability is benchmarked separately and is hard | LAB-Bench, arXiv:2407.10362 (2,457 tasks) | biology rows stay RED until a validated engine exists |
| A model must declare a **defined domain of applicability** (OECD Principle 3) | OECD (Q)SAR Assessment Framework, 2nd ed. 2024 | every engine needs an explicit AD gate, not a vibe |
| Systematic names can be parsed to structures by an open tool | OPSIN (Lowe 2011; now at EMBL-EBI, https://www.ebi.ac.uk/opsin) | name -> SMILES is a solved preprocessing step, not LLM work |
| Materials databases expose a common API | OPTIMADE v1.3 (optimade.org; Andersen 2021) | later phase: external materials data through one adapter, keys/licences first |

Conclusion: build a **deterministic router + gate layer** around the engines we
already validated, with a fixed answer contract and an audit ledger. Do not add
engines before the wiring exists.

## 2. What exists today (verified)

| Engine | Entry point | Data | Validation already done | Gate today |
|---|---|---|---|---|
| RDKit 2026.9.1 | `mcp/rdkit_tool.py` | none needed | parser/descriptor smoke tests | SMILES must parse |
| ESOL (Delaney) | `mcp/esol.py` | AqSolDB, 9,982 rows, CC0 | in-domain RMSE ~1.22 log; salts/metals ~5 log | `domain_classify`: neutral, single component, no metal, no P, MW <= 500 |
| UNIFAC gamma | `tools/unifac_gamma.py`, MCP `unifac_gamma` | ugropy groups + thermo 0.6.1 matrices | `docs/GAMMA_VALIDATION.md`: Dortmund median 21 %, 7/9 within +/-30 % | group exists, main-group pair exists (`MissingInteraction`) |
| cOSMO-SAC | `mcp/cosmosac_pubchemqc.py` | PubChemQC sigma: 361,583 profiles (122.2 MB) + index; refit constants | sanity 3/3 PASS; aqueous gamma-infinity median 36 % | InChIKey present, formal charge 0 |
| CALPHAD | `mcp/tools_server.py` | 3 TDB outside repo (Al 289,410 B, Fe 377,766 B, Ni 389,379 B; ODbL+DbCL) | Al 933.49 K vs 933.47; Al-Cu liquidus <= 8 K | element and phase must exist in the TDB |
| Hansen HSP | `mcp/tools_server.py` | `chemicals 1.5.2` CASRN lookup (entry count not recorded -> P0) | water/toluene/hexane match literature | CASRN must exist; mixtures (petrolatum) do not |
| Wax melting | `tools/wax_melting.py` | chemicals Tm/Hfus | pure C20/C28 hit their Tm | ideal solution only (YELLOW) |

Surfaces that exist as code: `mcp/tools_server.py` (CALPHAD + Hansen + UNIFAC),
`mcp/rdkit_tool.py`, `mcp/esol.py`, `mcp/cosmosac_pubchemqc.py`, the `/kj`
command (`C:\Users\pc\.config\opencode\commands\kj.md`), `AGENTS.md` routing
table and answer format.

**Correction found while writing this plan (2026-10-26 19:5x):** the MCP servers
are **not registered** in `C:\Users\pc\.config\opencode\opencode.jsonc`. That
file lists 16 servers and none of them is a kuro-jikken server; there is no
project-level `.opencode` folder in the repository either. So today opencode can
only reach these engines through shell commands, which is exactly the fragile
path this plan is meant to remove. A previous DEVAM block (232) recorded "MCP
kaydi (2 sunucu, handshake OK)" - that registration is gone or never persisted
and must be redone and verified (P0.5).

Missing: **registered MCP surface**, **one entry point**, **one gate layer**,
**one data manifest**, **one ledger**, **one golden test set**. Today every tool
carries its own ad-hoc note.

## 3. Architecture (layers, each replaceable)

```
sentence
  L0 normalise   text -> {substance ids, composition, conditions, unit}
  L1 intent      sentence -> capability id (fixed table; LLM may only fill JSON)
  L2 plan        capability -> ordered steps: engine + dataset + gate + unit
  L3 gate        per-engine applicability check -> PASS / YELLOW / RED + reason
  L4 compute     existing MCP tools (no new numerics in the router)
  L5 answer      value + unit + method + error + limits + reproduce + provenance
  L6 ledger      append-only JSONL: request, plan, gates, result, commit
```

Design rules:

1. **Numbers only from L4.** The router never does arithmetic.
2. **Gate before compute.** No gate record -> no answer.
3. **YELLOW and RED are first-class outputs**, not failures of the assistant.
4. **Every plan is replayable** offline from the ledger.
5. **One question max** when the request is ambiguous (CLARIFY), never a guess.

## 4. L0: normalisation (the part most projects skip)

| Input form | Resolver | Offline? | Failure |
|---|---|---|---|
| SMILES / InChI / InChIKey | RDKit | yes | REFUSE "structure does not parse" |
| CAS number | `chemicals` tables, PubChemPy | partial | REFUSE "CAS not found in any table" |
| IUPAC name | OPSIN (EBI web API) | no | REFUSE "name not resolvable offline" |
| trivial name ("vazelin", "aspirin") | PubChemPy synonym search -> InChIKey | no | CLARIFY one question |
| alloy composition ("Al-2Cu") | regex -> mole/weight percent + element list | yes | CLARIFY at% vs wt% |
| condition ("600 C", "1 atm") | Pint -> K, Pa | yes | CLARIFY default assumptions |

Rules: keep the resolved identifier next to the user's words; never silently
pick one of several matches; record resolver + version + timestamp in the ledger.

## 5. L1: intent -> capability (fixed table, no LLM freedom)

| Capability id | Triggers (TR/EN) | Engine chain | Verdict class today |
|---|---|---|---|
| `solubility.aqueous` | çözünür, solubility, logS | ESOL + domain gate | number (GREEN in domain, YELLOW out) |
| `mixture.gamma` | uyum, karışır, ayrışır, activity, gamma | UNIFAC -> cOSMO-SAC cross-check -> HSP ranking | number + ranking (YELLOW) |
| `mixture.wax` | wax, mum, erime aralığı | wax_melting (ideal) | range (YELLOW) |
| `alloy.phase` | alaşım, erir mi, liquidus, solidus, TDB | pycalphad + TDB | number (GREEN if element/phase present) |
| `molecule.identity` | MW, formül, halka, HBD/HBA | RDKit | number (GREEN) |
| `biology.binding` | bağlanır mı, docking, hedef, Kd | none | RED |
| `biology.toxicity` | toksik, ADMET, LD50, kanserojen | none | RED |
| `product.performance` | TEWL, his, occlusivity, emülsiyon kararlılığı | none | RED |
| `vle.azeotrope` | azeotrop, buhar basıncı, kaynama | none validated yet | RED until a VLE gate exists |

`AGENTS.md` keeps the human-readable version of this table; the code must read
the same table from one source (`data/capabilities.json`), so they cannot drift.

## 6. L2/L3: the gate catalogue (exact checks)

| Gate | Check | On fail |
|---|---|---|
| `gate.esol` | neutral, one component, no metal, no P, MW <= 500 | YELLOW with 5-log error bar, or REFUSE for salts/metals |
| `gate.unifac` | every subgroup name known, every main-group pair present | REFUSE (implemented today) |
| `gate.cosmo` | InChIKey in sigma index, charge 0 | REFUSE "molecule outside PubChemQC coverage" |
| `gate.calphad` | elements in TDB, phases exist, T inside assessed range | REFUSE "no TDB covers this system" |
| `gate.hsp` | CASRN in table, single molecule | REFUSE for mixtures (petrolatum) |
| `gate.wax` | all components have Tm and Hfus | REFUSE |
| `gate.structure` | SMILES parses, single fragment | REFUSE |

Each gate returns `{pass, verdict, reason, evidence}` and is unit-tested with at
least one known-bad and one known-good example (the UNIFAC gate already is).

## 7. L5: the answer contract (one shape, always)

```json
{
  "value": 926.4,
  "unit": "K",
  "method": "pycalphad 0.11.2 + mc_al_v2.032 (liquidus, x_Cu=0.01)",
  "error": {"kind": "bracket", "lower": 925.0, "upper": 927.0},
  "limits": ["binary Al-Cu only", "no oxidation, no creep", "TDB is ODbL, outside repo"],
  "verdict": "GREEN",
  "provenance": {"dataset": "mc_al_v2.032", "sha256": "BBA064BB...", "engine": "pycalphad 0.11.2"},
  "reproduce": "python tools/alloy_liquidus.py",
  "does_not_say": "that the alloy is strong, corrosion resistant or weldable"
}
```

Refusal shape keeps the same fields with `value: null`, `verdict: "RED"`,
`reason`, and the closest capability that *could* help.

## 8. Failure taxonomy (fixed sentences, no improvisation)

| Class | User-facing sentence (TR) |
|---|---|
| no engine | "Bunu hesaplayan dogrulanmis bir motorumuz yok; sayi uydurmuyorum." |
| no data | "Bu madde/veri seti elimizde yok; en yakin kapsam: ..." |
| out of domain | "Motor var ama bu molekul onun kapsami disinda (sebep: ...)." |
| missing parameters | "Grup etkilesim parametresi tabloda yok; hesap yapilmiyor." |
| ambiguous name | "Iki farkli madde buldum: A / B. Hangisi?" (tek soru) |
| unit mismatch | "Birim belirsiz (wt% mi at% mi?). Hangisi?" (tek soru) |
| model != measurement | "Bu bir tahmin; olcum degil. Hata cubugu: ..." |

## 9. L6: ledger and regression

- `runs/router/YYYYMMDD.jsonl`, append-only, one line per request:
  `{ts, session, request, resolved_ids, capability, plan, gates, answer, commit}`.
- `kj_ask --replay <id>` re-runs the same plan offline and must reproduce the
  same number and the same verdict.
- The golden set (section 10) runs in CI as ordinary pytest cases.

## 10. Golden set (acceptance benchmark, 20 requests)

Each row is a test: exact expected class, and for numbers a tolerance.

| # | Request | Expected |
|---|---|---|
| 1 | "etanol suda ne kadar cozunur" | NUMBER (ESOL, in domain) |
| 2 | "aseton suda ne kadar cozunur" | NUMBER (ESOL, in domain) |
| 3 | "sofra tuzu suda ne kadar cozunur" | REFUSE (salt, out of domain) |
| 4 | "vazelin bu kremle uyumlu mu" | REFUSE (petrolatum not in HSP) |
| 5 | "mineral yagi gliserinle karisir mi" | RANKING (HSP/UNIFAC, YELLOW) |
| 6 | "Al-2Cu alasimi 600 C'de erir mi" | NUMBER (CALPHAD, GREEN) |
| 7 | "Mg alasimi 700 C'ye dayanir mi" | REFUSE (no Mg TDB) |
| 8 | "bu molekulun MW'si kac" | NUMBER (RDKit) |
| 9 | "etanol/su azeotrop noktasi" | REFUSE (no VLE gate yet) |
| 10 | "bu ilac toksik mi" | RED (no tox engine) |
| 11 | "bu protein hedefe baglanir mi" | RED (no docking) |
| 12 | "mum 40 C'de erir mi" | RANGE (wax model, YELLOW) |
| 13 | "etanolun suda gamma-infinity'si" | NUMBER (UNIFAC, validated) |
| 14 | "asetonun suda gamma-infinity'si cOSMO ile" | NUMBER (cOSMO gate PASS) |
| 15 | "TDB'de olmayan bir elementle alasim" | REFUSE (gate.calphad) |
| 16 | "petrolatumun Hansen parametreleri" | REFUSE (mixture) |
| 17 | "bu SMILES gecerli mi" | BOOLEAN (RDKit) |
| 18 | "celik 500 C'de oksitlenir mi" | RED (no oxidation model) |
| 19 | "emulsiyon kararli mi" | RED (no engine) |
| 20 | "bu molekulun logP'si" | NUMBER (RDKit Crippen) |

Pass criterion: 20/20 correct class; every NUMBER reproducible by its command;
zero numbers produced without a gate record.

## 11. Build plan (phases, each shippable and tested)

| Phase | Work | Deliverable | Test | Effort |
|---|---|---|---|---|
| **P0** | data manifest + inventory doc | `data/manifest.json`, `docs/DATA_INVENTORY.md` | hashes/paths/licences validate; unknown dataset rejected by tests | 0.5 day |
| **P0.5** | register the MCP servers again | entries in `opencode.jsonc` (2 servers or 1 unified) + `/kj` smoke | after restart the tool list shows `unifac_gamma`, `alloy_melting_point`, `esol_*`; one live call returns a value | 0.25 day |
| **P1** | capability table + router skeleton | `mcp/router.py` + `kj_ask` (dry: plan only) + `data/capabilities.json` | golden set rows 1-20 return the right **class** (no numbers yet) | 1 day |
| **P2** | gate layer | `mcp/gates.py`, one function per gate, wired into router | known-good + known-bad per gate; UNIFAC/ESOL gates reused | 1 day |
| **P3** | answer contract | builder + Pint unit checks + provenance block | every golden NUMBER matches the schema; bad unit rejected | 0.5 day |
| **P4** | ledger + replay | `runs/router/*.jsonl`, `kj_ask --replay` | replay reproduces value and verdict bit-for-bit | 0.5 day |
| **P5** | optional engines | VLE/azeotrope (thermo + gate), biology gateway (only with licence + validation), OPTIMADE reader | new golden rows must be added first | after P4 |

Sub-phases added while executing the plan (2026-10-26). The v1 table above is
left as written; this table is the record of the extension:

| Sub-phase | Work | Deliverable | Evidence | Status |
|---|---|---|---|---|
| **P3.5a** | multi-gate dispatch | `router.gate_payloads` + `router.aggregate_gates`; extra `gate.hsp` for mixtures with a CAS | `5badce6`, DEVAM 246, suite 379 | done |
| **P3.5b** | identity resolver | `mcp/resolver.py` (CAS / SMILES / TR names / mixtures, explicit ambiguity) | `13e3a3e`, DEVAM 247, suite 391 | done |
| **P5a** | engine adapters + one call | `mcp/engines.py`, `mcp/pipeline.py`, `tools/ask.py` | `165acc4`, DEVAM 249, suite 412 | done |
| **P5b** | replay with real compute | `ledger.same_value` (1e-9/1e-12), `replay_router.py --compute` | `041ebf8`, DEVAM 250, suite 417 | done |
| **P5c** | numeric golden set | `tools/tests/test_golden_numbers.py` (20 rows: 6 numbers + 14 refusals) | `59b977a`, DEVAM 251, suite 440 | done |
| **P5d** | MCP surface | `kj_ask(request, payload, plan_only)`, `kj_replay(entry_id, recompute)` | `64acef0`, DEVAM 252, suite 444, stdio 9 tools | done |

Order is deliberate: manifest -> live MCP -> router -> gates -> contract ->
ledger. Building engines before P2 repeats today's problem (nice tools, no
single door), and skipping P0.5 keeps the door locked.

## 12. Non-goals (explicit)

- No LLM arithmetic, no free-form "the model estimates 5.2".
- No automatic scraping or dataset download without a licence entry.
- No biology binding/toxicity claim without a validated engine and a licence.
- No "performance" claims (occlusivity, TEWL, strength, durability) from any of
  these models.
- No new engine added without a known-value gate and a doc entry.

## 13. Risks

| Risk | Mitigation |
|---|---|
| router becomes a second chatbot | L1 restricted to a fixed capability table + JSON schema |
| gate drift between doc and code | one source: `data/capabilities.json`, docs generated/checked |
| golden set overfits to 20 examples | add rows whenever a real request fails; keep failures in the set |
| user over-trusts YELLOW numbers | verdict label is part of the answer object, not a footnote |
| data licences | manifest requires licence field; repo stays MIT-clean |

## 14. Next step

P0 + P0.5 in one session: data manifest, capability table, the two MCP servers
registered again and verified with one live call. Then P1's router skeleton
(plan only, no compute) and the 20-row golden classifier test. Nothing numeric
is produced by the router until gates (P2) exist, so there is no window where a
number can be returned without a gate record.
