"""Generate a three.js procedure page from a gated ``kj-recipe/1`` document.

The page is a *depiction* of a procedure, not a solver:

* the JSON is embedded verbatim (``const R = {...}; // kj-recipe-json``), so the
  page cannot drift from the document the gate approved;
* the hero shows a temperature only when the step declares one, and says
  ``target`` or ``limit`` - never "measured";
* every step names its source id in the side panel;
* the break state is the procedure refusal sentence, not a plausible number.

    python tools/recipe_page.py --all
    python tools/recipe_page.py data/recipes/mint_lemon.json --check

Exit 1 when ``--check`` finds a stale page, or when a recipe fails the gate.
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

import recipe  # noqa: E402

DEFAULT_OUT = ROOT / ".opencode" / "skills" / "lab" / "labs"


TEMPLATE = r"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · kuro-jikken</title>
<meta name="description" content="__DESC__">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  /* the kit's title is sized for short machine names; a recipe title is longer */
  .lab-title { font-size: clamp(30px, 3.0vw, 56px) !important; }
  .lab-title i { font-size: 0.62em !important; line-height: 1.05 !important; }
  .lab-pills { opacity: 0.72; }
</style>
<script type="importmap">
{ "imports": {
  "three": "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js",
  "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"
} }
</script>
</head>
<body>
<script type="module" src="../kit/lab-kit.js"></script>
<script type="module">
const { THREE, Lab, MAT, GEO, clamp, fmt } = window.LabKit

// The whole recipe, copied by tools/recipe_page.py from the gated document.
// No number on this page is typed by hand: steps, temperatures and sources all
// come from this object, and `--check` fails when the page and the file differ.
const R = __RECIPE_JSON__; // kj-recipe-json
const TR = R.tr || {}
const N = R.steps.length

// ---------------------------------------------------------------- the lab
const lab = new Lab({
  prompt: TR.title || R.title,
  no: 1, title: __PAGE_TITLE__, sub: 'bir tarif, bir iddia degil',
  size: __SIZE__,
  view: { az: __AZ__, el: __EL__, dist: __DIST__, target: [0, 0.045, 0] },
  ground: -0.002,
  cut: { a: [0, 0, 1], b: [0, 1, 0], reach: 0.18 },
  pills: ['kj-recipe/1', R.id, `${R.sources.length} sources`],
})
// the kit's prompt is branded for machines; this page is the /kj procedure lane
lab.$('.lab-prompt b').textContent = '/kj'
// the standard audit hook: shot.mjs and the probes read window.__lab
window.__lab = lab

// ---------------------------------------------------------------- the parts
const P = []
function part(group, geo, mat, o) {
  const m = lab.mesh(geo, mat, o)
  m.name = o.name || m.name
  P.push({ group, name: o.name })
  return m
}

__SCENE__

const built = buildScene(lab, THREE, MAT, GEO, part)

// the active-step marker: one ring, moved to the station of the current step
const ring = lab.mesh(GEO.tube(__RING_R__, __RING_R__ - 0.005, 0.0022, 64), MAT.glow({ emissive: [1, 0.55, 0.12], emissiveIntensity: 1.6 }), {
  name: 'Active step ring', pos: [0, 0.004, 0],
})

// ---------------------------------------------------------------- the number
lab.hero({ label: 'Sicaklik / temperature', unit: '°C', max: 110, digits: 0 })

let current = 0
let stepState = 0
const side = lab.$('.lab-side')

// the presenter bubble: one simple line per step, bottom-left of the stage
const bubble = document.createElement('div')
bubble.style.cssText = 'position:fixed;left:5.2%;bottom:12%;max-width:24em;background:#fff;color:#1c1b19;border:1px solid rgba(0,0,0,.14);border-radius:14px;padding:12px 16px;font:500 14px/1.45 Inter,system-ui,sans-serif;box-shadow:0 10px 30px rgba(0,0,0,.10);z-index:5'
document.body.appendChild(bubble)
const mise = document.createElement('div')
mise.style.cssText = 'margin-top:0.9em;padding-top:0.65em;border-top:1px solid rgba(0,0,0,0.14);font:500 10px/1.6 "JetBrains Mono",monospace;color:#6f6c66;max-width:23em'
mise.textContent = 'masa / mise en place: ' + R.ingredients.map((g) => `${g.name} ${g.amount} ${g.unit}`).join(' · ')
side.appendChild(mise)

// the step text sits between the hero and the slider
const callout = document.createElement('div')
callout.style.cssText = [
  'margin-top:0.85em', 'padding-top:0.7em',
  'border-top:1px solid rgba(0,0,0,0.14)',
  'max-width:23em',
].join(';')
side.insertBefore(callout, lab.$('.lab-ctls'))

// the claim boundary is part of the interface, not a footnote
const boundary = document.createElement('div')
boundary.style.cssText = [
  'margin-top:0.9em', 'padding:0.55em 0.65em',
  'border-left:3px solid #b45309', 'background:rgba(180,83,9,0.07)',
  'font:500 11px/1.5 Inter,system-ui,sans-serif', 'color:#5b3a12',
  'max-width:23em',
].join(';')
side.insertBefore(boundary, lab.$('.lab-ctls'))

const prov = document.createElement('div')
prov.style.cssText = [
  'margin-top:1.0em', 'padding-top:0.65em',
  'border-top:1px solid rgba(0,0,0,0.14)',
  'font:500 10px/1.6 "JetBrains Mono",ui-monospace,monospace',
  'letter-spacing:0.01em', 'color:#6f6c66', 'max-width:23em',
].join(';')
side.appendChild(prov)

function show(i) {
  current = i
  const step = R.steps[i]
  const trStep = (TR.steps && TR.steps[i]) || step.action
  bubble.textContent = trStep
  const note = step.note ? `<div style="margin-top:0.35em;color:#7a766e;font-size:10.5px">${step.note}</div>` : ''
  callout.innerHTML = [
    `<div style="font:600 10px/1.4 "JetBrains Mono",monospace;letter-spacing:0.08em;color:#8a857c">STEP ${i + 1} / ${N}</div>`,
    `<div style="font:400 15px/1.35 "Instrument Serif",serif;margin-top:0.25em;color:#1c1b19">${trStep}</div>`,
    `<div style="font:500 10px/1.5 "JetBrains Mono",monospace;color:#6f6c66;margin-top:0.3em">kaynak / source: ${step.source}</div>`,
    note,
  ].join('')
  const station = built.stations[i] || [0, 0, 0]
  ring.position.set(station[0], 0.004, station[2])
  stepState = i
  built.onStep(i)
  if (step.temperature_c !== undefined) {
    lab.setHero(step.temperature_c, {
      state: step.temperature_role === 'limit' ? 'limit (cited)' : 'target setpoint',
      sub: `step ${i + 1} / ${N} · source ${step.source}`,
    })
  } else {
    lab.setHero(0, { state: 'no temperature in this step', sub: `step ${i + 1} / ${N} · source ${step.source}` })
    lab._hv.textContent = '\u2014'
    lab._hb.firstElementChild.style.width = '0%'
  }
  boundary.innerHTML = `<b>Sinir / boundary</b><br>${TR.claim_boundary || R.claim_boundary}`
  prov.innerHTML = [
    `<b style="color:#3d3a35">kj-recipe/1</b> · ${R.id}`,
    `procedure · targets, not measured · mcp/recipe.py`,
  ].join('<br>')
}

// test hook: shot.mjs can drive a step without touching the slider
window.__showStep = show

// the kit's assembly restores a queued hero after the build; enforce the dash
// for steps that have no temperature until the user moves the slider again
lab.onTick(() => {
  if (lab._building || lab.broken) return
  built.onStep(stepState)
  const step = R.steps[current]
  if (step.temperature_c === undefined) {
    lab._hv.textContent = '\u2014'
    lab._hb.firstElementChild.style.width = '0%'
  }
})

const stepSlider = lab.slider({
  id: 'step', label: 'Adim / step', min: 1, max: N, step: 1, value: 1, digits: 0,
  ends: ['1', String(N)], onInput(value) {
    if (lab.broken) lab.resetBreak()
    show(clamp(Math.round(Number(value)), 1, N) - 1)
  },
})

// ---------------------------------------------------------------- break it
const REFUSAL = {
  sentence: 'Bu bir tarif; hastaligi tedavi etmez, ilacin yerine gecmez. Sayi yok.',
  reason: 'procedure lane: no medical claim, no number',
}
lab.breakIt({
  label: R.kind === 'food' ? 'Ask it to cure the flu' : 'Ask it to fix a scratch',
  run() {
    lab.setHero(0, { state: 'refused', sub: REFUSAL.reason, bad: true })
    lab._hv.textContent = '\u2014'
    lab._hb.firstElementChild.style.width = '0%'
    callout.innerHTML = `<div style="font:600 10px/1.4 "JetBrains Mono",monospace;color:#8d2b22">REFUSED</div><div style="font:400 15px/1.35 "Instrument Serif",serif;margin-top:0.25em">${REFUSAL.sentence}</div>`
    boundary.innerHTML = `<b>Sinir / boundary</b><br>${TR.claim_boundary || R.claim_boundary}`
  },
  reset() { show(current) },
})

// ---------------------------------------------------------------- the text
const safety = (TR.safety || R.safety.map((s) => s.text)).map((t) => `<li>${t}</li>`).join('')
const dns = (TR.does_not_say || R.does_not_say).map((t) => `<li>${t}</li>`).join('')
const sources = R.sources.map((s) => `<li><code>${s.id}</code> — ${s.title} — <a href="${s.url}">${s.url}</a> (${s.accessed})</li>`).join('')
lab.how(
  `<b>Bu sayfa bir tarif, bir motor degil.</b> Sayilar hedef (setpoint) veya kaynakli `
  + `sinirdir (limit); hicbiri olcum degildir. Belge <code>mcp/recipe.py</code> kapisindan gecer: `
  + `her adim bir kaynak kimligi ya da acikca <code>design</code> tasir, tip iddiasi `
  + `<code>claim_boundary</code> disinda yasaktir. `
  + `<b>Kiril nokta:</b> "gribi tedavi etsin" dersen sayfa sayi uretmez; sabit ret cumlesini gosterir.`
  + `<div style="margin-top:0.7em"><b>Guvenlik</b><ul>${safety}</ul></div>`
  + `<div style="margin-top:0.5em"><b>Bu tarif ne soylemiyor</b><ul>${dns}</ul></div>`
  + `<div style="margin-top:0.5em"><b>Kaynaklar</b><ul>${sources}</ul></div>`,
  [
    'lane: procedure (kj-recipe/1) — no engine, no surrogate',
    'claim gate: cure/treat/prevent words only inside claim_boundary/does_not_say',
    'temperature_role: setpoint may be design; limit must cite a source',
  ],
)

show(0)
lab.start()

// ---------------------------------------------------------------- performance
lab.ao.enabled = false
lab.renderer.shadowMap.type = THREE.PCFSoftShadowMap
lab.scene.traverse((o) => {
  if (o.isLight && o.shadow) {
    o.shadow.mapSize.set(1024, 1024)
    o.shadow.map?.dispose()
    o.shadow.map = null
    o.shadow.camera.near = 5
    o.shadow.camera.far = 12
    o.shadow.camera.updateProjectionMatrix()
    o.shadow.bias = -0.0006
    o.shadow.normalBias = 0.035
  }
  if (o.material) o.material.needsUpdate = true
})
lab.renderer.shadowMap.needsUpdate = true
</script>
</body>
</html>
"""


