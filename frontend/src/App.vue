<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import Icon from './components/Icon.vue'
import AnswerTurn from './components/AnswerTurn.vue'
import { api, configureApi } from './api'

const config = ref(null)
const sessions = ref([])
const current = ref(null)
const draft = ref('')
const pending = ref(null)
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const paused = ref(false)
const sidebarOpen = ref(false)
const toast = ref('')
const input = ref(null)
const end = ref(null)
let alive = true
let toastTimer
const SESSION_KEY = 'policy-agent-session'
const PENDING_KEY = 'policy-agent-pending'
function readStored(key) { try { return localStorage.getItem(key) } catch { return null } }
function store(key, value) { try { value === null ? localStorage.removeItem(key) : localStorage.setItem(key, value) } catch {} }
function savePending(value) { pending.value = value; store(PENDING_KEY, value ? JSON.stringify(value) : null) }
const busy = computed(() => Boolean(pending.value) || submitting.value)
const turns = computed(() => current.value?.turns || [])
const lastOutput = computed(() => turns.value.at(-1)?.result?.output)
const labels = { answered: '本次已回答', needs_confirmation: '需要确认', insufficient_evidence: '资料不足', model_error: '本轮未完成', tool_error: '本轮未完成', validation_failed: '引用校验未通过', limit_reached: '达到执行上限' }
const stateLabel = computed(() => busy.value ? (paused.value ? '连接待恢复' : '正在回答') : labels[lastOutput.value?.status] || (turns.value.at(-1)?.state === 'error' ? '本轮未完成' : '准备就绪'))
const limitReached = computed(() => turns.value.length >= (config.value?.limits.turns_per_conversation || 8))
const canSend = computed(() => !loading.value && !busy.value && config.value?.model_configured && draft.value.trim().length > 0 && draft.value.length <= 2000 && !limitReached.value)
function notice(message) {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 3200)
}
async function scrollEnd() { await nextTick(); end.value?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }
async function listSessions() { sessions.value = (await api('/api/conversations')).conversations }
async function selectSession(id) {
  if (busy.value || loading.value) return
  error.value = ''
  try {
    current.value = await api('/api/conversations/' + id)
    store(SESSION_KEY, id)
    sidebarOpen.value = false
    const running = current.value.turns.find(t => t.state === 'running')
    if (running) {
      savePending({ cid: id, rid: running.id, question: running.question })
      paused.value = false
      await poll(pending.value, running)
    }
  } catch (e) { error.value = e.message }
}
function newConversation() {
  if (busy.value) return
  current.value = null
  draft.value = ''
  error.value = ''
  paused.value = false
  store(SESSION_KEY, null)
  sidebarOpen.value = false
  nextTick(() => input.value?.focus())
}
function fillExample(example) {
  draft.value = example.question
  sidebarOpen.value = false
  nextTick(() => input.value?.focus())
}
async function deleteSession(id) {
  if (busy.value || !window.confirm('删除这段本机会话？已保存的运行日志不会删除。')) return
  try {
    await api('/api/conversations/' + id + '/delete', { method: 'POST', body: {} })
    if (current.value?.id === id) newConversation()
    await listSessions()
  } catch (e) { error.value = e.message }
}
function updateJob(job) {
  if (!current.value || current.value.id !== pending.value?.cid) return
  const i = current.value.turns.findIndex(t => t.id === job.id)
  if (i < 0) current.value.turns.push(job)
  else current.value.turns[i] = job
  if (current.value.turns.length === 1) current.value.title = job.question.slice(0, 22) + (job.question.length > 22 ? '…' : '')
}
async function poll(target, initial) {
  let job = initial
  try {
    while (alive && pending.value?.rid === target.rid) {
      if (!job) job = await api('/api/conversations/' + target.cid + '/turns/' + target.rid)
      updateJob(job)
      if (job.state !== 'running') {
        savePending(null)
        paused.value = false
        current.value.busy = false
        await listSessions().catch(() => {})
        await scrollEnd()
        return
      }
      job = null
      await new Promise(resolve => setTimeout(resolve, 1400))
    }
  } catch (e) {
    if (!alive) return
    if (['SESSION_NOT_FOUND', 'SESSION_EXPIRED'].includes(e.code)) {
      savePending(null)
      current.value = null
      store(SESSION_KEY, null)
    } else {
      paused.value = true
    }
    error.value = e.message
  }
}
async function submit() {
  if (!canSend.value) return
  submitting.value = true
  error.value = ''
  paused.value = false
  const question = draft.value.trim()
  let target
  try {
    if (!current.value) {
      current.value = await api('/api/conversations', { method: 'POST', body: {} })
      store(SESSION_KEY, current.value.id)
    }
    target = { cid: current.value.id, rid: crypto.randomUUID(), question }
    savePending(target)
    const job = await api('/api/conversations/' + target.cid + '/turns', {
      method: 'POST', body: { question, request_id: target.rid },
    })
    draft.value = ''
    updateJob(job)
    await listSessions().catch(() => {})
    await scrollEnd()
    await poll(target, job)
  } catch (e) {
    error.value = e.message
    if (e.code === 'NETWORK_ERROR' && target) {
      paused.value = true
    } else {
      savePending(null)
      if (['SESSION_NOT_FOUND', 'SESSION_EXPIRED'].includes(e.code)) {
        current.value = null
        store(SESSION_KEY, null)
      }
    }
  }
  finally { submitting.value = false }
}
async function resume() {
  if (!pending.value) return boot()
  const target = { ...pending.value }
  error.value = ''
  paused.value = false
  try {
    config.value = await api('/api/config')
    configureApi(config.value.csrf_token)
    let job
    try {
      job = await api('/api/conversations/' + target.cid + '/turns/' + target.rid)
    } catch (e) {
      if (e.code !== 'TURN_NOT_FOUND') throw e
      // Explicit user recovery only; the same request ID prevents a duplicate model run.
      job = await api('/api/conversations/' + target.cid + '/turns', {
        method: 'POST', body: { question: target.question, request_id: target.rid },
      })
    }
    current.value = await api('/api/conversations/' + target.cid)
    draft.value = ''
    await poll(target, job)
  } catch (e) {
    error.value = e.message
    if (['SESSION_NOT_FOUND', 'SESSION_EXPIRED'].includes(e.code)) {
      savePending(null)
      current.value = null
      store(SESSION_KEY, null)
    } else paused.value = true
  }
}
async function boot() {
  loading.value = true
  error.value = ''
  try {
    config.value = await api('/api/config')
    configureApi(config.value.csrf_token)
    await listSessions()
    let savedPending
    try { savedPending = JSON.parse(readStored(PENDING_KEY) || 'null') } catch { savedPending = null }
    const savedId = savedPending?.cid || readStored(SESSION_KEY)
    if (savedId && sessions.value.some(s => s.id === savedId)) {
      current.value = await api('/api/conversations/' + savedId)
      const running = current.value.turns.find(t => t.state === 'running')
      if (running) {
        savePending({ cid: savedId, rid: running.id, question: running.question })
        loading.value = false
        await poll(pending.value, running)
      } else if (savedPending && !current.value.turns.some(t => t.id === savedPending.rid)) {
        savePending(savedPending)
        paused.value = true
        error.value = '上次发送的状态尚未确认。点击恢复查询后确认，不会自动重复调用模型。'
      } else savePending(null)
    } else {
      current.value = null
      savePending(null)
      store(SESSION_KEY, null)
    }
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}
function keydown(event) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    submit()
  }
}
onMounted(boot)
onBeforeUnmount(() => { alive = false; clearTimeout(toastTimer) })
</script>

