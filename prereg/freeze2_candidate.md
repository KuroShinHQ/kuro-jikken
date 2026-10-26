# Freeze 2 candidate — LLM modes A/B/C (2026-10-26)

**Status: candidate. NOT registered. No confirmatory run started.**
All numbers below are measured; only the runtime estimate is derived.

## 1. Model and runtime

| item | value |
|---|---|
| Model | `Hermes3.6-35B-A3B-Uncensored-Genesis-MTP-APEX-Compact.gguf` |
| Model bytes | 18,339,420,608 |
| Model SHA-256 | `A60C9CA376578AC98FC419D12CD1FAD4D47C1CFEC1BBE75A162F6BBB86E554B2` |
| Template | `qwen-fixed-chat-template.jinja` |
| Template SHA-256 | `E57684BAE4156211A55473C5A63BE976A405A37AB5BE5AE0E5ABF1DF5349C4B2` |
| Server | Windows `llama-server.exe`, build **10288 (360e1349f)**, Clang 20.1.8 |
| Binary path | `C:\KuroshinHQ\kuroshin-kage\apps\llama\win\pkg\llama-server.exe` |
| `llama-server.exe` SHA-256 | `029D2FF8A82149C9048893512368A2297DB7FDBEE748000DB1EE1CDB334E9B0F` |
| `llama-server-impl.dll` SHA-256 | `E8F3F45C742FF3B59E781563277D679D2D16562DD7E1DEDD3052FDA45BEA8102` |
| Endpoint | `http://127.0.0.1:8099` only (8080/8081 refused) |
| Draft model | **disabled** (no `-md`; `dflash-draft-qwen35-bf16.gguf.disabled` never passed) |

## 2. Generation settings

| parameter | value |
|---|---|
| context | `-c 8192` (`n_slots = 4`, `kv_unified = true`) |
| GPU layers | `-ngl 99` |
| flash attention | `-fa on` |
| KV cache | `-ctk q8_0 -ctv q8_0` |
| threads | `-t 8 --threads-batch 8` |
| temperature | **0** |
| seed | **20261026** |
| max tokens | **1024** |
| chat template kwargs | `{"enable_thinking": false}` |
| prompt caching | `cache_prompt: true` (no effect at temperature 0) |
| tool budget | 5 calls per question, shared with the C retry |
| scoring | `bench/score.py`, deterministic, unchanged since `8967d06` |

## 3. Prompt files (SHA-256)

| file | SHA-256 |
|---|---|
| `bench/prompts/mode_a.txt` | `007a21c5650585e090ad78d80e960d2fc674be3ea4e558c1dae36b4b1d4db2ab` |
| `bench/prompts/mode_b.txt` | `6392396ff1732ce3eda9e0ae6a31ff3fe6e017a9d10409f6b2f12cdef9b70e3e` |
| `bench/prompts/mode_c.txt` | `173c1aa643c3159e9f8b9ca3fb15aadf4754be9241b826193807d7153ae99d7d` |
| `bench/prompts/question.txt` | `840329c7254bcda12f9ac720b5b99db8be1e13caaa0575cfa9bc9680180da228` |

The prompt files were not changed after the pilot; they are frozen by these hashes.

## 4. Molecule ID lists

Committed **before any model call** (`b2b52b3`, 2026-10-26 10:38:47 +0300).

| file | SHA-256 |
|---|---|
| `bench/data/ids_pilot.txt` (50) | `0e8c9f3e0f7100978ac60b8a98c832b327e443dc6448c9203e42d9eb7d9bc523` |
| `bench/data/ids_confirmatory.txt` (200) | `f5b8a2fe92e83ce89156fae5ac4672fff7048c94d0ca019638de43fe7d1adb6f` |
| `bench/data/ids_all.csv` (250) | `c7e70125248edae67b91218963035824a491feec63f5d444b570adf88055c4e9` |

Selection: AqSolDB 9.982 rows -> 7.542 in-domain -> `random.Random(20261026).sample(sorted_by_inchikey, 250)`.
First 50 = pilot, next 200 = confirmatory.

## 5. Pilot (debugging only — NOT a result; do not cite these numbers)

Run `20261026T081319Z_pilot` (5 molecules x 7 properties x 3 modes = 105 items).
These figures are for debugging only. **They are not a result**, not a preprint
number, and were not used for any Freeze 2 choice.

| mode | correct | mean s/item | tool calls/item | verification failures |
|---|---|---|---|---|
| A | 18/35 | 2.712 | 0.0 | 0 |
| B | 35/35 | 11.482 | 1.0 | 0 |
| C | 35/35 | 13.921 | 1.0 | 0 |

No tool-format failure, no unknown tool, no budget exhaustion, no retry.

## 6. Platform speed comparison (10 pilot questions, prompt cache on)

| platform | A median | A tok/s | B median | B tok/s | model load |
|---|---|---|---|---|---|
| **Windows** 10288 | **3.208 s** | 3.34 | **9.788 s** | 4.83 | < 1 min (page cache) |
| WSL 10288 | 5.396 s | 1.85 | 16.163 s | 2.96 | ~13 min |

**Chosen: Windows.** It is ~1.7x faster in both modes; the model lives on NTFS,
so WSL pays the 9p `/mnt/c` cost on every page fault, and the WSL load took ~13 minutes.

## 7. Runtime estimate for the confirmatory run (200 x 7 x 3 = 4,200 items)

From the pilot means: per molecule = 7 x (2.712 + 11.482 + 13.921) = **196.8 s**.
200 molecules = **39,360 s ≈ 10.9 h**; +10% overhead ≈ **12 h**.

**48-hour fallback (prereg section 8): NOT triggered** (12 h < 48 h). N stays 200.

## 8. Decision basis

Throughput only. Pilot accuracy (A 18/35) was not used to choose the platform,
the context size, the sampling parameters or N.

## 9. Provenance

| item | value |
|---|---|
| Harness commit at candidate time | `a94e36b` |
| `bench/score.py` SHA-256 | `31DD71265919336CE4ADC299846C33B8A43BB181250F615CAEC7A5BC065B65FF` |
| Raw pilot log | `runs/20261026T081319Z_pilot.jsonl` |
| Raw platform logs | `runs/20261026T085727Z_speed_wsl_10288.jsonl`, `runs/20261026T090242Z_speed_windows_10288_cache.jsonl` |
| Environment note | Advanced SystemCare was running (0.000 s CPU / no sockets measured); see `DEVIATIONS.md` |