SCENE_FOOD = r"""
function buildScene(lab, THREE, MAT, GEO, part) {
  // base ---------------------------------------------------------------- (4)
  part('base', GEO.rbox(0.44, 0.016, 0.30, 0.014), MAT.satin({ color: [0.19, 0.17, 0.15], roughness: 0.7 }), { name: 'Slate board', pos: [0, -0.008, 0] })
  part('base', GEO.disc(0.050, 0.004, 0.001, 48), MAT.satin({ color: [0.34, 0.28, 0.22], roughness: 0.6 }), { name: 'Mint saucer', pos: [-0.160, 0.002, 0.090] })
  part('base', GEO.disc(0.046, 0.004, 0.001, 48), MAT.satin({ color: [0.34, 0.28, 0.22], roughness: 0.6 }), { name: 'Lemon saucer', pos: [0.060, 0.002, 0.110] })
  part('base', GEO.disc(0.040, 0.004, 0.001, 48), MAT.satin({ color: [0.34, 0.28, 0.22], roughness: 0.6 }), { name: 'Mug coaster', pos: [0.145, 0.002, 0.010] })

  // the pot ------------------------------------------------------------- (6)
  const potX = -0.090
  part('mechanism', GEO.shell([[0.000, 0.002], [0.045, 0.002], [0.062, 0.012], [0.066, 0.086]], 0.003, 72), MAT.stainless(), { name: 'Saucepan wall', pos: [potX, 0, 0] })
  part('mechanism', GEO.disc(0.063, 0.002, 0.0006, 64), MAT.fluid({ color: [0.55, 0.75, 0.85], transparent: true, opacity: 0.55 }), { name: 'Water in the pot', pos: [potX, 0.068, 0] })
  part('mechanism', GEO.pipe([[potX - 0.064, 0.070, 0], [potX - 0.120, 0.094, 0], [potX - 0.168, 0.070, 0]], 0.0045, { seg: 32, radial: 10 }), MAT.steelDark(), { name: 'Pot handle' })
  part('mechanism', GEO.disc(0.068, 0.003, 0.0008, 64), MAT.stainless(), { name: 'Pot lid', pos: [potX, 0.090, 0] })
  part('mechanism', GEO.disc(0.010, 0.007, 0.002, 24), MAT.steelDark(), { name: 'Lid knob', pos: [potX, 0.096, 0] })
  part('mechanism', GEO.tube(0.070, 0.066, 0.004, 64), MAT.stainless(), { name: 'Pot rim', pos: [potX, 0.086, 0] })

  // steam --------------------------------------------------------------- (4)
  const steam = []
  for (const [k, x, z, r] of [[0, -0.020, 0.010, 0.009], [1, 0.018, -0.008, 0.011], [2, -0.006, -0.022, 0.008], [3, 0.028, 0.018, 0.010], [4, 0.004, 0.000, 0.013], [5, -0.030, -0.004, 0.007]]) {
    const m = MAT.glow({ emissive: [0.85, 0.90, 1], emissiveIntensity: 0.26, transparent: true, opacity: 0.10 })
    steam.push(part('subject', new THREE.SphereGeometry(r, 12, 8), m, {
      name: `Steam ${k + 1}`, pos: [potX + x, 0.105 + k * 0.018, z], scale: [1, 1.5, 1],
    }))
  }

  // the mug ------------------------------------------------------------- (5)
  const mugX = 0.145, mugZ = 0.010
  part('mechanism', GEO.tube(0.034, 0.030, 0.086, 48), MAT.glass({ roughness: 0.04 }), { name: 'Glass mug', pos: [mugX, 0.043, mugZ] })
  part('mechanism', GEO.disc(0.030, 0.002, 0.0005, 48), MAT.glass({ roughness: 0.04 }), { name: 'Mug floor', pos: [mugX, 0.003, mugZ] })
  const tea = part('subject', GEO.disc(0.030, 0.002, 0.0005, 48), MAT.fluid({ color: [0.55, 0.30, 0.06], transparent: true, opacity: 0.7, roughness: 0.1 }), { name: 'Tea', pos: [mugX, 0.052, mugZ] })
  part('mechanism', GEO.pipe([[mugX + 0.033, 0.062, mugZ], [mugX + 0.058, 0.055, mugZ], [mugX + 0.058, 0.024, mugZ], [mugX + 0.033, 0.020, mugZ]], 0.0035, { seg: 32, radial: 10 }), MAT.glass({ roughness: 0.04 }), { name: 'Mug handle' })

  // mint ---------------------------------------------------------------- (7)
  const leafMat = MAT.satin({ color: [0.15, 0.45, 0.18], roughness: 0.55 })
  const veinMat = MAT.satin({ color: [0.55, 0.75, 0.45], roughness: 0.6 })
  const leafGeo = new THREE.SphereGeometry(0.012, 20, 10)
  function mintLeaf(x, y, z, rot) {
    const m = part('subject', leafGeo.clone(), leafMat, { name: 'Mint leaf', pos: [x, y, z], rot: [0, rot, 0], scale: [1.5, 0.12, 0.8] })
    if (!rot) part('subject', GEO.pipe([[x - 0.012, y + 0.001, z], [x + 0.012, y + 0.001, z]], 0.0004, { seg: 8, radial: 5 }), veinMat, { name: 'Mint vein' })
    return m
  }
  mintLeaf(-0.170, 0.006, 0.094, 0.3)
  mintLeaf(-0.150, 0.006, 0.086, -0.5)
  mintLeaf(-0.156, 0.006, 0.104, 1.1)

  // lemon --------------------------------------------------------------- (8)
  const lemonMat = MAT.satin({ color: [0.95, 0.78, 0.12], roughness: 0.45 })
  const pithMat = MAT.satin({ color: [0.96, 0.93, 0.82], roughness: 0.6 })
  function lemonSlice(x, y, z, r) {
    part('subject', GEO.disc(r, 0.003, 0.0006, 48), lemonMat, { name: 'Lemon slice', pos: [x, y, z] })
    part('subject', GEO.tube(r, r - 0.002, 0.003, 48), pithMat, { name: 'Lemon rind', pos: [x, y, z] })
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI * 2
      part('subject', GEO.pipe([
        [x + Math.cos(a) * 0.002, y + 0.0016, z + Math.sin(a) * 0.002],
        [x + Math.cos(a) * (r - 0.003), y + 0.0016, z + Math.sin(a) * (r - 0.003)],
      ], 0.0006, { seg: 8, radial: 5 }), pithMat, { name: 'Lemon segment line' })
    }
  }
  lemonSlice(0.056, 0.006, 0.114, 0.026)
  lemonSlice(0.072, 0.006, 0.104, 0.024)
  lemonSlice(mugX + 0.004, 0.058, mugZ + 0.002, 0.023)

  // honey jar and spoon ------------------------------------------------ (4)
  part('mechanism', GEO.tube(0.022, 0.019, 0.055, 32), MAT.fluid({ color: [0.75, 0.45, 0.08], transparent: true, opacity: 0.9, roughness: 0.15 }), { name: 'Honey jar', pos: [0.185, 0.028, -0.100] })
  part('mechanism', GEO.disc(0.023, 0.006, 0.0012, 32), MAT.steelDark(), { name: 'Honey lid', pos: [0.185, 0.058, -0.100] })
  part('mechanism', GEO.rbox(0.030, 0.016, 0.001, 0.001), MAT.satin({ color: [0.92, 0.88, 0.78] }), { name: 'Honey label', pos: [0.185, 0.028, -0.078] })

  // thermometer --------------------------------------------------------- (3)
  part('mechanism', GEO.tube(0.0032, 0.0022, 0.140, 24), MAT.glass({ roughness: 0.04 }), { name: 'Thermometer glass', pos: [0.190, 0.070, 0.060] })
  part('mechanism', GEO.disc(0.0050, 0.008, 0.0015, 24), MAT.ruby({ roughness: 0.1 }), { name: 'Thermometer bulb', pos: [0.190, 0.004, 0.060] })
  part('mechanism', GEO.tube(0.0012, 0.0008, 0.080, 16), MAT.glow({ emissive: [0.9, 0.08, 0.06], emissiveIntensity: 0.8 }), { name: 'Thermometer column', pos: [0.190, 0.015, 0.060] })

  const stations = [
    [potX, 0, 0], [-0.160, 0, 0.090], [0.060, 0, 0.110], [mugX, 0, mugZ], [mugX, 0, mugZ],
  ]

  let steamOn = true
  const vis = (n, v) => { lab.root.traverse((x) => { if (x.name === n) { if (!x.userData.home) x.userData.home = x.position.clone(); const h = x.userData.home; lab.place(x, h.x, v ? h.y : -5, h.z) } }) }
  const move = (n, fn) => { let k = 0; lab.root.traverse((x) => { if (x.name === n) { fn(x, k++); lab.place(x, x.position.x, x.position.y, x.position.z) } }) }
  return {
    stations,
    onStep(i) {
      steamOn = i <= 1
      for (let k = 1; k <= 6; k++) vis('Steam ' + k, steamOn)
      vis('Pot lid', i === 0); vis('Lid knob', i === 0)
      vis('Mint vein', i === 0)
      if (i >= 1) move('Mint leaf', (o, k) => o.position.set(potX - 0.018 + (k % 3) * 0.018, 0.074, -0.010 + Math.floor(k / 3) * 0.020))
      vis('Lemon segment line', i < 2)
      if (i >= 2) move('Lemon slice', (o, k) => o.position.set(potX - 0.015 + (k % 3) * 0.015, 0.072, -0.008 + Math.floor(k / 3) * 0.016))
      if (i >= 2) move('Lemon rind', (o, k) => o.position.set(potX - 0.015 + (k % 3) * 0.015, 0.072, -0.008 + Math.floor(k / 3) * 0.016))
      tea.material.opacity = i >= 4 ? 1.0 : i >= 3 ? 0.55 : 0.15
    },
    tick(sdt, lab) {
      if (!steamOn) return
      for (const s of steam) {
        s.position.y += sdt * 0.012
        if (s.position.y > 0.190) s.position.y = 0.108
        s.rotation.y += sdt * 0.4
      }
    },
  }
}
"""


