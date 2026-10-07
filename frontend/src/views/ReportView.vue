<template>
  <div class="report-view">
    <!-- 顶部：周选择 + 操作 -->
    <div class="toolbar pa-card">
      <div class="tb-left">
        <el-button-group>
          <el-button @click="shiftWeek(-1)"><el-icon><ArrowLeft /></el-icon></el-button>
          <el-button @click="goThisWeek">本周</el-button>
          <el-button @click="shiftWeek(1)"><el-icon><ArrowRight /></el-icon></el-button>
        </el-button-group>
        <el-date-picker
          v-model="pickerDate"
          type="date"
          placeholder="跳转到某周"
          value-format="YYYY-MM-DD"
          style="width: 150px"
          @change="onPickDate"
        />
        <div class="week-info">
          <div class="week-range">{{ rangeText }}</div>
          <div class="week-id pa-muted">{{ weekData?.week_id || '' }}</div>
        </div>
      </div>

      <div class="tb-right">
        <el-tag size="small" type="info" effect="plain">{{ settings.ai.model }}</el-tag>
        <el-button v-if="!generating" type="primary" :disabled="!canGenerate" @click="generate">
          <el-icon><MagicStick /></el-icon>&nbsp;生成周报
        </el-button>
        <el-button v-else type="danger" @click="stop">
          <el-icon><VideoPause /></el-icon>&nbsp;停止
        </el-button>
        <el-button :disabled="!markdown.trim() || saving" :loading="saving" @click="save">
          <el-icon><FolderChecked /></el-icon>&nbsp;保存 .md
        </el-button>
        <el-button :disabled="!markdown.trim()" @click="copy">
          <el-icon><CopyDocument /></el-icon>&nbsp;复制
        </el-button>
      </div>
    </div>

    <!-- AI 未配置提示 -->
    <el-alert
      v-if="!settings.aiReady"
      type="warning"
      show-icon
      :closable="false"
      title="尚未配置 AI API Key"
    >
      <template #default>
        请在设置中填写阿里云百炼（Qwen）等服务商的 API Key 后才能生成周报。
        <el-link type="primary" @click="emit('open-settings')">去设置</el-link>
      </template>
    </el-alert>

    <!-- 本周统计 -->
    <div v-if="weekData" class="stats pa-card">
      <div class="stat">
        <div class="stat-num">{{ weekData.summary.total }}</div>
        <div class="stat-label pa-muted">总任务</div>
      </div>
      <div class="stat">
        <div class="stat-num ok">{{ weekData.summary.done }}</div>
        <div class="stat-label pa-muted">已完成</div>
      </div>
      <div class="stat">
        <div class="stat-num">{{ weekData.summary.total - weekData.summary.done }}</div>
        <div class="stat-label pa-muted">未完成</div>
      </div>
      <div class="stat">
        <div class="stat-num primary">{{ rateText }}</div>
        <div class="stat-label pa-muted">完成率</div>
      </div>
      <div class="stat-days">
        <div v-for="d in weekData.days" :key="d.date" class="stat-day">
          <div class="sd-bar">
            <div class="sd-fill" :style="{ height: barH(d) }" />
          </div>
          <div class="sd-label pa-muted">{{ wdShort(d.date) }}</div>
        </div>
      </div>
    </div>

    <!-- 主体：编辑器 + 历史 -->
    <div class="body">
      <section class="editor-wrap pa-card">
        <div class="panel-head">
          <span class="panel-title">周报内容</span>
          <span v-if="generating" class="pa-muted gen-hint">
            <el-icon class="spin"><Loading /></el-icon> AI 正在生成…
          </span>
          <span v-else-if="!markdown" class="pa-muted gen-hint">点击「生成周报」，或直接在下方编辑</span>
        </div>
        <MdEditor
          v-model="markdown"
          :theme="settings.theme === 'dark' ? 'dark' : 'light'"
          language="zh-CN"
          :preview="true"
          :toolbars-exclude="['github', 'save']"
          style="height: 100%"
        />
      </section>

      <aside class="history pa-card pa-scroll">
        <div class="panel-head">
          <span class="panel-title">历史周报</span>
          <el-button text size="small" @click="loadHistory"><el-icon><Refresh /></el-icon></el-button>
        </div>
        <div v-if="history.length" class="hist-list">
          <div
            v-for="h in history"
            :key="h.id"
            class="hist-item"
            :class="{ active: h.id === activeHistoryId }"
            @click="openHistory(h)"
          >
            <div class="hist-week">{{ h.week_id }}</div>
            <div class="hist-meta pa-muted">{{ h.week_start }} ~ {{ h.week_end }}</div>
            <div class="hist-meta pa-muted">
              {{ h.model }} · 完成 {{ h.stats.done }}/{{ h.stats.total }}
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无历史周报" :image-size="60" />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { api, streamReport } from '@/api'
import { useSettingsStore } from '@/stores/settings'
import { mondayOfWeek, today, WEEK_CN } from '@/utils/date'
import type { WeekData, ReportRecord } from '@/types'

const emit = defineEmits<{ (e: 'open-settings'): void }>()
const settings = useSettingsStore()

const monday = ref(mondayOfWeek(today()).format('YYYY-MM-DD'))
const pickerDate = ref('')
const weekData = ref<WeekData | null>(null)
const markdown = ref('')
const generating = ref(false)
const saving = ref(false)
const history = ref<ReportRecord[]>([])
const activeHistoryId = ref('')
let abortFn: (() => void) | null = null

