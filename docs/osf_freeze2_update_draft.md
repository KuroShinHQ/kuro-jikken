# OSF Update draft — Freeze 2 (registration 8pbnu)

Status: draft for a dated OSF *Update* on https://osf.io/8pbnu/.
Not sent. Author's approval is required before sending.
Date written: 2026-10-26.

## Justification (for the OSF field)

Dated Freeze 2 amendment before the confirmatory run. It fixes the final prompts,
model artefacts, platform and sampling parameters, and records the harness
decisions and environment findings that were not in the registered plan:
thinking is disabled, prompt caching is enabled and the Windows build is CPU
only.

No registered line was changed. The plan text, the scoring rules, the tolerances,
the seven property definitions and the 250 molecule IDs are untouched. Prompts were
not changed after the debug pilot and are frozen by the hashes below.

### 1. Thinking is disabled

`chat_template_kwargs = {"enable_thinking": false}` at request level. Mode A is
therefore a **non-thinking mode**: the model answers from its own knowledge without
a chain of thought. This is a harness decision, not part of the original plan, and
it was chosen **for throughput only**, not from any accuracy observation:

- thinking on (template default): two pilot items took 265 s and 253 s, spent
  3,072 completion tokens, and produced **no JSON answer** (truncated at the cap);
- `reasoning_effort: low`: 26 s per item, still too slow for 4,200 items;
- thinking off: valid JSON, stable throughput, confirmatory run ≈ 12 h.

The reported difference between modes must be read with this in mind: mode A is
the non-thinking condition. This will be repeated in the results report.

### 2. N = 200 confirmatory (no fallback)

Measured pilot throughput (5 molecules x 7 properties x 3 modes, 105 items):
A 2.712 s/item, B 11.482 s/item, C 13.921 s/item. Per molecule = 196.8 s;
200 molecules = 39,360 s ≈ 10.9 h, plus ~10% overhead ≈ **12 h**.
The 48-hour fallback in section 8 is **not triggered**; N stays 200.
The estimate uses throughput only; pilot accuracy was not used.

Of the 50 pilot IDs only the first 5 were run; the other 45 were not run and
are disjoint from the confirmatory IDs.

### 3. Windows llama-server build 10288 (CPU only)

Platform: Windows `llama-server.exe` build **10288 (360e1349f)**, Clang 20.1.8,
`C:\KuroshinHQ\kuroshin-kage\apps\llama\win\pkg\llama-server.exe`.
This build has no CUDA backend, so inference runs on the CPU with 8 threads.
A WSL build of the same commit was measured for comparison and was ~1.7x slower
(model on NTFS, 9p `/mnt/c` cost); it was not chosen.

### 4. Deviations and environment

Everything in `DEVIATIONS.md` dated 2026-10-26 applies to the pilot numbers:

- **Advanced SystemCare left running** by the author's decision, after a
  read-only measurement: 0.000 s CPU per process over 10 s; no TCP or UDP
  endpoint in 10 samples over 20 s. Pilot timings carry this environment note.
- **WSL build 10288 was compiled from source** in a separate worktree
  (`/root/kuroshin/engines/llama10288`, commit `360e1349f`, CUDA 12.6); the
  existing WSL install was not modified. Whether the WSL build used the GPU was
  not measured, and it does not affect the run, which uses the Windows CPU-only
  build. It was 1.7x slower than Windows and was not chosen.
- **WSL systemd units masked** before benchmarking so that no LLM server starts
  by itself: `llama-server`, `openclaw`, `ollama` (renamed `*.masked_20261026`
  and masked with `/dev/null`), plus user units `kuroshin-llama` and
  `openclaw-gateway` (renamed). Exact undo commands are in `DEVIATIONS.md`.
- **Thinking disabled** (`enable_thinking: false`); see section 1. This is a
  harness decision that is not in the registered plan.
