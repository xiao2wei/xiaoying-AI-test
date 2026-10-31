import { test, expect } from '@playwright/test'

// Deterministic browser fixtures only. These are never used by the application,
// screenshots or model-quality evidence, and make zero DeepSeek requests.
async function fixture(page, { configured = true, losePost = false, delayed = false, status = 'answered' } = {}) {
  const sessions = []
  let sends = 0
  const config = { csrf_token: 'fixture-csrf', model: 'fixture-only', model_configured: configured,
    source: { title: '界面测试资料（夹具）', pages: 229, documents: 29, url: '/api/source.pdf' },
    examples: [{ title: '示例问题', question: '测试申诉期限？' }],
    limits: { turns_per_conversation: 8, tools_per_turn: 10, decision_rounds_per_turn: 12 } }
  const citation = { chunk_id: 'D24-C012', doc_id: 'D24', title: '测试条例（夹具）', article: '第十一条',
    pdf_pages: [184], printed_pages: [179], version_date: '2021-05-30', quote: '三十个工作日内提出申诉。' }
  function completed(body) {
    const text = body.question.includes('<img') ? body.question : '应当在三十个工作日内提出。'
    return { id: body.request_id, question: body.question, state: 'completed',
      result: { real_model: false, question: body.question, seconds: 1.25, model_calls: 0, tool_calls: 2, read_ids: ['D24-C012'],
        output: { status, answer: status === 'answered' ? text : '资料不足', claims: status === 'answered' ? [{ text, citations: [citation] }] : [],
          gaps: status === 'answered' ? [] : ['请提供学校官方接入说明，当前资料没有对应密码。'] },
        trace: [
          { kind: 'decision', action: 'read', reason: '读取命中的条款进行核对。', arguments: { chunk_id: 'D24-C012' } },
          { kind: 'tool', name: 'read', arguments: { chunk_id: 'D24-C012' }, result: { ok: true, chunk: citation, excerpt: citation.quote } },
          { kind: 'decision', action: 'finish', reason: '依据原文给出回答。', arguments: {} },
        ] } }
  }
  await page.route('**/api/**', async route => {
    const req = route.request()
    const path = new URL(req.url()).pathname
    let data
    if (path === '/api/config') data = config
    else if (path === '/api/conversations' && req.method() === 'GET') data = { conversations: sessions.map(s => ({ ...s, turns: undefined, turn_count: s.turns.length })) }
    else if (path === '/api/conversations') {
      if (delayed) await new Promise(r => setTimeout(r, 200))
      const session = { id: String(sessions.length + 1).padStart(32, '0'), title: '新对话', busy: false, turns: [] }
      sessions.push(session); data = session
    } else {
      const parts = path.split('/')
      const s = sessions.find(x => x.id === parts[3])
      if (!s) return route.fulfill({ status: 404, json: { error: { code: 'SESSION_NOT_FOUND', message: '不存在' } } })
      if (parts[4] === 'turns' && req.method() === 'POST') {
        sends++
        const body = req.postDataJSON()
        expect(Object.keys(body).sort()).toEqual(['question', 'request_id'])
        const job = completed(body); s.turns.push(job); s.title = body.question.slice(0, 22)
        if (losePost) { losePost = false; return route.abort('failed') }
        data = job
      } else if (parts[4] === 'turns') data = s.turns.find(t => t.id === parts[5])
      else if (parts[4] === 'delete') { sessions.splice(sessions.indexOf(s), 1); data = { deleted: true } }
      else data = s
    }
    await route.fulfill({ json: data })
  })
  await page.goto('/')
  await expect(page.getByText('想了解哪项制度？')).toBeVisible()
  return { sends: () => sends, sessions }
}
async function send(page, question) {
  await page.getByRole('textbox', { name: '输入问题' }).fill(question)
  await page.getByRole('button', { name: '发送', exact: true }).click()
}
test('answer, original citation, PDF page and actual trace are expandable', async ({ page }) => {
  await fixture(page); await send(page, '测试申诉期限？')
  await expect(page.locator('.claim')).toContainText('三十个工作日')
  await page.getByRole('button', { name: '查看引用1' }).click()
  await expect(page.locator('blockquote')).toHaveText('三十个工作日内提出申诉。')
  await expect(page.locator('.pdf-link')).toHaveAttribute('href', '/api/source.pdf#page=184')
  await page.locator('.trace > summary').click()
  await expect(page.locator('.trace-content')).toContainText('读取命中的条款进行核对')
  await expect(page.locator('.trace-content')).toContainText('D24-C012')
  await expect(page.getByText('真实 DeepSeek · 依据已读取资料')).toHaveCount(0)
})
test('multi-turn view, reload, new conversation and explicit examples', async ({ page }) => {
  const f = await fixture(page)
  await page.locator('.welcome-examples button').click()
  expect(f.sends()).toBe(0)
  await expect(page.getByRole('textbox')).toHaveValue('测试申诉期限？')
  await page.getByRole('button', { name: '发送', exact: true }).click()
  await expect(page.locator('.turn')).toHaveCount(1)
  await send(page, '这里说的是工作日吗？')
  await expect(page.locator('.turn')).toHaveCount(2)
  expect(f.sessions).toHaveLength(1)
  await page.reload()
  await expect(page.locator('.turn')).toHaveCount(2)
  await page.getByRole('button', { name: '新建对话' }).click()
  await expect(page.locator('.turn')).toHaveCount(0)
  await send(page, '另一段独立对话')
  await expect(page.locator('.turn')).toHaveCount(1)
  expect(f.sessions).toHaveLength(2)
})
test('double activation while creating a session makes one paid-task request', async ({ page }) => {
  const f = await fixture(page, { delayed: true })
  await page.getByRole('textbox').fill('测试申诉期限？')
  await page.locator('.send').evaluate(button => { button.click(); button.click() })
  await expect(page.locator('.turn[data-state="completed"]')).toHaveCount(1)
  expect(f.sends()).toBe(1); expect(f.sessions).toHaveLength(1)
})
test('lost POST response recovers original job without resending', async ({ page }) => {
  const f = await fixture(page, { losePost: true })
  await send(page, '测试申诉期限？')
  await expect(page.getByRole('button', { name: '恢复查询' })).toBeVisible()
  expect(f.sends()).toBe(1)
  await page.getByRole('button', { name: '恢复查询' }).click()
  await expect(page.locator('.turn[data-state="completed"]')).toHaveCount(1)
  expect(f.sends()).toBe(1)
})
test('missing key disables send; no fallback answer', async ({ page }) => {
  const f = await fixture(page, { configured: false })
  await expect(page.getByRole('alert')).toContainText('尚未配置DeepSeek密钥')
  await expect(page.getByRole('textbox')).toBeDisabled()
  await expect(page.locator('.send')).toBeDisabled()
  expect(f.sends()).toBe(0)
})
test('source gap is actionable and marked as insufficient', async ({ page }) => {
  await fixture(page, { status: 'insufficient_evidence' }); await send(page, '无线密码是多少？')
  await expect(page.locator('.answer-status')).toHaveText('资料不足')
  await expect(page.locator('.answer-main')).toContainText('请提供学校官方接入说明')
  await expect(page.locator('.source')).toHaveCount(0)
})
test('question and answer HTML stay literal text', async ({ page }) => {
  await fixture(page)
  const html = '<img src=x onerror="window.untrustedExecuted=true">'
  await send(page, html)
  await expect(page.locator('.claim')).toContainText(html)
  await expect(page.locator('.thread img')).toHaveCount(0)
  expect(await page.evaluate(() => window.untrustedExecuted)).toBeUndefined()
})
test('mobile layout has no horizontal overflow and retains new-chat controls', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await fixture(page); await send(page, '手机上的申诉期限问题？')
  await expect(page.locator('.turn[data-state="completed"]')).toHaveCount(1)
  await page.getByRole('button', { name: '查看引用1' }).click()
  await page.locator('.trace > summary').click()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.getByRole('button', { name: '打开会话与资料' }).click()
  await expect(page.locator('.sidebar')).toHaveClass(/visible/)
  await page.getByRole('button', { name: '新建对话' }).click()
  await expect(page.locator('.turn')).toHaveCount(0)
})
