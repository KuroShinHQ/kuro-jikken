---
name: lab
description: Build a lab page for kuro-jikken from a gated Python engine - one interactive 3D HTML page (three.js via the vendored kit), a photoreal piece of laboratory apparatus, a number that is a ledger entry rather than an in-page solver, a provenance strip under every number, and a break state that shows the fixed refusal sentence instead of inventing a value. Use when someone asks to visualise, explain or show an experiment or property (melting point, liquidus, solubility, activity coefficient, Hansen distance) for kuro-jikken, wants a lab scene, a cutaway, an exploded view or a film of one, or asks "make a page/lab out of this engine". Not for generic dashboards or charts.
---

# lab - kuro-jikken

One engine call becomes one page you can break. The page is the argument: the object on
screen is real apparatus, the number on screen is traceable, and the edge of the domain is
visible instead of hidden.

## The bar (nothing ships below this)

1. **Every number has a lane**: `anchor` (a ledger entry), `surrogate` (a declared
   approximation validated against the engine) or `refusal` (no number at all).
2. **Provenance under every number**: engine, dataset, gate verdict, error bar, ledger id,
   bake time, git head. A number without a strip is unfinished.
3. **Break it works**: pushing outside the domain produces the gate's fixed sentence and an
   em dash, never a plausible-looking number.
4. **It opens from disk**: one self contained file (`scripts/inline.mjs`), three.js from the
   pinned CDN, no bundler, no server.
5. **Readable at 1x, still rewarding at 4x**: a named part list, no bare slab, no empty corner.
6. **`node scripts/shot.mjs` prints fps >= 30** for the interactive page and the audit passes
   (`python scripts/lab_audit.py labs/<page>.html` exit 0). A green claim without these two is
   not evidence.

## The three lanes of a number

| Lane | Source | Shown as | Allowed when |
|---|---|---|---|
| **anchor** | `bake.py` -> `mcp/pipeline.ask` -> ledger | the number + ledger id | the gate returned PASS or YELLOW |
| **surrogate** | a pure module built from anchors (`labs/<name>_model.mjs`) | `~` + the declared tolerance | validated against the engine at anchors **and** midpoints |
| **refusal** | `mcp/answer.refusal` (7 fixed sentences) | em dash + sentence | gate RED, UNKNOWN, CLARIFY or no engine |

Rules that keep the lanes honest:

- The hero/answer number is **always an anchor**. A surrogate never replaces it.
- A surrogate is only a *depiction* of measured anchors. It may interpolate, never extrapolate
  past the baked range, and never run where the gate is RED.