- **The Windows build is CPU only (finding, not a result).** -ngl 99 was passed
  but this binary has no CUDA backend; inference ran on CPU (8 threads); the
  ~12 h estimate was measured on this same CPU setup. Established before
  Freeze 2: the package directory holds only `ggml-cpu-*.dll` (no
  `ggml-cuda.dll`, no `cudart64_*` or `cublas64_*`), and
  `llama-server-impl.dll` contains 0 occurrences of `ggml_cuda`, `cublas`,
  `CUDA0` and `offloading`.
- **Prompt caching enabled** (`cache_prompt: true`). Only recomputation is
  skipped; temperature is 0 and outputs are unchanged. Verified on 35 pilot
  items (5 molecules x 7 properties, mode B): answers and tool traces were
  byte-identical with cache on and off
  (`runs/20261026T094129Z_cachecheck_summary.json`).
- **Debug pilot used 5 of the 50 pilot molecules** (105 items) on the author's
  instruction to shrink the debugging run; the pilot set stays 50 molecules.
- **Two aborted speed-test attempts** (thinking on, then an interrupted run)
  remain in `runs/` as raw evidence. Nothing under `runs/` was edited or deleted.

## Fixed artefacts (hashes)

| item | SHA-256 |
|---|---|
| model `Hermes3.6-35B-A3B-Uncensored-Genesis-MTP-APEX-Compact.gguf` (18,339,420,608 B) | `A60C9CA376578AC98FC419D12CD1FAD4D47C1CFEC1BBE75A162F6BBB86E554B2` |
| template `qwen-fixed-chat-template.jinja` | `E57684BAE4156211A55473C5A63BE976A405A37AB5BE5AE0E5ABF1DF5349C4B2` |
| `llama-server.exe` | `029D2FF8A82149C9048893512368A2297DB7FDBEE748000DB1EE1CDB334E9B0F` |
| `llama-server-impl.dll` | `E8F3F45C742FF3B59E781563277D679D2D16562DD7E1DEDD3052FDA45BEA8102` |
| `prompts/mode_a.txt` | `007a21c5650585e090ad78d80e960d2fc674be3ea4e558c1dae36b4b1d4db2ab` |
| `prompts/mode_b.txt` | `6392396ff1732ce3eda9e0ae6a31ff3fe6e017a9d10409f6b2f12cdef9b70e3e` |
| `prompts/mode_c.txt` | `173c1aa643c3159e9f8b9ca3fb15aadf4754be9241b826193807d7153ae99d7d` |
| `prompts/question.txt` | `840329c7254bcda12f9ac720b5b99db8be1e13caaa0575cfa9bc9680180da228` |
| `ids_pilot.txt` (50 IDs; first 5 run in the debug pilot) | `0e8c9f3e0f7100978ac60b8a98c832b327e443dc6448c9203e42d9eb7d9bc523` |
| `ids_confirmatory.txt` (200) | `f5b8a2fe92e83ce89156fae5ac4672fff7048c94d0ca019638de43fe7d1adb6f` |
| `ids_all.csv` (250) | `c7e70125248edae67b91218963035824a491feec63f5d444b570adf88055c4e9` |

Settings: context 8192, `-ngl 99` passed but ignored (no CUDA backend; CPU only,
8 threads), `-fa on`, KV `q8_0`, temperature 0,
seed 20261026, max tokens 1024, prompt caching on, draft model disabled,
endpoint 127.0.0.1:8099 only.

## Author approval

The author approves the four decisions above (thinking disabled, N = 200, Windows
llama-server build 10288, ~12 h estimate), including inference on the CPU only,
on 2026-10-28 (confirmation word given in the session: ONAY).

## What this update does not do

- It does not change the hypotheses, the primary analysis, the scoring rules, the
  property definitions or the 250 molecule IDs.
- It does not start the confirmatory run and reports no result.
- The pilot figures in the repository are **debugging only, NOT a result**.

## Summary line to append (if OSF requires a field change)

Freeze 2 (2026-10-26): thinking disabled (mode A is non-thinking); model and
template hashes fixed; Windows llama-server 10288; context 8192; temperature 0;
seed 20261026; max tokens 1024; N = 200; confirmatory run ≈ 12 h; 48-hour
fallback not triggered.


