<template>
  <div class="report-view pa-scroll">
    <!-- 框栏 1：周报生成 -->
    <section class="panel-section">
      <h3 class="section-title">
        <el-icon><MagicStick /></el-icon>
        周报生成
      </h3>

      <div class="gen-grid">
        <!-- 第一列：日期（周） -->
        <div class="gen-col">
          <div class="col-head">日期（周）</div>
          <div class="week-col">
            <button class="week-picker-btn" @click="weekPickerVisible = true">
              {{ pickYear }}年{{ pickWeek }}周
              <el-icon class="caret"><ArrowDown /></el-icon>
            </button>
            <div class="week-range">{{ weekRangeText }}</div>
          </div>
        </div>

        <!-- 第二列：模板与署名 + 生成按钮 -->
        <div class="gen-col">
          <div class="col-head">模板与署名</div>
          <div class="ctrl-line">
            <span class="ctrl-label">选择模板</span>
            <el-select v-model="templateName" size="small" class="ctrl-sel" placeholder="选择模板">
              <el-option v-for="t in templates" :key="t.name" :label="t.name" :value="t.name" />
            </el-select>
          </div>
          <div class="ctrl-line">
            <span class="ctrl-label">选择署名</span>
            <el-select v-model="author" size="small" class="ctrl-sel" placeholder="选择署名">
              <el-option v-for="a in authors" :key="a" :label="a" :value="a" />
            </el-select>
          </div>
          <div class="ctrl-line">
            <el-button size="small" class="tpl-load-btn" @click="pickTemplateFile">模板加载</el-button>
            <input
              ref="fileInput"
              type="file"
              accept=".md,text/markdown"
              style="display: none"
              @change="onTemplatePicked"
            />
            <el-button size="small" class="author-mgr-btn" @click="openAuthorMgr">署名管理</el-button>
          </div>
          <div class="ctrl-line">
            <el-button v-if="!generating" type="primary" :disabled="!canGenerate" @click="generate()">
              <el-icon><MagicStick /></el-icon>&nbsp;生成周报
            </el-button>
            <el-button v-else type="danger" @click="stop">
              <el-icon><VideoPause /></el-icon>&nbsp;停止
            </el-button>
            <span v-if="generating" class="pa-muted gen-inline">
              <el-icon class="spin"><Loading /></el-icon> {{ genElapsed }}s · {{ genChars }} 字
            </span>
          </div>
        </div>

        <!-- 第三列：模型 -->
        <div class="gen-col">
          <div class="col-head">模型</div>
          <div class="ctrl-line">
            <span class="ctrl-label">模型选择</span>
            <el-select v-model="modelName" size="small" class="ctrl-sel" filterable placeholder="选择模型">
              <el-option v-for="m in models" :key="m" :label="m" :value="m" />
            </el-select>
          </div>
          <div class="ctrl-line">
            <el-button size="small" class="model-mgr-btn" @click="emit('open-settings', 'ai')">模型管理</el-button>
            <el-button size="small" class="prompt-btn" @click="openPromptDialog">提示词</el-button>
          </div>
          <div v-if="!models.length" class="pa-muted col-tip">暂无已启用模型，点「模型管理」去设置中勾选</div>
        </div>
      </div>

      <!-- 生成进度：耗时 / 字数 / 流式预览 -->
      <div v-if="generating" class="gen-progress">
        <div class="gp-head">
          <el-icon class="spin"><Loading /></el-icon>
          <span>生成中：已耗时 {{ genElapsed }} 秒 · 已接收 {{ genChars }} 字</span>
          <span class="pa-muted">（完成后自动存入下方列表）</span>
        </div>
        <div ref="previewBox" class="gp-preview pa-scroll">{{ genPreview }}</div>
      </div>

      <el-alert v-if="!settings.aiReady" type="warning" show-icon :closable="false" title="尚未配置 AI API Key">
        <template #default>
          请在设置中填写服务商 API Key 后才能生成周报。
          <el-link type="primary" @click="emit('open-settings')">去设置</el-link>
        </template>
      </el-alert>
    </section>

    <!-- 框栏 2：周报编辑（已保存列表） -->
    <section class="panel-section">
      <h3 class="section-title">
        <el-icon><Document /></el-icon>
        周报编辑
      </h3>

      <div class="points-list">
        <div v-for="r in reports" :key="r.id" class="point-item">
          <div class="point-info">
            <span class="point-name">{{ r.title || fallbackTitle(r) }}</span>
            <span class="point-desc pa-muted">{{ r.week_start }} ~ {{ r.week_end }} · {{ r.model }}</span>
          </div>
          <div class="point-actions">
            <el-button size="small" class="export-btn" circle title="导出" @click="exportReport(r)">
              <el-icon><Download /></el-icon>
            </el-button>
            <el-button size="small" type="warning" circle title="编辑" @click="openEdit(r)">
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button size="small" type="danger" circle title="删除" @click="remove(r)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
        <div v-if="!reports.length" class="empty-points">暂无已保存的周报</div>
      </div>
    </section>

    <!-- 编辑 / 新建 弹窗 -->
    <el-dialog
      v-model="editorVisible"
      :title="editorTitle"
      width="920px"
      top="6vh"
      :close-on-click-modal="false"
    >
      <MdEditor
        v-model="editorMd"
        :theme="settings.theme === 'dark' ? 'dark' : 'light'"
        language="zh-CN"
        :preview="true"
        :toolbars-exclude="['github', 'save']"
        style="height: 58vh"
      />
      <template #footer>
        <span v-if="generating" class="pa-muted gen-hint">
          <el-icon class="spin"><Loading /></el-icon> AI 正在生成…
        </span>
        <el-button @click="editorVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="!editorMd.trim()" @click="saveEditor">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 年-周 滚轮选择弹窗 -->
    <el-dialog v-model="weekPickerVisible" title="选择年份与周" width="380px">
      <div class="tumbler">
        <div class="t-wrap">
          <div class="t-head">年</div>
          <TumblerColumn v-model="pickYear" :options="yearOpts" :rows="5" :item-h="30" />
        </div>
        <div class="t-wrap">
          <div class="t-head">周</div>
          <TumblerColumn v-model="pickWeek" :options="weekOpts" :rows="5" :item-h="30" />
        </div>
      </div>
      <template #footer>
        <el-button @click="weekPickerVisible = false">取消</el-button>
        <el-button type="primary" @click="weekPickerVisible = false">确定</el-button>
      </template>
    </el-dialog>

    <!-- 署名管理弹窗 -->
    <el-dialog v-model="authorMgrVisible" title="署名管理" width="440px">
      <div class="author-mgr">
        <div v-for="(a, i) in authorDraft" :key="`${a}-${i}`" class="author-row">
          <el-input
            v-if="editingIdx === i"
            v-model="editText"
            size="small"
            class="author-input"
            @keyup.enter="commitEdit"
          />
          <span v-else class="author-name">{{ a }}</span>
          <div class="author-ops">
            <el-button v-if="editingIdx !== i" size="small" text @click="startEdit(i)">编辑</el-button>
            <el-button v-else size="small" text type="primary" @click="commitEdit">保存</el-button>
            <el-button size="small" text type="danger" @click="removeAuthor(i)">删除</el-button>
          </div>
        </div>
        <div v-if="!authorDraft.length" class="pa-muted author-empty">暂无署名，请在下方添加</div>
        <div class="author-add">
          <el-input v-model="newAuthor" size="small" placeholder="输入新署名" @keyup.enter="addAuthor" />
          <el-button size="small" type="primary" @click="addAuthor">添加</el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="authorMgrVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 提示词编辑弹窗 -->
    <el-dialog v-model="promptVisible" title="提示词（system / user）" width="760px" :close-on-click-modal="false">
      <div class="pa-muted prompt-tip">
        「保存」仅保存草稿（下次打开默认显示）；「保存并生成」保存后立即按下方 prompt 执行本次生成；
        外部「生成周报」按钮仍使用系统按当周数据自动构建的 prompt。
      </div>
      <div class="prompt-field">
        <div class="prompt-label">System Prompt</div>
        <el-input v-model="promptSystem" type="textarea" :rows="9" />
      </div>
      <div class="prompt-field">
        <div class="prompt-label">User Prompt</div>
        <el-input v-model="promptUser" type="textarea" :rows="12" />
      </div>
      <template #footer>
        <el-button size="small" @click="fillBuiltPrompt">恢复默认构建</el-button>
        <el-button size="small" type="primary" :loading="promptSaving" @click="savePromptDraftOnly">保存</el-button>
        <el-button size="small" type="success" :loading="promptSaving" @click="savePromptAndGenerate">保存并生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import TumblerColumn from '@/components/calendar/TumblerColumn.vue'
