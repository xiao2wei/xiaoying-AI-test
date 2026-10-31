import { chromium } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'
import crypto from 'node:crypto'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const baseURL = process.env.POLICY_WEB_URL || 'http://127.0.0.1:8000'
const evidence = path.join(root, 'examples/submission/web-ui')
const images = path.join(root, 'docs/images')
await fs.mkdir(evidence, { recursive: true }); await fs.mkdir(images, { recursive: true })
if (await fs.stat(path.join(evidence, 'real-smoke.json')).catch(() => null)) {
  throw new Error('Real evidence already exists. Do not repeat paid questions or overwrite it.')
}
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : undefined) })
const resume = process.argv.includes('--resume-web-session')
const context = await browser.newContext({ ...(resume ? { storageState: path.join(root, 'work/web-browser-state.json') } : {}), viewport: { width: 1440, height: 1080 }, deviceScaleFactor: 1 })
const page = await context.newPage()
const errors = []
page.on('pageerror', error => errors.push(String(error)))
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
const started = new Date().toISOString()
try {
  await page.goto(baseURL)
  await page.getByRole('textbox', { name: '输入问题' }).waitFor()
  await page.waitForFunction(() => !document.querySelector('.boot-state'))
  const config = await page.evaluate(() => fetch('/api/config').then(r => r.json()))
  if (!config.model_configured) throw new Error('Real model key is not configured')
  const screenshots = []
  async function screenshot(name, fullPage = true) {
    await page.screenshot({ path: path.join(images, name), fullPage, animations: 'disabled' })
    screenshots.push('docs/images/' + name)
  }
  if (!resume) await screenshot('web-welcome.png', false)
  else {
    await fs.stat(path.join(images, 'web-welcome.png'))
    screenshots.push('docs/images/web-welcome.png')
    if (await page.locator('.turn').count() === 0) throw new Error('Resume requested but original session unavailable; will not repeat paid requests')
  }
  const questions = [
    '校内申诉从知道权利受侵害之日起多久内提出？因不可抗力逾期，障碍消除后多久可以提起？',
    '这里的30天和10天都是工作日吗？请分别说明从什么时候开始计算。',
  ]
  for (let i = 0; i < questions.length; i++) {
    if (await page.locator('.turn').count() <= i) {
      await page.getByRole('textbox', { name: '输入问题' }).fill(questions[i])
      await page.getByRole('button', { name: '发送', exact: true }).click()
    } else {
      if (await page.locator('.turn').nth(i).locator('.user-question').textContent() !== questions[i]) throw new Error('Unexpected session contents; will not repeat paid requests')
      console.log('REUSE_EXISTING_REAL_TURN', i + 1)
    }
    await page.locator('.turn').nth(i).locator('.answer-card').waitFor()
    console.log('REAL_TURN_STARTED', i + 1)
    await page.waitForFunction(n => document.querySelectorAll('.turn[data-state="completed"]').length === n, i + 1, { timeout: 180000 })
    const turn = page.locator('.turn').nth(i)
    await turn.locator('.answer-status.answered').waitFor()
    await turn.locator('.source').first().waitFor()
    if (i === 0) {
      await page.evaluate(() => window.scrollTo(0, 0))
      await screenshot('web-overview.png', false)
      await turn.getByRole('button', { name: '查看引用1' }).first().click()
      await page.evaluate(() => window.scrollTo(0, 0))
      await screenshot('web-citations.png')
      await turn.locator('.source').evaluateAll(nodes => nodes.forEach(n => { n.open = false }))
      await turn.locator('.trace > summary').click()
      await page.evaluate(() => window.scrollTo(0, 0))
      await screenshot('web-trace.png')
      await turn.locator('.trace > summary').click()
    }
    console.log('REAL_TURN_COMPLETED', i + 1)
  }
  const cid = await page.evaluate(() => localStorage.getItem('policy-agent-session'))
  const session = await page.evaluate(id => fetch('/api/conversations/' + id).then(r => r.json()), cid)
  if (session.turns.length !== 2 || !session.turns.every(t => t.result.real_model && t.result.output.status === 'answered')) throw new Error('Real two-turn verification failed')
  await page.evaluate(() => window.scrollTo(0, 0))
  await screenshot('web-conversation.png')
  await context.storageState({ path: path.join(root, 'work/web-browser-state.json') })
  await page.setViewportSize({ width: 414, height: 896 })
  await page.locator('.turn').last().getByRole('button', { name: '查看引用1' }).first().click()
  await page.evaluate(() => window.scrollTo(0, 0))
  await screenshot('web-mobile.png')
  if (!(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))) throw new Error('Mobile horizontal overflow')
  const raw = []
  for (let i = 0; i < session.turns.length; i++) {
    const turn = session.turns[i]
    const bytes = await fs.readFile(path.join(root, 'work/web-runs', cid, turn.id + '.json'))
    const result = JSON.parse(bytes)
    if (!result.real_model || result.validation_errors?.length) throw new Error('Real model/provenance validation failed')
    const dest = 'examples/submission/web-ui/real-turn-' + (i + 1) + '.json'
    await fs.writeFile(path.join(root, dest), bytes)
    raw.push({ path: dest, sha256: crypto.createHash('sha256').update(bytes).digest('hex'), result })
  }
  const historyVerified = raw[1].result.history.length === 2 &&
    raw[1].result.history[0].content === questions[0] &&
    JSON.stringify(JSON.parse(raw[1].result.history[1].content)) === JSON.stringify(raw[0].result.output)
  if (!historyVerified) throw new Error('Second turn did not receive actual first-turn history')
  const models = raw.flatMap(r => r.result.trace.filter(e => e.kind === 'model'))
  const summary = {
    started_at: session.created_at, validation_started_at: started, resumed_existing_session: resume, completed_at: new Date().toISOString(), passed: true,
    scope: 'Two real browser questions through the existing Agent; not a new formal evaluation.',
    browser: await browser.version(), questions, session_id: cid,
    real_turns: 2, actual_history_verified: historyVerified,
    model_requests: raw.reduce((n, r) => n + r.result.model_calls, 0),
    tool_calls: raw.reduce((n, r) => n + r.result.tool_calls, 0),
    total_tokens: models.reduce((n, m) => n + (m.usage?.total_tokens || 0), 0),
    browser_errors: errors,
    mobile_no_horizontal_overflow: true,
    outputs: raw.map(({ path, sha256 }) => ({ path, sha256 })), screenshots,
  }
  await fs.writeFile(path.join(evidence, 'browser-session.json'), JSON.stringify(session, null, 2) + '\n')
  await fs.writeFile(path.join(evidence, 'real-smoke.json'), JSON.stringify(summary, null, 2) + '\n')
  console.log(JSON.stringify(summary, null, 2))
} finally {
  await context.storageState({ path: path.join(root, 'work/web-browser-state.json') }).catch(() => {})
  await browser.close()
}