SCENE_CHEM = r"""
function buildScene(lab, THREE, MAT, GEO, part) {
  // base ---------------------------------------------------------------- (3)
  part('base', GEO.rbox(0.44, 0.016, 0.30, 0.014), MAT.satin({ color: [0.19, 0.17, 0.15], roughness: 0.7 }), { name: 'Slate board', pos: [0, -0.008, 0] })
  part('base', GEO.rbox(0.11, 0.008, 0.070, 0.006), MAT.satin({ color: [0.62, 0.58, 0.50], roughness: 0.75 }), { name: 'Folded towel', pos: [0.150, 0.004, 0.090] })
  part('base', GEO.rbox(0.10, 0.004, 0.060, 0.004), MAT.satin({ color: [0.70, 0.66, 0.58], roughness: 0.8 }), { name: 'Towel fold', pos: [0.150, 0.010, 0.090] })

  // shallow glass dish: the foil and the silver must be visible
  const bowlX = -0.060
  part('mechanism', GEO.shell([[0.000, 0.002], [0.060, 0.004], [0.100, 0.014], [0.116, 0.048]], 0.004, 80), MAT.glass({ roughness: 0.05, thickness: 0.004 }), { name: 'Glass dish', pos: [bowlX, 0, 0] })
  part('mechanism', GEO.tube(0.116, 0.112, 0.004, 80), MAT.glass({ roughness: 0.05 }), { name: 'Dish rim', pos: [bowlX, 0.048, 0] })
  part('mechanism', GEO.disc(0.110, 0.002, 0.0005, 64), MAT.fluid({ color: [0.55, 0.75, 0.85], transparent: true, opacity: 0.18, roughness: 0.05 }), { name: 'Hot water', pos: [bowlX, 0.040, 0] })

  // foil and silver ----------------------------------------------------- (6)
  part('mechanism', GEO.rbox(0.135, 0.0016, 0.105, 0.0012), MAT.aluminium(), { name: 'Aluminium foil', pos: [bowlX, 0.010, 0], rot: [0, 0.06, 0] })
  for (const [k, x, z, a] of [[0, -0.045, -0.020, 0.4], [1, 0.010, 0.018, -0.7], [2, 0.052, -0.030, 1.2]]) {
    part('mechanism', GEO.pipe([[bowlX + x - 0.020, 0.0135, z], [bowlX + x, 0.0145, z + 0.008], [bowlX + x + 0.020, 0.0135, z]], 0.0009, { seg: 10, radial: 5 }), MAT.aluminium(), { name: `Foil crease ${k + 1}` })
  }
  part('mechanism', GEO.pipe([[bowlX + 0.030, 0.017, 0.010], [bowlX + 0.090, 0.030, 0.028], [bowlX + 0.120, 0.020, 0.050]], 0.0032, { seg: 24, radial: 8 }), MAT.steel(), { name: 'Silver spoon handle' })
  part('mechanism', GEO.disc(0.017, 0.003, 0.001, 40), MAT.steel(), { name: 'Silver spoon bowl', pos: [bowlX + 0.024, 0.017, 0.008] })
  const tarnish = part('subject', GEO.disc(0.014, 0.0008, 0.0002, 40), MAT.satin({ color: [0.20, 0.14, 0.08], transparent: true, opacity: 0.85 }), { name: 'Silver sulfide tarnish', pos: [bowlX + 0.024, 0.0188, 0.008] })

  // baking soda --------------------------------------------------------- (4)
  part('mechanism', GEO.rbox(0.060, 0.080, 0.032, 0.003), MAT.satin({ color: [0.93, 0.91, 0.84] }), { name: 'Baking soda box', pos: [0.160, 0.042, -0.095] })
  part('mechanism', GEO.rbox(0.061, 0.020, 0.033, 0.002), MAT.satin({ color: [0.35, 0.55, 0.70] }), { name: 'Soda label', pos: [0.160, 0.048, -0.095] })
  part('mechanism', GEO.rbox(0.060, 0.004, 0.032, 0.001), MAT.satin({ color: [0.80, 0.78, 0.72] }), { name: 'Soda box top', pos: [0.160, 0.084, -0.095] })
  part('mechanism', GEO.lathe([[0.000, 0.000], [0.022, 0.006], [0.012, 0.018], [0.000, 0.020]], 32), MAT.satin({ color: [0.96, 0.95, 0.90] }), { name: 'Soda mound', pos: [0.130, 0.003, -0.058] })

  // bubbles ------------------------------------------------------------- (7)
  const bubbleMat = MAT.glass({ roughness: 0.02 })
  const bubbles = []
  for (let k = 0; k < 7; k++) {
    bubbles.push(part('subject', new THREE.SphereGeometry(0.0022, 10, 7), bubbleMat, {
      name: `Bubble ${k + 1}`, pos: [bowlX - 0.035 + (k % 3) * 0.030, 0.018 + (k % 4) * 0.006, -0.030 + Math.floor(k / 3) * 0.028],
    }))
  }

  const stations = [
    [bowlX, 0, 0], [bowlX + 0.045, 0, 0.010], [0.160, 0, -0.080], [bowlX, 0, 0], [0.150, 0, 0.090],
  ]

  let bubblesOn = false
  const vis = (n, v) => { lab.root.traverse((x) => { if (x.name === n) { if (!x.userData.home) x.userData.home = x.position.clone(); const h = x.userData.home; lab.place(x, h.x, v ? h.y : -5, h.z) } }) }
  return {
    stations,
    onStep(i) {
      const foil = i >= 1, silver = i >= 2, water = i === 3 || i === 4
      bubblesOn = i === 3 || i === 4
      for (let k = 1; k <= 7; k++) vis('Bubble ' + k, bubblesOn)
      for (const n of ['Aluminium foil', 'Foil crease 1', 'Foil crease 2', 'Foil crease 3']) vis(n, foil)
      for (const n of ['Silver spoon handle', 'Silver spoon bowl', 'Silver sulfide tarnish']) vis(n, silver)
      vis('Hot water', water)
      vis('Soda box top', i < 3)
      vis('Soda mound', i >= 3)
      tarnish.material.opacity = i <= 2 ? 0.85 : i === 3 ? 0.55 : i === 4 ? 0.30 : 0.02
    },
    tick(sdt) {
      if (!bubblesOn) return
      for (const b of bubbles) {
        if (!b.visible) continue
        b.position.y += sdt * 0.010
        if (b.position.y > 0.044) b.position.y = 0.016
      }
    },
  }
}
"""