import { api, streamReport } from '@/api'
import { useSettingsStore } from '@/stores/settings'
import { useAuthStore } from '@/stores/auth'
import { mondayOfWeek } from '@/utils/date'
import type { WeekData, ReportRecord, TemplateItem } from '@/types'

const emit = defineEmits<{ (e: 'open-settings', tab?: string): void }>()
const settings = useSettingsStore()
const auth = useAuthStore()

// ---------------- 年-周 滚轮 ----------------
const pickYear = ref(dayjs().year())
const pickWeek = ref(dayjs().isoWeek())
const weekPickerVisible = ref(false)
const yearOpts = computed(() => {
  const cur = dayjs().year()
  return Array.from({ length: 11 }, (_, i) => ({ value: cur - 5 + i, label: String(cur - 5 + i) }))
})
const weekOpts = computed(() => {
  const n = dayjs(`${pickYear.value}-12-28`).isoWeek()
  return Array.from({ length: n }, (_, i) => ({ value: i + 1, label: `第 ${i + 1} 周` }))
})
const monday = computed(() =>
  mondayOfWeek(dayjs(`${pickYear.value}-01-04`).isoWeek(pickWeek.value)).format('YYYY-MM-DD')
)
const sunday = computed(() => dayjs(monday.value).add(6, 'day').format('YYYY-MM-DD'))
const weekRangeText = computed(() => `${dayjs(monday.value).format('YYYY.MM.DD')}~${dayjs(sunday.value).format('YYYY.MM.DD')}`)

