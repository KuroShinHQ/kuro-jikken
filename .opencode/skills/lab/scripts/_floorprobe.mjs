// Temporary scene probe: ground/floor meshes (delete after use)
import { resolve, dirname } from 'node:path'
import { serve } from './lib/serve.mjs'
import { launch } from './lib/browser.mjs'

const file = resolve(process.argv[2])
const root = resolve(dirname(dirname(file)))
const srv = await serve(root)
const { browser, page } = await launch({ width: 1280, height: 720 })
await page.goto(`${srv.url}/${file.slice(root.length + 1)}`, { waitUntil: 'load', timeout: 120000 })
await page.waitForFunction(() => window.__lab?.renderer, null, { timeout: 120000 })
await page.waitForTimeout(3000)
const out = await page.evaluate(() => {
  const L = window.__lab
  const rows = []
  L.scene.traverse((o) => {
    if (!o.isMesh) return
    const t = o.geometry?.type ?? ''
    if (!/Circle|Plane/.test(t)) return
    const c = o.material?.color
    rows.push({
      geo: t, y: +o.position.y.toFixed(4), z: +o.position.z.toFixed(4),
      visible: o.visible, mat: o.material?.type, color: c ? c.getHexString() : null,
      w: o.geometry.parameters?.width ?? o.geometry.parameters?.radius ?? null,
      recv: o.receiveShadow, isPart: !!L.parts.find((p) => p.obj === o),
    })
  })
  return rows
})
console.log(JSON.stringify(out, null, 0))
await browser.close()
srv.server.close()
