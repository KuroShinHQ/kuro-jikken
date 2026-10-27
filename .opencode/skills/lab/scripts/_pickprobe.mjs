// Temporary pick probe: what object is under a pixel? (delete after use)
import { resolve, dirname } from 'node:path'
import { serve } from './lib/serve.mjs'
import { launch } from './lib/browser.mjs'

const file = resolve(process.argv[2])
const px = JSON.parse(process.argv[3] ?? '[]')
const root = resolve(dirname(dirname(file)))
const srv = await serve(root)
const { browser, page } = await launch({ width: 1920, height: 1080 })
await page.goto(`${srv.url}/${file.slice(root.length + 1)}`, { waitUntil: 'load', timeout: 120000 })
await page.waitForFunction(() => window.__lab?.renderer, null, { timeout: 120000 })
await page.evaluate(() => document.fonts.ready)
await page.evaluate(() => window.__lab.toggle('cut', true))
await page.waitForTimeout(4000)
const out = await page.evaluate((px) => {
  const L = window.__lab
  const THREE = window.LabKit.THREE
  const RC = new THREE.Raycaster()
  const ndc = new THREE.Vector2()
  const name = (o) => {
    const p = L.parts.find((q) => q.obj === o)
    if (p) return p.name
    let n = o.name || o.type
    let q = o.parent
    while (q && q !== L.machine && q !== L.scene) { n = `${q.name || q.type}/${n}`; q = q.parent }
    return n
  }
  return px.map(([x, y]) => {
    ndc.set((x / innerWidth) * 2 - 1, -(y / innerHeight) * 2 + 1)
    RC.setFromCamera(ndc, L.camera)
    return { px: [x, y], hits: RC.intersectObjects(L.scene.children, true).slice(0, 3).map((h) => ({ name: name(h.object), d: +h.distance.toFixed(4) })) }
  })
}, px)
console.log(JSON.stringify(out, null, 1))
await browser.close()
srv.server.close()
