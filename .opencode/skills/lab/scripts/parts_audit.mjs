// parts_audit: every part sits on something, nothing interfers, nothing floats.
//   node scripts/parts_audit.mjs labs/al_cu_liquidus.html [--json]
// Exit 1 on a violation. Reads the live scene: bounding boxes in world units.
import { resolve, dirname } from 'node:path'
import { serve } from './lib/serve.mjs'
import { launch } from './lib/browser.mjs'

const file = resolve(process.argv[2])
const asJson = process.argv.includes('--json')
const root = resolve(dirname(dirname(file)))
const srv = await serve(root)
const { browser, page } = await launch({ width: 1280, height: 720 })
await page.goto(`${srv.url}/${file.slice(root.length + 1).split('\\').join('/')}`, { waitUntil: 'load', timeout: 120000 })
await page.waitForFunction(() => window.__lab?.renderer, null, { timeout: 120000 })
await page.waitForTimeout(2500)

const out = await page.evaluate(() => {
  const L = window.__lab, THREE = window.LabKit.THREE
  L.machine.updateWorldMatrix(true, true)
  const s = L.machine.getWorldScale(new THREE.Vector3()).x || 1
  const rows = L.parts.map((p) => {
    const b = new THREE.Box3().setFromObject(p.obj)
    return { name: p.name, min: [b.min.x / s, b.min.y / s, b.min.z / s], max: [b.max.x / s, b.max.y / s, b.max.z / s] }
  })
  return { scale: s, rows }
})
await browser.close(); srv.server.close()

const R = out.rows, TOL = 0.0015
const floating = [], interference = [], outside = []
const ov = (a, b) => [0, 1, 2].map((i) => Math.min(a.max[i], b.max[i]) - Math.max(a.min[i], b.min[i]))
for (const r of R) {
  if (Math.max(Math.abs(r.min[0]), Math.abs(r.max[0]), Math.abs(r.min[2]), Math.abs(r.max[2])) > 0.45) outside.push(r.name)
  // a part sits on another when their footprints overlap and that part's top reaches this bottom
  const supported = R.some((o) => o !== r && Math.max(0, ...[0, 1, 2].map((i) => Math.max(r.min[i] - o.max[i], o.min[i] - r.max[i]))) <= 0.005)
  if (!supported) floating.push(r.name)
}
for (let i = 0; i < R.length; i++) for (let j = i + 1; j < R.length; j++) {
  const o = ov(R[i], R[j])
  if (o[0] > TOL && o[1] > TOL && o[2] > TOL) interference.push([R[i].name, R[j].name, +Math.min(...o).toFixed(4)])
}
const report = { parts: R.length, floating, interference, outside }
if (asJson) console.log(JSON.stringify(report))
else {
  console.log(`parts ${R.length} | floating ${floating.length} | interference ${interference.length} | outside ${outside.length}`)
  for (const f of floating) console.log('  FLOAT', f[0], f[1])
  for (const f of interference) console.log('  HIT  ', f[0], '<->', f[1], f[2])
  for (const f of outside) console.log('  OUT  ', f)
}
const bad = floating.length + outside.length
console.log(bad ? 'RESULT FAIL' : 'RESULT PASS')
process.exit(bad ? 1 : 0)


