#!/usr/bin/env node
// A4 experiment sheet -> PDF (+ a PNG proof so a human can look at it without opening the PDF).
//   node scripts/sheet.mjs labs/al_cu_sheet.html out/al_cu_sheet.pdf
import { dirname, resolve, relative } from 'node:path'
import { mkdirSync, statSync, readFileSync } from 'node:fs'
import { serve } from './lib/serve.mjs'
import { launch } from './lib/browser.mjs'

const a = process.argv.slice(2)
const PAGE = a[0], OUT = a[1]
if (!PAGE || !OUT) {
  console.error('usage: node scripts/sheet.mjs labs/al_cu_sheet.html out/sheet.pdf')
  process.exit(2)
}
const file = resolve(PAGE), root = resolve(dirname(dirname(file)))
const srv = await serve(root)
mkdirSync(dirname(resolve(OUT)), { recursive: true })
const { browser, page } = await launch({ width: 1240, height: 1754 })
const errors = []
page.on('pageerror', (e) => errors.push(e.message.split('\n')[0]))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })
await page.goto(`${srv.url}/${relative(root, file)}`, { waitUntil: 'load', timeout: 120000 })
await page.evaluate(() => document.fonts.ready)
await page.waitForTimeout(1200)
const facts = await page.evaluate(() => ({
  hero: document.getElementById('hero')?.textContent,
  rows: document.querySelectorAll('table tbody tr, table tr').length,
  sheet: (() => { const r = document.querySelector('.sheet').getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)] })(),
}))
await page.pdf({ path: OUT, printBackground: true, preferCSSPageSize: true })
const png = OUT.replace(/\.pdf$/i, '.png')
await page.setViewportSize({ width: 794, height: 1123 })
await page.screenshot({ path: png, fullPage: false })
// a sheet that spills onto a second A4 page is a broken sheet, so count the pages
const pages = (readFileSync(OUT).toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length
console.log(JSON.stringify({ ...facts, pdf: OUT, pdf_bytes: statSync(OUT).size, pages, png, errors }))
await browser.close()
srv.server.close()
