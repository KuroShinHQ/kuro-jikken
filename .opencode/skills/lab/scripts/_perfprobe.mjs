// Temporary perf tuning probe (delete after use).
import { resolve, dirname } from 'node:path'
import { chromium } from 'playwright'
import { serve } from './lib/serve.mjs'

const file = resolve(process.argv[2])
const root = resolve(dirname(dirname(file)))
const srv = await serve(root)
const browser = await chromium.launch({
  headless: false,
  args: ['--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--disable-background-timer-throttling', '--disable-renderer-backgrounding'],
})
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } })
await page.goto(`${srv.url}/${file.slice(root.length + 1)}`, { waitUntil: 'load', timeout: 120000 })
await page.waitForFunction(() => window.__lab?.renderer, null, { timeout: 120000 })
await page.evaluate(() => document.fonts.ready)
await page.waitForTimeout(5000)

const steps = [
  ['baseline', ''],
  ['ao off', 'lab.ao.enabled = false'],
  ['+ transmission 0', `lab.scene.traverse(o => { if (o.material && o.material.transmission > 0) { o.material.transmission = 0; o.material.opacity = 0.24; o.material.needsUpdate = true } })`],
  ['+ shadows off', 'lab.renderer.shadowMap.enabled = false'],
  ['+ pixelRatio 1', 'lab.renderer.setPixelRatio(1)'],
]
for (const [name, js] of steps) {
  if (js) await page.evaluate((s) => { const lab = window.__lab; return eval(s) }, js)
  await page.waitForTimeout(1500)
  const fps = await page.evaluate(() => new Promise((r) => {
    const t0 = performance.now(); let n = 0
    const f = () => { n++; if (performance.now() - t0 < 2000) requestAnimationFrame(f); else r(n / 2) }
    requestAnimationFrame(f)
  }))
  console.log(name.padEnd(20), fps)
}
await browser.close()
srv.server.close()
