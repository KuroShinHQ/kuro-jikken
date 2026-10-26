# Deviations and transparency log

Prereg: `prereg/llm_modes_plan_v1.md` (SHA-256 `EE039AC6…B1525`, registered as OSF `8pbnu`).
Any deviation is dated here; primary analyses stay as registered.

## 2026-10-26 — harness settings fixed before Freeze 2

1. **Thinking disabled at the template level.** `chat_template_kwargs =
   {"enable_thinking": false}`. Reason: with thinking on, every request hit the
   1024-token cap without producing a JSON answer (two measured items: 265 s and
   253 s, 3,072 completion tokens, `answered=False`); `reasoning_effort=low`
   still cost 26 s/item. No scoring rule, tolerance, ID list or property
   definition was changed. Recorded in `prereg/freeze2_candidate.md`.
2. **Prompt caching enabled** (`cache_prompt: true`). Only recomputation is
   skipped; temperature is 0, so outputs are unchanged. Mode B went from a
   33.4 s median to 7.5 s on two probe items.
3. **Debug pilot used 5 of the 50 pilot molecules** (105 items), on the author's
   instruction to shrink the debugging run. The pilot set remains 50 molecules;
   no pilot number is reported as a result.
4. **Advanced SystemCare left running** by the author's decision, after a
   read-only measurement: 0.000 s CPU per process over 10 s; no TCP or UDP
   endpoint in 10 samples over 20 s. Timing numbers carry this environment note.

## 2026-10-26 — environment changes (reversible)

5. **WSL systemd units masked** before benchmarking, so no LLM server starts by
   itself. Units: `llama-server.service`, `openclaw.service`, `ollama.service`
   (renamed to `*.masked_20261026` and masked with `/dev/null`), plus user units
   `kuroshin-llama.service`, `openclaw-gateway.service` (renamed only).
   Undo (inside WSL, as root):
   `systemctl unmask llama-server openclaw ollama` then
   `cd /etc/systemd/system && mv llama-server.service.masked_20261026 llama-server.service`
   (same for `openclaw`, `ollama`), and in `/root/.config/systemd/user` rename the
   two `*.masked_20261026` files back.
6. **WSL build 10288 was compiled from source** in a separate worktree
   (`/root/kuroshin/engines/llama10288`, commit `360e1349f`, CUDA 12.6). The
   existing WSL install was not modified. It was slower than Windows (1.7x), so
   Windows is used for the run.
7. **Two aborted speed-test attempts** (thinking on, then an interrupted run)
   remain in `runs/` as raw evidence. Nothing under `runs/` was edited or
   deleted.

## 2026-10-26 — unchanged

- Prompts were not changed after the pilot (`bench/prompts/*` hashes in Freeze 2).
- Scoring, tolerances, property definitions and the 250 ID lists are unchanged
  since their commits (`8967d06`, `b2b52b3`).
- No confirmatory run has been started.