const sunday = computed(() => dayjs(monday.value).add(6, 'day').format('YYYY-MM-DD'))
const rangeText = computed(() => `${dayjs(monday.value).format('YYYY年M月D日')} ~ ${dayjs(sunday.value).format('M月D日')}`)
const rateText = computed(() => {
  const s = weekData.value?.summary
  return s ? `${Math.round(s.rate * 100)}%` : '—'
})
const canGenerate = computed(() => settings.aiReady && (weekData.value?.summary.total ?? 0) > 0)

function wdShort(date: string) {
  return WEEK_CN[dayjs(date).day() === 0 ? 6 : dayjs(date).day() - 1].replace('周', '')
}
function barH(d: { total: number; done: number }) {
  if (!d.total) return '6%'
  return `${Math.max(8, Math.round((d.done / d.total) * 100))}%`
}

async function loadWeek() {
  try {
    weekData.value = await api.weekData(monday.value)
  } catch { weekData.value = null }
}

function shiftWeek(delta: number) {
  monday.value = dayjs(monday.value).add(delta * 7, 'day').format('YYYY-MM-DD')
}
function goThisWeek() {
  monday.value = mondayOfWeek(today()).format('YYYY-MM-DD')
}
function onPickDate(v: string) {
  if (v) monday.value = mondayOfWeek(v).format('YYYY-MM-DD')
}

function generate() {
  activeHistoryId.value = ''
  markdown.value = ''
  generating.value = true
  abortFn = streamReport(monday.value, {
    onDelta: (t) => { markdown.value += t },
    onDone: () => { generating.value = false; abortFn = null },
    onError: (msg) => {
      generating.value = false
      abortFn = null
      ElMessage.error('生成失败：' + msg)
    }
  })
}
function stop() {
  abortFn?.()
  abortFn = null
  generating.value = false
  ElMessage.info('已停止')
}

async function save() {
  if (!markdown.value.trim()) return
  saving.value = true
  try {
    const rec = await api.saveReport(monday.value, markdown.value)
    ElMessage.success(`已保存到 weekly_report_output/${rec.file.split('/').pop()}`)
    await loadHistory()
  } catch { /* interceptor 提示 */ } finally {
    saving.value = false
  }
}

async function copy() {
  try {
    await navigator.clipboard.writeText(markdown.value)
    ElMessage.success('已复制到剪贴板')
  } catch { ElMessage.warning('复制失败，请手动选择文本') }
}

async function loadHistory() {
  try {
    const res = await api.listReports()
    history.value = res.reports || []
  } catch { history.value = [] }
}

async function openHistory(h: ReportRecord) {
  activeHistoryId.value = h.id
  try {
    const detail = await api.getReport(h.id)
    markdown.value = detail.content || ''
  } catch { /* interceptor 提示 */ }
}

onMounted(async () => {
  await settings.load()
  await Promise.all([loadWeek(), loadHistory()])
})

onBeforeUnmount(() => { abortFn?.() })

// 周变化时重新加载数据
watch(monday, loadWeek)
</script>

<style scoped>
.report-view { display: flex; flex-direction: column; gap: 14px; height: 100%; }

.toolbar { padding: 14px 16px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.tb-left, .tb-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.week-info { margin-left: 4px; }
.week-range { font-size: 15px; font-weight: 700; color: var(--color-text-primary); }
.week-id { font-size: 12px; }

.stats { padding: 16px 18px; display: flex; align-items: center; gap: 28px; }
.stat { text-align: center; }
.stat-num { font-size: 26px; font-weight: 800; color: var(--color-text-primary); line-height: 1; }
.stat-num.ok { color: var(--color-success); }
.stat-num.primary { color: var(--color-primary); }
.stat-label { font-size: 12px; margin-top: 6px; }
.stat-days { flex: 1; display: flex; align-items: flex-end; justify-content: space-around; gap: 6px; height: 62px; }
.stat-day { display: flex; flex-direction: column; align-items: center; gap: 5px; flex: 1; height: 100%; }
.sd-bar { flex: 1; width: 100%; max-width: 26px; display: flex; align-items: flex-end; background: var(--color-bg-tertiary); border-radius: 4px; overflow: hidden; }
.sd-fill { width: 100%; background: linear-gradient(180deg, var(--color-primary-light), var(--color-primary)); border-radius: 4px 4px 0 0; transition: height .4s ease; }
.sd-label { font-size: 11px; }

.body { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 290px; gap: 14px; }
.editor-wrap { padding: 12px 14px 14px; display: flex; flex-direction: column; min-height: 420px; overflow: hidden; }
.history { padding: 12px; min-height: 0; overflow-y: auto; }
.panel-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.panel-title { font-size: 14px; font-weight: 600; color: var(--color-text-primary); }
.gen-hint { font-size: 12px; display: flex; align-items: center; gap: 5px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.hist-list { display: flex; flex-direction: column; gap: 8px; }
.hist-item { padding: 10px 12px; border-radius: var(--radius-sm); border: 1px solid var(--color-border); cursor: pointer; transition: all var(--transition-fast); }
.hist-item:hover { border-color: var(--color-border-hover); }
.hist-item.active { border-color: var(--color-primary); background: rgba(245,158,11,.08); }
.hist-week { font-size: 13px; font-weight: 700; color: var(--color-text-primary); }
.hist-meta { font-size: 11px; margin-top: 3px; }

@media (max-width: 1100px) {
  .body { grid-template-columns: 1fr; }
  .history { max-height: 240px; }
}
</style>
