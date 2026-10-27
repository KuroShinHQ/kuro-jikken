// Vendored from AirsupHQ/machine-skill (MIT). Copyright (c) 2026 Airsup. See ../LICENSE.
// Launch headless Chromium with the GPU on, guarded against magenta frames.
let pw
try { pw = await import('playwright') } catch {
  try { pw = await import('playwright-core') } catch { console.error('Needs Playwright: npm i -D playwright && npx playwright install chromium'); process.exit(2) }
}
import { guardPage } from './guard.mjs'
export async function launch({ width = 1920, height = 1080, scale = 1 } = {}) {
  const args = ['--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--disable-background-timer-throttling', '--disable-renderer-backgrounding']
  if (process.platform === 'darwin') args.push('--use-angle=metal')
  else if (process.platform === 'linux') args.push('--use-angle=vulkan', '--enable-features=Vulkan')
  // Windows headless defaults to SwiftShader (2 fps measured 2026-10-27, scripts/_gpuhead.mjs);
  // forcing ANGLE/D3D11 gives the real GPU: "ANGLE (NVIDIA ... RTX 4060 ... D3D11)" at 61 fps.
  // 30x the frames per second, and it is the same path the desktop browser uses.
  else if (process.platform === 'win32') args.push('--use-gl=angle', '--use-angle=d3d11')
  const browser = await pw.chromium.launch({ headless: true, args })
  const page = guardPage(await browser.newPage({ viewport: { width, height }, deviceScaleFactor: scale }))
  page.on('pageerror', (e) => console.log('PAGE ERROR', e.message.split('\n')[0]))
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('CONSOLE', m.text().slice(0, 1200)) })
  return { browser, page }
}