<template>
  <button v-if="sidebarOpen" class="drawer-shade" aria-label="关闭侧边栏" @click="sidebarOpen = false"></button>
  <aside class="sidebar" :class="{ visible: sidebarOpen }" aria-label="会话与资料">
    <div class="brand"><span class="brand-icon"><Icon name="book" /></span>制度问答
      <button class="mobile-close" aria-label="关闭侧边栏" @click="sidebarOpen = false"><Icon name="close" /></button>
    </div>
    <button class="new-chat" :disabled="busy || loading" @click="newConversation"><Icon name="plus" />新建对话</button>
    <div class="side-heading">当前知识库</div>
    <section class="library">
      <div class="file-top"><Icon name="file" />人事人才篇 · PDF</div>
      <div class="file-name">{{ config?.source.title || '正在加载资料信息…' }}</div>
      <div v-if="config" class="file-detail"><span>{{ config.source.pages }}页</span><span>{{ config.source.documents }}份制度</span></div>
    </section>
    <div class="side-scroll">
      <div class="side-heading">示例问题</div>
      <div class="sample-list">
        <button v-for="example in config?.examples || []" :key="example.title" class="sample-item" :disabled="busy"
                @click="fillExample(example)"><Icon name="chat" />{{ example.title }}</button>
      </div>
      <template v-if="sessions.length">
        <div class="side-heading">最近对话</div>
        <div class="recent-list">
          <div v-for="item in sessions" :key="item.id" class="recent-row" :class="{ active: item.id === current?.id }">
            <button class="recent-select" :title="item.title" :disabled="busy" @click="selectSession(item.id)">{{ item.title }}</button>
            <button class="recent-delete" :disabled="busy" :aria-label="'删除对话：' + item.title" @click="deleteSession(item.id)"><Icon name="trash" :size="12" /></button>
          </div>
        </div>
      </template>
    </div>
    <div class="side-bottom"><a class="help-link" href="https://github.com/xiao2wei/xiaoying-AI-test/blob/main/docs/WEB-UI.md" target="_blank" rel="noopener"><Icon name="file" />使用说明</a>
      <div class="sidebar-note">仅依据当前资料回答</div>
    </div>
  </aside>

  <div class="app">
    <header class="topbar">
      <div class="topbar-title"><button class="mobile-menu" aria-label="打开会话与资料" :aria-expanded="sidebarOpen" @click="sidebarOpen = true"><Icon name="menu" /></button><Icon name="chat" />问答工作台</div>
      <div class="top-meta"><span>{{ config?.model || 'DeepSeek' }}</span><span class="preview-pill">本地 Agent</span></div>
    </header>
    <main class="main">
      <section class="session-title">
        <div><h1>{{ current?.title || '制度问答' }}</h1><p>结合制度原文回答，保留每条结论的依据。</p></div>
        <span class="session-status" :class="{ working: busy, attention: lastOutput && lastOutput.status !== 'answered' }"><i class="dot"></i>{{ stateLabel }}</span>
      </section>
      <div class="mobile-library"><Icon name="file" />{{ config?.source.title || '正在加载资料信息…' }}</div>
      <div v-if="loading" class="boot-state" role="status">正在连接本地服务…</div>
      <div v-if="config && !config.model_configured" class="notice-box error" role="alert">尚未配置DeepSeek密钥。请在项目根目录的.env中填写密钥并重启服务；页面不会回退到Mock。</div>
      <div v-if="error" class="notice-box error connection-error" role="alert">
        <span>{{ error }}</span>
        <button v-if="paused" @click="resume">恢复查询</button>
        <button v-else-if="!config" @click="boot">重新连接</button>
      </div>
      <div class="thread">
        <div v-if="!turns.length && !loading" class="welcome">
          <span class="welcome-icon"><Icon name="book" :size="25" /></span>
          <h2>想了解哪项制度？</h2>
          <p>直接输入问题，也可以选择一个示例开始。</p>
          <div class="welcome-examples"><button v-for="example in config?.examples || []" :key="example.title" @click="fillExample(example)" :disabled="busy">{{ example.title }}<Icon name="chevron" :size="12" /></button></div>
        </div>
        <AnswerTurn v-for="turn in turns" :key="turn.id" :turn="turn" :source-url="config?.source.url" @notice="notice" />
        <div ref="end"></div>
      </div>
      <section class="composer-wrap">
        <div v-if="limitReached && !busy" class="limit-note">本次对话已达到{{ config?.limits.turns_per_conversation }}轮，请新建对话继续。</div>
        <div class="composer">
          <textarea ref="input" v-model="draft" :disabled="busy || loading || !config?.model_configured || limitReached"
                    maxlength="2000" aria-label="输入问题" rows="2"
                    :placeholder="busy ? '正在处理本轮问题，请等待完成…' : '继续追问，或输入新的制度问题……'"
                    @keydown="keydown"></textarea>
          <div class="composer-bar">
            <span class="composer-hint"><Icon name="history" />Enter 发送 · Shift + Enter 换行</span>
            <button class="send" :disabled="!canSend" @click="submit">{{ busy ? '处理中' : '发送' }}<Icon name="up" /></button>
          </div>
        </div>
        <p class="footnote">真实调用 DeepSeek · 每轮最多{{ config?.limits.decision_rounds_per_turn || 12 }}轮决策、{{ config?.limits.tools_per_turn || 10 }}次工具调用 · 密钥仅保存在本地服务端</p>
      </section>
    </main>
  </div>
  <div v-if="toast" class="toast show" role="status">{{ toast }}</div>
</template>