// ---------------- 生成配置 ----------------
const templates = ref<TemplateItem[]>([])
const templateName = ref('')
const models = ref<string[]>([])
const modelName = ref('')
const author = ref('')

// 记住最后一次使用的选项（模板/模型/署名），下次进入优先恢复
const LS_TEMPLATE = 'report_last_template'
const LS_MODEL = 'report_last_model'
const lsAuthorKey = () => `report_last_author::${auth.user?.username || ''}`
watch(templateName, (v) => { if (v) localStorage.setItem(LS_TEMPLATE, v) })
watch(modelName, (v) => { if (v) localStorage.setItem(LS_MODEL, v) })
watch(author, (v) => { if (v) localStorage.setItem(lsAuthorKey(), v) })

// 署名管理
const authors = ref<string[]>([])
const authorMgrVisible = ref(false)
const authorDraft = ref<string[]>([])
const newAuthor = ref('')
const editingIdx = ref(-1)
const editText = ref('')

// 生成进度
const genChars = ref(0)
const genElapsed = ref(0)
const genPreview = ref('')
const previewBox = ref<HTMLElement | null>(null)
let genTimer: number | null = null
let genStartAt = 0

// ---------------- 数据 ----------------
const weekData = ref<WeekData | null>(null)
const reports = ref<ReportRecord[]>([])
const totalCount = computed(() => weekData.value?.summary.total ?? 0)
const canGenerate = computed(() => settings.aiReady && totalCount.value > 0)

