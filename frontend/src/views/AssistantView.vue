<template>
  <div class="assistant-view">
    <!-- 左栏：历史会话（按用户隔离，仅本人可见） -->
    <aside class="sess-panel">
      <div class="sess-head">
        <el-button type="primary" size="small" class="new-btn" @click="newChat">
          <el-icon><Plus /></el-icon>&nbsp;新对话
        </el-button>
      </div>
      <div class="sess-list pa-scroll">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="sess-item"
          :class="{ active: s.id === currentId }"
          @click="openSession(s.id)"
        >
          <div class="sess-text">
            <div class="sess-title">{{ s.title }}</div>
            <div class="sess-meta pa-muted">{{ s.message_count }} 条 · {{ fmtTime(s.updated_at) }}</div>
          </div>
          <el-button class="sess-del" size="small" type="danger" circle title="删除该对话" @click.stop="removeSession(s)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <div v-if="!sessions.length" class="pa-muted sess-empty">暂无历史对话</div>
      </div>
    </aside>

    <!-- 右栏：对话区 -->
    <section
      class="chat-panel"
      @dragenter.prevent="onDragEnter"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="onDragLeave"
      @drop.prevent="onDrop"
    >
      <div class="chat-head">
        <span class="chat-title">{{ currentTitle }}</span>
        <el-button v-if="!models.length" size="small" class="model-mgr-btn" @click="emit('open-settings', 'ai')">
          模型管理
        </el-button>
      </div>

      <div ref="msgBox" class="msg-list pa-scroll">
        <div v-if="!messages.length && !streaming" class="chat-empty pa-muted">
          输入问题开始对话；支持把图片直接拖拽到本区域，或点输入框左下回形针按钮选择图片。
        </div>

        <div v-for="msg in messages" :key="msg.id" class="msg" :class="msg.role">
          <div class="msg-avatar">{{ msg.role === 'user' ? '我' : 'AI' }}</div>
          <div class="msg-body">
            <div v-for="(b, i) in msg.blocks" :key="`${msg.id}-${i}`" class="msg-block">
              <img
                v-if="b.type === 'image' && b.data"
                :src="b.data"
                :alt="b.name || '图片'"
                class="msg-img"
                @click="viewerSrc = b.data || ''"
              />
              <SearchCards v-else-if="b.type === 'search'" :results="b.results || []" />
              <MdPreview
                v-else
                :model-value="b.text || ''"
                :theme="mdTheme"
                language="zh-CN"
                class="msg-md"
              />
            </div>
            <div v-if="msg.role === 'assistant' && msg.model" class="pa-muted msg-model">{{ msg.model }}</div>
          </div>
        </div>

        <!-- 流式回复中的临时气泡 -->
        <div v-if="streaming" class="msg assistant">
          <div class="msg-avatar">AI</div>
          <div class="msg-body">
            <SearchCards v-if="streamSearch && streamSearch.results.length" :results="streamSearch.results" class="msg-block" />
            <!-- 与存档消息同构：套 msg-block 才能命中透明底覆盖，避免流式期间出现黑色底框 -->
            <div v-if="streamText" class="msg-block">
              <MdPreview :model-value="streamText" :theme="mdTheme" language="zh-CN" class="msg-md" />
            </div>
            <div v-else class="pa-muted streaming-tip">
              <el-icon class="spin"><Loading /></el-icon>
              {{ streamSearch?.results?.length ? '已获取搜索结果，生成中…' : (streamSearch?.error || '思考中…') }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="dragging" class="drop-mask">松开鼠标以附加图片</div>

      <!-- 输入区：单卡片内包含 待发图片 / 文本框 / 底部工具行（附件 + 模型 + 发送） -->
      <div class="composer">
        <el-alert v-if="!settings.aiReady" type="warning" show-icon :closable="false" class="composer-alert">
          尚未配置 AI API Key，请在
          <el-link type="primary" @click="emit('open-settings')">设置 → AI 模型</el-link>
          中填写后再对话。
        </el-alert>

        <div class="composer-card">
          <div v-if="pending.length" class="pending-row">
            <div v-for="(p, i) in pending" :key="`${p.name}-${i}`" class="pending-chip">
              <img :src="p.data" :alt="p.name" />
              <el-icon class="pending-del" title="移除" @click="pending.splice(i, 1)"><CircleClose /></el-icon>
            </div>
          </div>

          <el-input
            v-model="input"
            type="textarea"
            :rows="3"
            resize="none"
            class="composer-input"
            placeholder="输入问题，Enter 发送 / Shift+Enter 换行；↑↓ 翻阅历史问题"
            @keydown.enter.exact.prevent="send"
            @keydown="onComposerKey"
          />

          <div class="composer-bar">
            <el-button class="attach-btn" circle title="附加图片" @click="pickImages">
              <el-icon><Paperclip /></el-icon>
            </el-button>
            <input ref="imgInput" type="file" accept="image/*" multiple style="display: none" @change="onImagesPicked" />
            <el-button
              class="search-toggle"
              :class="{ on: webSearch }"
              size="small"
              round
              title="开启后先联网搜索再作答，并展示搜索来源"
              @click="webSearch = !webSearch"
            >
              <el-icon><Search /></el-icon>&nbsp;联网搜索
            </el-button>
            <span v-if="pending.length" class="pa-muted composer-tip">已附加 {{ pending.length }} 张图片</span>
            <span v-if="streaming" class="pa-muted composer-tip">
              <el-icon class="spin"><Loading /></el-icon> {{ streamText.length }} 字
            </span>
            <div class="composer-spacer" />
            <el-select v-model="modelName" size="small" class="model-sel" filterable placeholder="选择模型">
              <el-option v-for="m in models" :key="m" :label="m" :value="m" />
            </el-select>
            <el-button v-if="!streaming" type="primary" circle title="发送" :disabled="!canSend" @click="send">
              <el-icon><Promotion /></el-icon>
            </el-button>
            <el-button v-else type="danger" circle title="停止" @click="stop">
              <el-icon><VideoPause /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
    </section>

    <el-image-viewer v-if="viewerSrc" :url-list="[viewerSrc]" @close="viewerSrc = ''" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { api, streamChat } from '@/api'
import { useSettingsStore } from '@/stores/settings'
import { useAuthStore } from '@/stores/auth'
import SearchCards from '@/components/assistant/SearchCards.vue'
import type { ChatSessionMeta, ChatMessage, ChatBlock, SearchResult } from '@/types'

const emit = defineEmits<{ (e: 'open-settings', tab?: string): void }>()
const settings = useSettingsStore()
const auth = useAuthStore()

// ---------------- 会话列表 ----------------
const sessions = ref<ChatSessionMeta[]>([])
const currentId = ref('')
const messages = ref<ChatMessage[]>([])
const currentTitle = computed(() => sessions.value.find((s) => s.id === currentId.value)?.title || '新对话')

// ---------------- 输入 / 流式 ----------------
const input = ref('')
// 输入历史：↑/↓ 在输入框中翻阅已发送的问题（随会话加载重建）
const inputHistory = ref<string[]>([])
let histPos = 0 // 指向 inputHistory；等于长度时为当前草稿
let histDraft = ''
const pending = ref<{ data: string; name: string }[]>([])
const streaming = ref(false)
const streamText = ref('')
const streamSearch = ref<{ results: SearchResult[]; error: string } | null>(null)
const dragging = ref(false)
const viewerSrc = ref('')
const msgBox = ref<HTMLElement | null>(null)
const imgInput = ref<HTMLInputElement | null>(null)
let abortFn: (() => void) | null = null
let dragDepth = 0

const canSend = computed(() => !streaming.value && (!!input.value.trim() || pending.value.length > 0))
const mdTheme = computed(() => (settings.theme === 'dark' ? 'dark' : 'light'))

// ---------------- 模型（仅设置中勾选启用的模型） ----------------
const models = ref<string[]>([])
const modelName = ref('')
const lsModelKey = () => `assistant_last_model::${auth.user?.username || ''}`
watch(modelName, (v) => { if (v) localStorage.setItem(lsModelKey(), v) })

// ---------------- 联网搜索开关（按用户记住） ----------------
const webSearch = ref(false)
const lsWebSearchKey = () => `assistant_web_search::${auth.user?.username || ''}`
watch(webSearch, (v) => localStorage.setItem(lsWebSearchKey(), v ? '1' : '0'))

function loadModels() {
  const list = [...(settings.ai.enabled_models || [])]
  models.value = list
  if (!list.includes(modelName.value)) {
    const saved = localStorage.getItem(lsModelKey()) || ''
    modelName.value = list.includes(saved) ? saved : (list[0] || '')
  }
}

// ---------------- 载入 / 切换 / 删除 ----------------
async function loadSessions() {
  try {
    const res = await api.listChatSessions()
    sessions.value = res.sessions || []
  } catch { sessions.value = [] }
}

async function openSession(id: string) {
  if (streaming.value) stop()
  currentId.value = id
  try {
    const s = await api.getChatSession(id)
    messages.value = s.messages || []
  } catch { messages.value = [] }
  rebuildHistory()
  scrollBottom()
}

function newChat() {
  if (streaming.value) stop()
  currentId.value = ''
  messages.value = []
  input.value = ''
  pending.value = []
}

async function removeSession(s: ChatSessionMeta) {
  try {
    await ElMessageBox.confirm(`删除对话「${s.title}」？其中的提问与回复内容将一并删除。`, '确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch { return }
  try {
    await api.deleteChatSession(s.id)
    ElMessage.success('已删除')
    if (currentId.value === s.id) newChat()
    await loadSessions()
  } catch { /* interceptor 提示 */ }
}

function fmtTime(t: string) {
  return (t || '').replace('T', ' ').slice(5, 16)
}

// ---------------- 图片附加（拖拽 / 选择） ----------------
function readImageFile(file: File): Promise<{ data: string; name: string }> {
  return new Promise((resolve, reject) => {
    const fr = new FileReader()
    fr.onload = () => resolve({ data: String(fr.result), name: file.name })
    fr.onerror = () => reject(new Error('read error'))
    fr.readAsDataURL(file)
  })
}

async function addFiles(files: FileList | File[]) {
  for (const f of Array.from(files)) {
    if (!f.type.startsWith('image/')) { ElMessage.warning(`仅支持图片文件：${f.name}`); continue }
    if (f.size > 8 * 1024 * 1024) { ElMessage.warning(`图片过大（单张 <= 8MB）：${f.name}`); continue }
    try {
      pending.value.push(await readImageFile(f))
    } catch { ElMessage.error(`读取图片失败：${f.name}`) }
  }
}

function onDragEnter() { dragDepth += 1; dragging.value = true }
function onDragLeave() {
  dragDepth -= 1
  if (dragDepth <= 0) { dragDepth = 0; dragging.value = false }
}
function onDrop(e: DragEvent) {
  dragDepth = 0
  dragging.value = false
  if (e.dataTransfer?.files?.length) addFiles(e.dataTransfer.files)
}
function pickImages() { imgInput.value?.click() }
function onImagesPicked(e: Event) {
  const el = e.target as HTMLInputElement
  if (el.files) addFiles(el.files)
  el.value = ''
}

// ---------------- 发送 / 停止 ----------------
function scrollBottom() {
  nextTick(() => {
    const el = msgBox.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function reloadCurrent() {
  if (!currentId.value) return
  api.getChatSession(currentId.value)
    .then((s) => { messages.value = s.messages || []; rebuildHistory(); scrollBottom() })
    .catch(() => { /* 会话可能已删除 */ })
}

// 从当前会话的用户消息重建输入历史
function rebuildHistory() {
  inputHistory.value = messages.value
    .filter((m) => m.role === 'user')
    .map((m) => m.blocks.filter((b) => b.type === 'text').map((b) => b.text || '').join('\n'))
    .filter((t) => t.trim())
  histPos = inputHistory.value.length
}

// ↑/↓ 翻阅历史：仅当光标已处于首行/末行时接管，多行编辑中的正常移动不受影响
function onComposerKey(e: KeyboardEvent) {
  if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return
  const el = e.target as HTMLTextAreaElement
  if (e.key === 'ArrowUp') {
    if (el.value.slice(0, el.selectionStart).includes('\n')) return
    e.preventDefault()
    stepHistory(-1, el)
  } else {
    if (el.value.slice(el.selectionEnd).includes('\n')) return
    e.preventDefault()
    stepHistory(1, el)
  }
}
function stepHistory(d: number, el: HTMLTextAreaElement) {
  const h = inputHistory.value
  if (!h.length) return
  if (histPos >= h.length) histDraft = input.value // 离开草稿前先存档
  const next = Math.min(h.length, Math.max(0, histPos + d))
  if (next === histPos) return
  histPos = next
  input.value = next >= h.length ? histDraft : h[next]
  nextTick(() => { el.selectionStart = el.selectionEnd = el.value.length })
}

function send() {
  const text = input.value.trim()
  const images = pending.value.slice()
  if (!text && !images.length) return
  // 本地先渲染用户消息（图片与文字按附加顺序排版）
  const blocks: ChatBlock[] = [
    ...images.map((p) => ({ type: 'image' as const, data: p.data, name: p.name })),
    ...(text ? [{ type: 'text' as const, text }] : [])
  ]
  messages.value.push({ id: `tmp-u-${Date.now()}`, role: 'user', blocks })
  if (text) {
    if (inputHistory.value[inputHistory.value.length - 1] !== text) inputHistory.value.push(text)
    histPos = inputHistory.value.length
  }
  input.value = ''
  pending.value = []
  streaming.value = true
  streamText.value = ''
  streamSearch.value = null
  scrollBottom()

  abortFn = streamChat(
    {
      session_id: currentId.value || null, text, images,
      model: modelName.value || null, web_search: webSearch.value
    },
    {
      onSession: (sid) => {
        if (!currentId.value) currentId.value = sid
        loadSessions()
      },
      onSearch: (s) => {
        streamSearch.value = s
        scrollBottom()
      },
      onDelta: (t) => {
        streamText.value += t
        scrollBottom()
      },
      onDone: async () => {
        if (!streaming.value) return // 流结束事件可能触发两次，防重复收尾
        streaming.value = false
        abortFn = null
        reloadCurrent()
        await loadSessions()
      },
      onError: (msg) => {
        streaming.value = false
        abortFn = null
        ElMessage.error('回复失败：' + msg)
        // 服务端已保存已生成的部分，重新载入展示
        setTimeout(reloadCurrent, 600)
      }
    }
  )
}

function stop() {
  abortFn?.()
  abortFn = null
  streaming.value = false
  streamText.value = ''
  streamSearch.value = null
  ElMessage.info('已停止')
  setTimeout(reloadCurrent, 600)
}

onMounted(async () => {
  await settings.load()
  loadModels()
  webSearch.value = localStorage.getItem(lsWebSearchKey()) === '1'
  await loadSessions()
  // 进入页面自动恢复最近一次对话（内容从 persistent 重加载）
  if (sessions.value.length) await openSession(sessions.value[0].id)
})
onBeforeUnmount(() => { abortFn?.() })
watch(() => settings.ai.enabled_models, loadModels, { deep: true })
</script>

<style scoped>
.assistant-view { display: flex; gap: 14px; height: 100%; min-height: 0; padding: 2px; }

/* 左栏会话列表 */
.sess-panel {
  width: 240px; flex-shrink: 0;
  display: flex; flex-direction: column; gap: 10px;
  padding: 12px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.34), rgba(15, 23, 42, 0.22));
  border: 1px solid rgba(148, 163, 184, 0.12);
}
.sess-head { flex-shrink: 0; }
.new-btn { width: 100%; }
.sess-list { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 6px; overflow-y: auto; }
.sess-item {
  display: flex; align-items: center; gap: 6px;
  padding: 9px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  cursor: pointer;
  transition: background .2s, border-color .2s;
}
.sess-item:hover { background: var(--color-surface-hover); }
.sess-item.active {
  background: linear-gradient(90deg, rgba(245, 158, 11, .16), rgba(245, 158, 11, .04));
  border-color: rgba(245, 158, 11, .35);
}
.sess-text { flex: 1; min-width: 0; }
.sess-title {
  font-size: 13px; font-weight: 600; color: var(--color-text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sess-meta { font-size: 11px; margin-top: 2px; }
.sess-del { flex-shrink: 0; opacity: 0; transition: opacity .2s; }
.sess-item:hover .sess-del { opacity: 1; }
.sess-empty { text-align: center; font-size: 12.5px; padding: 18px 0; }

/* 右栏对话区 */
.chat-panel {
  position: relative;
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 10px;
  padding: 12px 14px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.34), rgba(15, 23, 42, 0.22));
  border: 1px solid rgba(148, 163, 184, 0.12);
}
.chat-head { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.chat-title {
  flex: 1; min-width: 0; font-size: 14px; font-weight: 700; color: var(--color-text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.el-button.model-mgr-btn { background: #0891b2; border-color: #0891b2; color: #fff; font-weight: 600; }

.msg-list { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 14px; padding: 4px 2px; overflow-y: auto; }
.chat-empty { text-align: center; font-size: 13px; padding: 40px 0; line-height: 1.8; }

.msg { display: flex; gap: 10px; align-items: flex-start; }
.msg.user { flex-direction: row-reverse; }
.msg-avatar {
  width: 30px; height: 30px; flex-shrink: 0;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: #1a1206;
}
.msg.assistant .msg-avatar { background: linear-gradient(135deg, #8b5cf6, #6d28d9); color: #fff; }
.msg-body {
  max-width: 78%; min-width: 0;
  display: flex; flex-direction: column; gap: 8px; align-items: flex-start;
}
.msg.user .msg-body { align-items: flex-end; }
.msg-block { width: 100%; }
.msg-img {
  max-width: 320px; max-height: 320px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  cursor: zoom-in; display: block;
}
.msg-md { width: 100%; }
.msg-block :deep(.md-editor) { background: transparent; border: none; }
.msg-block :deep(.md-editor-preview-wrapper) { padding: 0; }
.msg-block :deep(.md-editor-preview) { font-size: 13.5px; color: var(--color-text-primary); }
/* MdPreview 自带暗色文字偏灰暗，统一覆盖为项目文本色 */
.msg-block :deep(.md-editor-preview p),
.msg-block :deep(.md-editor-preview li),
.msg-block :deep(.md-editor-preview h1),
.msg-block :deep(.md-editor-preview h2),
.msg-block :deep(.md-editor-preview h3),
.msg-block :deep(.md-editor-preview h4),
.msg-block :deep(.md-editor-preview h5),
.msg-block :deep(.md-editor-preview h6) { color: var(--color-text-primary); }
.msg-block :deep(.md-editor-preview blockquote) { color: var(--color-text-secondary); }
/* 代码块/行内代码底色与项目色板统一：接近面板底色而非纯黑 */
.msg-block :deep(.md-editor-preview code) { background: var(--color-bg-tertiary); }
.msg-block :deep(.md-editor-preview pre),
.msg-block :deep(.md-editor-preview pre code),
.msg-block :deep(.md-editor-preview [class*="code-"]) { background: var(--color-bg-secondary); }
.msg.user .msg-block :deep(.md-editor-preview) {
  padding: 10px 12px;
  background: rgba(245, 158, 11, .1);
  border: 1px solid rgba(245, 158, 11, .25);
  border-radius: var(--radius-md);
}
.msg-model { font-size: 11px; }
.streaming-tip { display: flex; align-items: center; gap: 6px; font-size: 13px; padding: 6px 2px; }

/* 拖拽遮罩 */
.drop-mask {
  position: absolute; inset: 8px; z-index: 5;
  border: 2px dashed var(--color-primary);
  border-radius: var(--radius-md);
  background: rgba(245, 158, 11, .08);
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 700; color: var(--color-primary);
  pointer-events: none;
}

/* 输入区：参考 Qoder CN 桌面版，附件/模型/发送均收于输入卡片内；限宽并与消息正文左缘对齐 */
.composer {
  flex-shrink: 0; display: flex; flex-direction: column; gap: 8px;
  align-self: flex-start; margin-left: 42px; /* 2(列表内衬) + 30(头像) + 10(间距) = 消息正文左缘 */
  width: calc(100% - 42px); max-width: 860px;
}
.composer-alert { padding: 6px 10px; }
.composer-card {
  display: flex; flex-direction: column; gap: 8px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  transition: border-color .2s;
}
.composer-card:focus-within { border-color: var(--color-border-hover); }
.composer-input :deep(.el-textarea__inner) {
  background: transparent; border: none; box-shadow: none;
  padding: 2px 0; font-size: 13.5px;
}
.pending-row { display: flex; gap: 8px; flex-wrap: wrap; }
.pending-chip { position: relative; width: 64px; height: 64px; }
.pending-chip img {
  width: 100%; height: 100%; object-fit: cover; display: block;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}
.pending-del {
  position: absolute; top: -7px; right: -7px;
  font-size: 17px; color: var(--color-danger, #f56c6c);
  background: var(--color-bg-secondary);
  border-radius: 50%; cursor: pointer;
}
.composer-bar {
  display: flex; align-items: center; gap: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border);
}
.attach-btn {
  background: transparent; border-color: var(--color-border);
  color: var(--color-text-secondary);
}
.attach-btn:hover, .attach-btn:focus {
  background: transparent; border-color: var(--color-primary); color: var(--color-primary);
}
.model-sel { width: 160px; flex-shrink: 0; }
/* 模型选择框：透明底 + 卡片同款描边，融入输入卡片 */
.model-sel :deep(.el-select__wrapper) {
  background: transparent;
  box-shadow: 0 0 0 1px var(--color-border) inset;
  border-radius: 8px;
  min-height: 28px;
  padding: 0 8px;
}
.model-sel :deep(.el-select__wrapper:hover),
.model-sel :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--color-border-hover) inset;
}
.model-sel :deep(.el-select__selected-item),
.model-sel :deep(.el-select__placeholder) {
  color: var(--color-text-secondary); font-size: 12px;
}
.model-sel :deep(.el-select__caret) { color: var(--color-text-muted); }
.search-toggle {
  background: transparent; border-color: var(--color-border);
  color: var(--color-text-secondary); font-size: 12px;
}
.search-toggle:hover, .search-toggle:focus {
  background: transparent; border-color: var(--color-info); color: var(--color-info);
}
.search-toggle.on {
  background: rgba(59, 130, 246, .15); border-color: var(--color-info);
  color: var(--color-info); font-weight: 600;
}
.composer-tip { font-size: 12px; display: flex; align-items: center; gap: 5px; }
.composer-spacer { flex: 1; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 900px) {
  .assistant-view { flex-direction: column; }
  .sess-panel { width: 100%; max-height: 180px; }
}
</style>
