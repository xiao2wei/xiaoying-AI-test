<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({ turn: { type: Object, required: true }, sourceUrl: { type: String, default: '/api/source.pdf' } })
const emit = defineEmits(['notice'])
const result = computed(() => props.turn.result)
const output = computed(() => result.value?.output)
const sourceElements = new Map()
const statuses = {
  answered: '已回答', needs_confirmation: '需要确认', insufficient_evidence: '资料不足',
  tool_error: '工具失败，未完成', limit_reached: '达到上限，未完成',
  model_error: '模型服务未完成', validation_failed: '引用校验未通过',
}
const statusLabel = computed(() => statuses[output.value?.status] || (props.turn.state === 'error' ? '本轮未完成' : '正在回答'))
const sources = computed(() => {
  const map = new Map()
  for (const claim of output.value?.claims || []) {
    for (const citation of claim.citations || []) {
      const key = citation.chunk_id
      if (!map.has(key)) map.set(key, { ...citation, index: map.size + 1, quotes: [] })
      const source = map.get(key)
      if (!source.quotes.includes(citation.quote)) source.quotes.push(citation.quote)
    }
  }
  return [...map.values()]
})
const events = computed(() => (result.value?.trace || []).filter(e => e.kind === 'decision' || e.kind === 'tool'))
const modelEvents = computed(() => (result.value?.trace || []).filter(e => e.kind === 'model'))
const actionLabel = { search: '选择检索', read: '选择读取原文', finish: '提出回答或结束' }
function claimSources(claim) {
  return [...new Set((claim.citations || []).map(c => c.chunk_id))]
    .map(id => sources.value.find(s => s.chunk_id === id)).filter(Boolean)
}
function showSource(id) {
  const element = sourceElements.get(id)
  if (element) {
    element.open = true
    element.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }
}
function toolSummary(event) {
  const r = event.result || {}
  if (!r.ok) return '失败：' + (r.error?.code || '未知错误') + (r.error?.message ? ' · ' + r.error.message : '')
  if (r.hits) return '命中 ' + r.hits.length + ' 个片段：' + r.hits.map(x => x.chunk_id).join('、')
  if (r.chunk) return '已读取 ' + r.chunk.chunk_id + ' · ' + (r.chunk.article || '') + ' · PDF ' + (r.chunk.pdf_pages || []).join('、') + '页'
  return '工具执行成功'
}
function gapText(gap) {
  if (gap === 'HTTP_402') return 'DeepSeek账号余额不足，本轮未完成。请补充余额后重启本地服务。'
  if (gap === 'HTTP_401' || gap === 'HTTP_403') return 'DeepSeek凭据校验未通过，请检查项目根目录.env中的密钥并重启服务。'
  return gap
}
async function copyAnswer() {
  try {
    await navigator.clipboard.writeText(output.value?.answer || '')
    emit('notice', '已复制完整回答')
  } catch {
    emit('notice', '浏览器未允许复制，请手动选中回答文字。')
  }
}
function download() {
  const blob = new Blob([JSON.stringify(props.turn, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'policy-turn-' + props.turn.id + '.json'
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
</script>

<template>
  <section class="turn" :data-turn-id="turn.id" :data-state="turn.state">
    <div class="user-row">
      <div class="user-question">{{ turn.question }}</div>
      <span class="avatar user-avatar"><Icon name="user" /></span>
    </div>
    <div class="answer-head">
      <span class="avatar ai-avatar">AI</span>制度助手
      <span class="answer-sub">{{ result?.real_model ? '真实 DeepSeek · 依据已读取资料' : 'Agent 问答' }}</span>
      <span v-if="output" class="answer-status" :class="output.status">{{ statusLabel }}</span>
    </div>
    <article class="answer-card">
      <div v-if="turn.state === 'running'" class="answer-main running" role="status" aria-live="polite">
        <span class="spinner"></span>
        <div><strong>Agent 正在处理问题</strong><p>请稍候。完成后展示实际回答、原文引用和执行过程。</p></div>
      </div>
      <div v-else-if="turn.state === 'error'" class="answer-main">
        <div class="notice-box error" role="alert">{{ turn.error?.message || '本轮未完成。' }}</div>
      </div>
      <template v-else-if="output">
        <div class="answer-main">
          <div class="answer-text">
            <p v-for="(claim, i) in output.claims || []" :key="i" class="claim">
              {{ claim.text }}
              <button v-for="source in claimSources(claim)" :key="source.chunk_id" class="cite"
                      :aria-label="'查看引用' + source.index" @click="showSource(source.chunk_id)">{{ source.index }}</button>
            </p>
            <p v-if="!output.claims?.length && !output.gaps?.length">{{ output.answer }}</p>
          </div>
          <div v-if="output.gaps?.length" class="notice-box" :class="{ error: !['needs_confirmation', 'insufficient_evidence'].includes(output.status) }">
            <strong>{{ output.status === 'needs_confirmation' ? '还需要你确认' : output.status === 'insufficient_evidence' ? '资料缺口' : '未完成原因' }}</strong>
            <ul><li v-for="(gap, i) in output.gaps" :key="i">{{ gapText(gap) }}</li></ul>
          </div>
          <div v-if="sources.length" class="sources">
            <details v-for="source in sources" :key="source.chunk_id" class="source"
                     :ref="el => el ? sourceElements.set(source.chunk_id, el) : sourceElements.delete(source.chunk_id)">
              <summary>
                <span class="source-id">{{ source.doc_id }}</span>
                <div class="source-info">
                  <div class="source-title">{{ source.title }}</div>
                  <div class="source-meta">{{ source.article }} · PDF 第{{ (source.pdf_pages || []).join('、') }}页 · 版本日期 {{ source.version_date || '未标明' }}</div>
                </div>
                <span class="source-action"><span>查看原文</span><Icon name="chevron" class="chevron" /></span>
              </summary>
              <div class="source-content">
                <div class="print-page">{{ source.chunk_id }} · 印刷第{{ (source.printed_pages || []).join('、') }}页</div>
                <blockquote v-for="(text, i) in source.quotes" :key="i">{{ text }}</blockquote>
                <a v-if="source.pdf_pages?.length" :href="sourceUrl + '#page=' + source.pdf_pages[0]"
                   target="_blank" rel="noopener" class="pdf-link"><Icon name="link" :size="12" />在PDF中查看第{{ source.pdf_pages[0] }}页</a>
              </div>
            </details>
          </div>
        </div>
        <div class="answer-footer">
          <details class="trace">
            <summary><Icon name="trace" />查看执行过程
              <span class="trace-meta">{{ result.tool_calls }} 次工具 · {{ result.model_calls }} 次模型</span>
              <Icon name="chevron" class="chevron" />
            </summary>
            <ol class="trace-content">
              <li v-for="(event, i) in events" :key="i">
                <span class="step-no">{{ String(i + 1).padStart(2, '0') }}</span>
                <div class="event-body">
                  <strong>{{ event.kind === 'decision' ? actionLabel[event.action] || event.action : event.name === 'search' ? '执行检索工具' : '执行原文读取' }}</strong>
                  <p v-if="event.kind === 'decision'">{{ event.reason }}</p>
                  <p v-else :class="{ 'tool-error': !event.result?.ok }">{{ toolSummary(event) }}</p>
                  <pre v-if="event.arguments && Object.keys(event.arguments).length">{{ JSON.stringify(event.arguments, null, 2) }}</pre>
                  <p v-if="event.result?.excerpt" class="tool-excerpt">{{ event.result.excerpt }}</p>
                </div>
              </li>
            </ol>
            <div class="trace-stats">本轮耗时 {{ result.seconds?.toFixed(2) }} 秒 · 读取 {{ result.read_ids?.length || 0 }} 个片段</div>
            <details class="request-records"><summary>模型响应记录（{{ modelEvents.length }}）</summary>
              <ul><li v-for="(event, i) in modelEvents" :key="i">{{ event.response_model || event.model }} · HTTP {{ event.http_status || '连接未完成' }} · {{ event.seconds }}秒
                <span v-if="event.response_id" class="response-id">{{ event.response_id }}</span>
                <span v-if="event.error">错误：{{ event.error }}</span>
              </li></ul>
            </details>
          </details>
          <div class="answer-actions">
            <button class="copy" @click="copyAnswer"><Icon name="copy" />复制回答</button>
            <button class="copy" @click="download" :aria-label="'下载本轮记录'"><Icon name="download" />记录</button>
          </div>
        </div>
      </template>
    </article>
  </section>
</template>