// ---------------- 编辑器 ----------------
const editorVisible = ref(false)
const editorMd = ref('')
const editingRecord = ref<ReportRecord | null>(null)
const generating = ref(false)
const saving = ref(false)
let abortFn: (() => void) | null = null
const editorTitle = computed(() =>
  editingRecord.value ? `编辑：${editingRecord.value.title || fallbackTitle(editingRecord.value)}` : '新建周报'
)

function fallbackTitle(r: ReportRecord): string {
  const m = /(\d{4})-W(\d{2})/.exec(r.week_id || '')
  const yw = m ? `${m[1]}年${parseInt(m[2], 10)}周周报` : r.week_id
  return `${yw}--${r.author || ''}`
}

async function loadWeek() {
  try { weekData.value = await api.weekData(monday.value) } catch { weekData.value = null }
}
async function loadTemplates() {
  try {
    const res = await api.listTemplates()
    templates.value = res.templates || []
    if (!templateName.value && templates.value.length) {
      // 优先用上次选择的模板，已不存在则回落第一个
      const saved = localStorage.getItem(LS_TEMPLATE) || ''
      templateName.value = templates.value.some((t) => t.name === saved) ? saved : templates.value[0].name
    }
  } catch { templates.value = [] }
}
async function loadModels() {
  // 仅显示「设置 → AI 可用列表」中勾选启用的模型
  const list = [...(settings.ai.enabled_models || [])]
  models.value = list
  if (!list.includes(modelName.value)) {
    // 优先用上次选择的模型，已禁用则回落第一个
    const saved = localStorage.getItem(LS_MODEL) || ''
    modelName.value = list.includes(saved) ? saved : (list[0] || '')
  }
}
async function loadAuthors() {
  try {
    const res = await api.listAuthors()
    authors.value = res.authors || []
    // 优先用上次选择的署名，已不存在则回落用户默认署名/第一个
    const saved = localStorage.getItem(lsAuthorKey()) || ''
    if (saved && authors.value.includes(saved)) author.value = saved
    else if (!authors.value.includes(author.value)) author.value = authors.value[0] || author.value
  } catch { authors.value = [] }
}
async function loadReports() {
  try {
    const res = await api.listReports()
    const list = res.reports || []
    list.sort((a, b) => (b.generated_at || '').localeCompare(a.generated_at || ''))
    reports.value = list
  } catch { reports.value = [] }
}

// ---------------- 生成 / 模板 / 编辑 ----------------
function clearGenTimer() {
  if (genTimer !== null) {
    clearInterval(genTimer)
    genTimer = null
  }
}
function generate(override?: { system: string; user: string } | null) {
  let buf = ''
  generating.value = true
  genChars.value = 0
  genElapsed.value = 0
  genPreview.value = ''
  genStartAt = Date.now()
  clearGenTimer()
  genTimer = window.setInterval(() => {
    genElapsed.value = Math.round((Date.now() - genStartAt) / 1000)
  }, 1000)
  abortFn = streamReport(monday.value, {
    onDelta: (t) => {
      buf += t
      genChars.value = buf.length
      genPreview.value = buf
    },
    onDone: async () => {
      if (!generating.value) return // streamReport 可能触发两次 onDone，防重复保存
      generating.value = false
      abortFn = null
      clearGenTimer()
      genPreview.value = ''
      const md = buf.trim()
      if (!md) { ElMessage.warning('未生成任何内容'); return }
      try {
        const rec = await api.saveReport(monday.value, md, author.value, modelName.value)
        if (author.value.trim() && auth.user) auth.user.report_author = author.value.trim()
        await loadReports()
        ElMessage.success(`已生成并保存：${rec.title}`)
      } catch { /* interceptor 提示 */ }
    },
    onError: (msg) => {
      generating.value = false
      abortFn = null
      clearGenTimer()
      genPreview.value = ''
      ElMessage.error('生成失败：' + msg)
    }
  }, { model: modelName.value, template: templateName.value, author: author.value, prompt: override || null })
}
function stop() {
  abortFn?.()
  abortFn = null
  generating.value = false
  clearGenTimer()
  genPreview.value = ''
  ElMessage.info('已停止')
}

