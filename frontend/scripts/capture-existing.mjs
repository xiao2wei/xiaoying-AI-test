import { chromium } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'
import crypto from 'node:crypto'
import { fileURLToPath } from 'node:url'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const evidence = path.join(root, 'examples/submission/web-ui')
const original = JSON.parse(await fs.readFile(path.join(evidence, 'real-smoke.json'), 'utf8'))
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : undefined) })
const context = await browser.newContext({ viewport: { width: 1440, height: 1080 },
  storageState: path.join(root, 'work/web-browser-state.json') })
const page = await context.newPage()
let posts = 0
// Screenshot refresh must never submit a model task, even accidentally.
await page.route('**/api/**', route => {
  if (route.request().method() === 'POST') { posts++; return route.abort() }
  return route.continue()
})
try {
  await page.goto(process.env.POLICY_WEB_URL || 'http://127.0.0.1:8000')
  await page.waitForFunction(() => document.querySelectorAll('.turn[data-state="completed"]').length === 2)
  const questions = await page.locator('.user-question').allTextContents()
  if (JSON.stringify(questions) !== JSON.stringify(original.questions)) throw new Error('Session mismatch')
  async function fitPage(width, baseHeight) {
    await page.setViewportSize({ width, height: baseHeight })
    await page.evaluate(() => { document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo(0, 0) })
    const height = await page.evaluate(() => document.documentElement.scrollHeight)
    await page.setViewportSize({ width, height: Math.max(baseHeight, height) })
    await page.evaluate(() => window.scrollTo(0, 0))
  }
  await fitPage(1440, 1080)
  await page.screenshot({ path: path.join(root, 'docs/images/web-conversation.png'), fullPage: true, animations: 'disabled' })
  await page.locator('.turn').first().locator('.trace > summary').click()
  await fitPage(1440, 1080)
  await page.locator('.turn').first().screenshot({ path: path.join(root, 'docs/images/web-trace.png'), animations: 'disabled' })
  await page.locator('.turn').first().locator('.trace > summary').click()
  await page.locator('.turn').last().getByRole('button', { name: '查看引用1' }).first().click()
  await fitPage(414, 896)
  await page.screenshot({ path: path.join(root, 'docs/images/web-mobile.png'), fullPage: true, animations: 'disabled' })
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  if (posts || overflow) throw new Error('Screenshot refresh violation')
  await page.setViewportSize({ width: 1440, height: 1080 })
  await page.getByRole('button', { name: '新建对话' }).click()
  await page.getByText('想了解哪项制度？').waitFor()
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))))
  await page.screenshot({ path: path.join(root, 'docs/images/web-welcome.png'), fullPage: true, animations: 'disabled' })
  const images = []
  for (const file of original.screenshots) {
    const bytes = await fs.readFile(path.join(root, file))
    images.push({ path: file, sha256: crypto.createHash('sha256').update(bytes).digest('hex'),
      width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) })
  }
  const report = { captured_at: new Date().toISOString(), session_id: original.session_id,
    real_turns_reused: 2, model_requests: 0, post_requests: posts,
    mobile_no_horizontal_overflow: !overflow,
    note: 'Actual rendered Vue app. Long-page captures use a taller viewport to avoid sticky-input overlap; trace is an element screenshot. No answers changed.',
    images }
  await fs.writeFile(path.join(evidence, 'screenshots.json'), JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report, null, 2))
} finally { await browser.close() }
