// Temporary GL/fps probe (delete after use).
import { resolve, dirname } from 'node:path'
import { serve } from './lib/serve.mjs'
import { launch } from './lib/browser.mjs'

const file = resolve(process.argv[2])
const root = resolve(dirname(dirname(file)))
const srv = await serve(root)
const { browser, page } = await launch({ width: 1920, height: 1080 })
await page.goto(`${srv.url}/${file.slice(root.length + 1)}`, { waitUntil: 'load', timeout: 120000 })
await page.waitForFunction(() => window.__lab?.renderer, null, { timeout: 120000 })
await page.evaluate(() => document.fonts.ready)
await page.waitForTimeout(5000)
const info = await page.evaluate(async () => {
  const c = document.createElement('canvas')
  const gl = c.getContext('webgl2')
  const d = gl.getExtension('WEBGL_debug_renderer_info')
  const renderer = d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'n/a'
  const measure = () => new Promise((r) => {
    const t0 = performance.now(); let n = 0
    const f = () => { n++; if (performance.now() - t0 < 2000) requestAnimationFrame(f); else r(n / 2) }
    requestAnimationFrame(f)
  })
  const a = await measure()
  const b = await measure()
  return { renderer, fps1: a, fps2: b, parts: window.__lab.partCount(), tris: window.__lab.tris }
})
console.log(JSON.stringify(info))
await browser.close()
srv.server.close()