const fileInput = ref<HTMLInputElement | null>(null)
function pickTemplateFile() {
  fileInput.value?.click()
}

// ---------------- 提示词编辑 ----------------
const promptVisible = ref(false)
const promptSystem = ref('')
const promptUser = ref('')
const promptBuilt = ref<{ system: string; user: string } | null>(null)
const promptSaving = ref(false)

async function openPromptDialog() {
  promptVisible.value = true
  try {
    const data = await api.getPrompt({ start: monday.value, template: templateName.value || null, author: author.value })
    promptBuilt.value = data.built
    const cur = data.saved || data.built
    promptSystem.value = cur.system
    promptUser.value = cur.user
  } catch { /* interceptor 提示 */ }
}
function fillBuiltPrompt() {
  if (!promptBuilt.value) return
  promptSystem.value = promptBuilt.value.system
  promptUser.value = promptBuilt.value.user
}
async function persistPrompt(): Promise<boolean> {
  promptSaving.value = true
  try {
    await api.savePrompt(promptSystem.value, promptUser.value)
    return true
  } catch { return false } finally { promptSaving.value = false }
}
async function savePromptDraftOnly() {
  if (await persistPrompt()) ElMessage.success('提示词已保存')
}
async function savePromptAndGenerate() {
  if (!(await persistPrompt())) return
  promptVisible.value = false
  generate({ system: promptSystem.value, user: promptUser.value })
}
async function onTemplatePicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 允许再次选择同一文件
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.md')) {
    ElMessage.warning('请选择 .md 模板文件')
    return
  }
  try {
    const text = await file.text()
    const item = await api.uploadTemplate(file.name, text)
    await loadTemplates()
    templateName.value = item.name
    ElMessage.success(`已导入模板：${item.name}`)
  } catch { /* interceptor 提示 */ }
}

// ---------------- 署名管理 ----------------
function openAuthorMgr() {
  authorDraft.value = [...authors.value]
  editingIdx.value = -1
  editText.value = ''
  newAuthor.value = ''
  authorMgrVisible.value = true
}
async function persistAuthors() {
  try {
    const res = await api.setAuthors(authorDraft.value)
    authors.value = res.authors || []
    if (authors.value.length && !authors.value.includes(author.value)) author.value = authors.value[0]
  } catch { /* interceptor 提示 */ }
}
function addAuthor() {
  const name = newAuthor.value.trim()
  if (!name) { ElMessage.warning('请输入署名'); return }
  if (authorDraft.value.includes(name)) { ElMessage.info('该署名已存在'); return }
  authorDraft.value.push(name)
  newAuthor.value = ''
  persistAuthors()
}
function startEdit(i: number) {
  editingIdx.value = i
  editText.value = authorDraft.value[i]
}
function commitEdit() {
  const i = editingIdx.value
  if (i < 0) return
  const name = editText.value.trim()
  if (!name) { ElMessage.warning('署名不能为空'); return }
  if (authorDraft.value.some((a, j) => a === name && j !== i)) { ElMessage.info('该署名已存在'); return }
  authorDraft.value[i] = name
  editingIdx.value = -1
  persistAuthors()
}
function removeAuthor(i: number) {
  if (authorDraft.value.length <= 1) { ElMessage.warning('至少保留一个署名'); return }
  authorDraft.value.splice(i, 1)
  if (editingIdx.value === i) editingIdx.value = -1
  persistAuthors()
}

async function openEdit(r: ReportRecord) {
  try {
    const detail = await api.getReport(r.id)
    editingRecord.value = r
    editorMd.value = detail.content || ''
    editorVisible.value = true
  } catch { /* interceptor 提示 */ }
}