- Declare the tolerance with a measurement, not a feeling (Al-Cu: 21 anchors, 20 midpoints,
  max 0.342 K against the engine's own 0.684 K bisection bracket -> tolerance 0.5 K).
- Physics copied from a paper into JS is forbidden; physics **derived from our own bake and
  re-checked against our own engine** is allowed. The difference is the audit, not the language.

## The ten steps

1. **Size it.** `Figure` = one mechanism, 40-80 parts, one HTML. `Hero` = a dense apparatus,
   80-150 parts. `Epic` = a whole line/plant; quote it, do not start it. Name the size before
   any geometry. A working page must open in the first hour.
2. **Truth first.** Find the engine, the gate and the dataset in `mcp/` + `data/manifest.json`.
   If there is no engine, stop: the page is a refusal, and say so (`biology.toxicity` today).
3. **Bake the anchors.** Never hand-write a number into the page.
   ```
   python .opencode/skills/lab/scripts/bake.py \
     --request "Al-{cu} wt% Cu alasimi erir mi" \
     --payload-file data/labs/alcu_payload.tpl.json \
     --sweep cu=0..10:21 --out data/labs/al_cu_liquidus.json --session lab
   ```
   `--payload-file` is mandatory on PowerShell (quote mangling) and is read as `utf-8-sig`.
4. **Parts list before geometry.** Write `labs/<name>_parts.md`: at least 40 named parts in five
   groups - base (plate, feet, screws, label plate, scale), structure (posts, rails, clamps),
   mechanism (crucible, susceptor, probe, coil), controls (knob, dial, toggle), subject (the one
   lit part: the melt, the sample, the drop). Every part sits on another part.
5. **Pick the apparatus.** The object must be the explanation: a crucible in a susceptor for a
   liquidus, a U-tube for a density, a flask in a bath for a solubility. Never a labelled box.
6. **Build the model module.** `labs/<name>_model.mjs`: anchors, ids, tolerances, `interp(x)`,
   `nearestAnchor(x)`. The page imports it; the page does not hold a second copy of the numbers.
7. **Build the page** with the kit (`Lab`, `MAT`, `GEO`): real metres, PBR materials, studio
   light, `cut`/`explode`/`xray`, `lab.hero`, `lab.slider`, `lab.how`, `lab.breakIt`.
8. **Provenance strip.** Appended under the hero in `.lab-side`, monospace, one line per field:
   engine, dataset, gate + bracket, ledger id, baked time + head.
9. **Break it.** `lab.breakIt({ run, reset })`: `run()` shows `REFUSAL.sentence` and the em dash;
   `reset()` restores the anchor for the current slider position. No number in the break state.
10. **Verify like a critic.** `shot.mjs` at 1x and 4x, read every PNG; `lab_audit.py` exit 0;
    `scripts/inline.mjs` for the single file; then film beats (L7) and the A4 sheet (L11).

## Review loop (do at least four rounds)

Whole view, cutaway with labels, exploded, two 4x close-ups of joints, then the break state.
Compare against real product photography of the apparatus in your memory: proportions, part
count, materials, how light falls. List what is wrong, fix it, render again. Stop when the list
is empty - not when the page merely runs.

## Commands

| What | Command |
|---|---|
| bake anchors | `python .opencode/skills/lab/scripts/bake.py ...` (above) |
| replay one anchor | `python tools/replay_router.py <ledger-id> --compute` |
| screenshot + fps | `node scripts/shot.mjs labs/<page>.html out/review.png` |
| single file | `node scripts/inline.mjs labs/<page>.html` |
| audit | `python scripts/lab_audit.py [--compute]` (exit 1 on drift) |
| generate model | `python scripts/gen_model.py [--check]` |
| A4 sheet (L11) | `node scripts/sheet.mjs labs/<sheet>.html data/labs/<name>.pdf` (prints `pages`) |
| film (L7) | `FFMPEG=<live2d ffmpeg> VENC=openh264 FPS=30 node scripts/record.mjs labs/<page>.html labs/<page>.mp4 --w 1920 --h 1080 --ss 1.5` |

**The film chain on this laptop (measured 2026-10-27, do not re-guess it):** there is no `ffmpeg`
on PATH, and Playwright's bundle (`ms-playwright\ffmpeg-1013`, n7.0.1) has **no h264 encoder**
(libvpx-vp9 only). Two builds are usable, and they are not interchangeable:

- `C:\Program Files\Live2D Cubism 5.0\tools\ffmpeg\ffmpeg.exe` (4.4.3) reads our PNG pipe and has
  `libopenh264` -> run with `VENC=openh264 VBITRATE=16M`. **This is what the Al-Cu film uses.**
- Wondershare 3.2.5 has libx264 but its `png_pipe`/`image2pipe` demuxer cannot size a frame from
  stdin ("Could not find codec parameters ... unspecified size"), so it cannot take the stream.

There is no `ffprobe` either: `pinkscan.mjs` now reads the rate from `FPS` (default 30) and stays
silent when the probe is missing. Headless Chromium defaults to SwiftShader (2 fps measured);
`scripts/lib/browser.mjs` forces ANGLE/D3D11 on Windows and gets the real GPU (61 fps).

## Files

```
.opencode/skills/lab/
  SKILL.md                  this file
  kit/lab-kit.js            vendored kit (MIT, AirsupHQ/machine-skill) + our hero fix
  kit/template.html
  scripts/bake.py           grid -> pipeline.ask -> JSON (anchors + ledger ids)
  scripts/gen_model.py      JSON -> labs/<name>_model.mjs (anchors are machine copied)
  scripts/lab_audit.py      the three-lane audit (anchors, surrogate tolerance, refusal purity)
  scripts/{shot,record,inline,pinkscan}.mjs
  scripts/sheet.mjs         A4 sheet -> PDF (+ PNG proof, prints the page count)
  labs/<name>.html          the page
  labs/<name>_model.mjs     pure surrogate module
  labs/<name>_parts.md      the part list
```

## Failure modes already seen (do not repeat)

- **Hand-copied constants drift.** The Al-Cu page carries its 21 values; an audit must compare
  them to the JSON. A generator is better than a copy.
- **The kit's build animation overwrites the hero.** Fixed upstream in `lab-kit.js`
  (`_heroPending`); do not set the hero before `lab.start()` and expect it to survive.
- **`file://` blocks module scripts.** A page with `<script src="../kit/lab-kit.js">` only works
  when served; `inline.mjs` is the deliverable, the served version is the working copy.
- **A measured 0 is not "no error".** 21 anchors with 20 midpoints is a tolerance, not a proof.
- **`slider.set()` does not fire `input`.** The kit's `set(v)` (what the film uses to drag a
  slider) writes the DOM value and calls the slider's own `onInput` option - it never dispatches
  an `input` event. A page that listens with `el.addEventListener('input')` shows a frozen hero
  while the knob moves: the Al-Cu still at 10.0 wt% still read 927.78 K (2.0 wt% number). Put the
  handler in `lab.slider({ onInput })`, and snap the readout to a stored anchor so no intermediate
  float is printed as a number.