SCENES = {"food": SCENE_FOOD, "household-chemistry": SCENE_CHEM}

VIEW = {
    "food": {"size": 0.44, "az": 32, "el": 24, "dist": 2.30, "ring": 0.052},
    "household-chemistry": {"size": 0.44, "az": 36, "el": 26, "dist": 2.30, "ring": 0.125},
}


def build(recipe_doc: dict, file_name: str) -> str:
    report = recipe.validate(recipe_doc)
    view = VIEW[recipe_doc["kind"]]
    payload = json.dumps(recipe_doc, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    scene = SCENES[recipe_doc["kind"]]
    title = (recipe_doc.get("tr") or {}).get("title") or recipe_doc["title"]
    page_title = recipe_doc.get("page_title") or recipe_doc["title"]
    description = f"{recipe_doc['kind']} procedure gated by mcp/recipe.py; {report['steps']} steps, {len(report['sources'])} sources"
    return (
        TEMPLATE.replace("__RECIPE_JSON__", payload)
        .replace("__SCENE__", scene.strip())
        .replace("__FILE__", file_name)
        .replace("__TITLE__", html.escape(title))
        .replace("__PAGE_TITLE__", json.dumps(page_title, ensure_ascii=False))
        .replace("__DESC__", html.escape(description))
        .replace("__SIZE__", str(view["size"]))
        .replace("__AZ__", str(view["az"]))
        .replace("__EL__", str(view["el"]))
        .replace("__DIST__", str(view["dist"]))
        .replace("__RING_R__", str(view["ring"]))
    )


def page_name(path: pathlib.Path) -> str:
    return f"recipe_{path.stem}.html"


def generate(path: pathlib.Path, out_dir: pathlib.Path, check: bool = False) -> dict:
    doc = recipe.load(path)
    text = build(doc, path.name)
    out = out_dir / page_name(path)
    if check:
        current = out.read_text(encoding="utf-8") if out.exists() else None
        return {"path": str(path), "page": str(out), "stale": current != text, "bytes": len(text)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return {"path": str(path), "page": str(out), "bytes": len(text), "stale": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=pathlib.Path)
    parser.add_argument("--all", action="store_true", help="every data/recipes/*.json")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true", help="do not write; exit 1 on a stale page")
    args = parser.parse_args(argv)
    paths = args.paths or (sorted((ROOT / "data" / "recipes").glob("*.json")) if args.all else [])
    if not paths:
        parser.error("give a recipe path or --all")
    stale = 0
    for path in paths:
        try:
            row = generate(path, args.out, check=args.check)
        except recipe.RecipeError as exc:
            print(json.dumps({"path": str(path), "verdict": "RED", "reason": str(exc)}, ensure_ascii=False))
            stale += 1
            continue
        print(json.dumps(row, ensure_ascii=False))
        stale += int(row["stale"])
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