async function saveEditor() {
  if (!editorMd.value.trim()) return
  saving.value = true
  try {
    if (editingRecord.value) {
      await api.updateReport(editingRecord.value.id, editorMd.value)
      ElMessage.success('已更新')
    } else {
      const rec = await api.saveReport(monday.value, editorMd.value, author.value, modelName.value)
      if (author.value.trim()) auth.user && (auth.user.report_author = author.value.trim())
      ElMessage.success(`已保存：${rec.title}`)
    }
    editorVisible.value = false
    await loadReports()
  } catch { /* interceptor 提示 */ } finally {
    saving.value = false
  }
}

async function exportReport(r: ReportRecord) {
  try {
    const detail = await api.getReport(r.id)
    const name = (r.title || fallbackTitle(r)).replace(/[\\/:*?"<>|]/g, '_')
    const blob = new Blob([detail.content || ''], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${name}.md`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success(`已导出：${name}.md`)
  } catch { /* interceptor 提示 */ }
}

async function remove(r: ReportRecord) {
  try {
    await ElMessageBox.confirm(`删除周报「${r.title || fallbackTitle(r)}」？`, '确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch { return }
  try {
    await api.deleteReport(r.id)
    ElMessage.success('已删除')
    await loadReports()
  } catch { /* interceptor 提示 */ }
}

onMounted(async () => {
  await settings.load()
  author.value = auth.user?.report_author || auth.user?.username || ''
  await Promise.all([loadWeek(), loadTemplates(), loadModels(), loadReports(), loadAuthors()])
})
onBeforeUnmount(() => {
  abortFn?.()
  clearGenTimer()
})
watch(monday, loadWeek)
watch(() => settings.ai.enabled_models, loadModels, { deep: true })
// 流式预览自动滚到底部
watch(genPreview, async () => {
  await nextTick()
  const el = previewBox.value
  if (el) el.scrollTop = el.scrollHeight
})
</script>

<style scoped>
.report-view { display: flex; flex-direction: column; gap: 14px; height: 100%; padding: 2px; }

/* 框栏卡片（参考点位管理风格） */
.panel-section {
  padding: 14px 16px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.34), rgba(15, 23, 42, 0.22));
  border: 1px solid rgba(148, 163, 184, 0.12);
  box-shadow: 0 10px 24px rgba(2, 6, 23, 0.12);
}
.section-title {
  margin: 0 0 12px 0;
  font-size: 13px; font-weight: 600;
  color: var(--color-text-secondary);
  display: flex; align-items: center; gap: 6px;
  letter-spacing: .5px;
}
.section-title .el-icon { font-size: 14px; color: var(--color-primary); }

.week-picker-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 9px 18px;
  font-size: 17px; font-weight: 700;
  color: var(--color-primary);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: border-color .2s, background .2s;
}
.week-picker-btn:hover { border-color: var(--color-primary); }
.week-picker-btn .caret { font-size: 12px; color: var(--color-text-secondary); }
.week-col { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
.week-range { color: #fff; font-size: 13px; font-weight: 600; letter-spacing: .5px; }
.tumbler { display: flex; gap: 18px; justify-content: center; }
.el-button.tpl-load-btn { background: #f5c518; border-color: #f5c518; color: #231a03; font-weight: 600; }
.el-button.tpl-load-btn:hover, .el-button.tpl-load-btn:focus { background: #ffd83d; border-color: #ffd83d; color: #231a03; }
.el-button.export-btn { background: #7c3aed; border-color: #7c3aed; color: #fff; }
.el-button.export-btn:hover, .el-button.export-btn:focus { background: #8b5cf6; border-color: #8b5cf6; color: #fff; }
.el-button.author-mgr-btn { background: #16a34a; border-color: #16a34a; color: #fff; font-weight: 600; }
.el-button.author-mgr-btn:hover, .el-button.author-mgr-btn:focus { background: #22c55e; border-color: #22c55e; color: #fff; }
.el-button.model-mgr-btn { background: #0891b2; border-color: #0891b2; color: #fff; font-weight: 600; }
.el-button.model-mgr-btn:hover, .el-button.model-mgr-btn:focus { background: #06b6d4; border-color: #06b6d4; color: #fff; }
.el-button.prompt-btn { background: #ea580c; border-color: #ea580c; color: #fff; font-weight: 600; }
.el-button.prompt-btn:hover, .el-button.prompt-btn:focus { background: #f97316; border-color: #f97316; color: #fff; }
.t-wrap { display: flex; flex-direction: column; align-items: center; width: 92px; }
.t-head {
  font-size: 12px; color: var(--color-text-secondary);
  padding-bottom: 3px; margin-bottom: 3px; width: 100%; text-align: center;
  border-bottom: 1px solid var(--color-border);
}
/* 生成区三列子框 */
.gen-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.gen-col {
  display: flex; flex-direction: column; gap: 10px;
  min-width: 0;
  padding: 12px 14px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: var(--radius-md);
  background: var(--color-bg-secondary);
}
.col-head { font-size: 12px; font-weight: 600; color: var(--color-text-secondary); letter-spacing: .5px; }
.col-tip { font-size: 12px; line-height: 1.5; }
.ctrl-line { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ctrl-label { font-size: 12.5px; color: var(--color-text-secondary); width: 62px; flex: 0 0 auto; }
.ctrl-sel { flex: 1; min-width: 120px; }

/* 生成进度 */
.gen-progress {
  margin-top: 12px;
  padding: 10px 12px;
  display: flex; flex-direction: column; gap: 8px;
  border: 1px dashed rgba(245, 197, 24, 0.45);
  border-radius: var(--radius-md);
}
.gp-head { display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--color-text-secondary); }
.gp-preview {
  max-height: 180px; min-height: 90px;
  padding: 8px 10px;
  white-space: pre-wrap; word-break: break-word;
  font-size: 12px; line-height: 1.6;
  font-family: ui-monospace, Consolas, monospace;
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
}

/* 署名管理 */
.author-mgr { display: flex; flex-direction: column; gap: 8px; }
.author-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.author-name { font-size: 13px; color: var(--color-text-primary); }

/* 提示词编辑 */
.prompt-tip { margin-bottom: 10px; font-size: 12px; line-height: 1.6; }
.prompt-field { margin-bottom: 12px; }
.prompt-label { margin-bottom: 4px; font-size: 13px; font-weight: 600; }
.prompt-field :deep(.el-textarea__inner) { font-family: Consolas, 'Courier New', monospace; font-size: 12px; }
.author-input { flex: 1; }
.author-ops { display: flex; gap: 2px; flex: 0 0 auto; }
.author-empty { text-align: center; padding: 12px 0; font-size: 13px; }
.author-add { display: flex; gap: 8px; margin-top: 4px; }

/* 周报列表（参考点位列表风格） */
.points-list {
  max-height: min(46vh, 420px);
  min-height: 120px;
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-secondary);
}
.point-item {
  display: flex; justify-content: space-between; align-items: center; gap: 8px;
  padding: 10px 14px;
  transition: background .2s ease;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
}
.point-item:last-child { border-bottom: none; }
.point-item:hover { background: rgba(148, 163, 184, 0.06); }
.point-info { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.point-name {
  font-size: 13px; font-weight: 600; color: var(--color-text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.point-desc { font-size: 11px; }
.point-actions { display: flex; gap: 4px; flex: 0 0 auto; }
.empty-points { padding: 24px; text-align: center; color: var(--color-text-secondary); font-size: 13px; }

.gen-hint { font-size: 12px; display: flex; align-items: center; gap: 5px; margin-right: auto; }
.gen-inline { font-size: 12px; display: flex; align-items: center; gap: 5px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 900px) {
  .gen-grid { grid-template-columns: 1fr; }
}
</style>
