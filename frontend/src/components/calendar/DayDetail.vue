<template>
  <div class="day-detail">
    <!-- ① 日期卡片 -->
    <section class="sub-card sc-date">
      <div class="sc-title-row">
        <span class="sc-title">日期</span>
        <span v-if="relativeDayLabel" class="d-rel">{{ relativeDayLabel }}</span>
      </div>
      <div class="date-body">
        <div class="date-line">
          <span class="d-md">{{ mdText }}</span>
          <span class="d-week">{{ weekdayCn(date) }}</span>
        </div>
        <div class="d-lunar pa-secondary">{{ lunar.lunarText }}</div>
        <div v-if="lunar.festivals.length || lunar.solarTerm || lunar.ganZhi" class="d-tags">
          <el-tag v-for="f in lunar.festivals" :key="f" type="danger" effect="light" size="small">{{ f }}</el-tag>
          <el-tag v-if="lunar.solarTerm" type="success" effect="light" size="small">{{ lunar.solarTerm }}</el-tag>
          <span v-if="lunar.ganZhi" class="d-ganzhi pa-muted">{{ lunar.ganZhi }}</span>
        </div>
      </div>
    </section>

    <!-- ② 天气卡片 -->
    <section class="sub-card sc-weather">
      <div class="sc-title-row">
        <span class="sc-title">天气</span>
        <span v-if="wx" class="sc-hint pa-muted">{{ wx.city }}</span>
      </div>
      <template v-if="wx">
        <div class="wx-main">
          <span class="wx-emoji">{{ wx.emoji }}</span>
          <div>
            <div class="wx-temp">{{ wx.tempText }} <span class="wx-text">{{ wx.text }}</span></div>
            <div class="wx-sub pa-muted">{{ wx.subText }}</div>
          </div>
        </div>
        <div class="wx-metrics">
          <div v-for="m in wx.metrics" :key="m.label" class="wx-metric">
            <span class="pa-muted">{{ m.label }}</span>
            <span :style="m.color ? { color: m.color } : undefined">{{ m.value }}</span>
          </div>
        </div>
      </template>
      <div v-else class="wx-empty pa-muted">
        <span v-if="!defaultCity">
          未配置城市，<el-link type="primary" @click="emit('open-settings')">去设置</el-link>
        </span>
        <span v-else>该日期暂无天气数据（仅支持今天起未来 7 天）</span>
      </div>
    </section>

    <!-- ③ 当日任务卡片 -->
    <section class="sub-card sc-todo">
      <div class="sc-title-row">
        <span class="sc-title">当日任务</span>
        <el-button type="primary" size="small" @click="openAdd(false)">
          <el-icon><Plus /></el-icon>&nbsp;新增
        </el-button>
      </div>
      <div class="sc-progress">
        <div class="dp-text">
          <span>已完成 <b>{{ rateNum }}</b>%</span>
        </div>
        <el-progress
          :percentage="rateNum"
          :stroke-width="6"
          :show-text="false"
          :color="rateNum === 100 ? '#10b981' : '#f59e0b'"
        />
      </div>
      <div v-if="pendingTasks.length" class="task-list pa-scroll">
        <TaskItem
          v-for="t in pendingTasks"
          :key="t.id"
          :task="t"
          @toggle="(v) => onToggle(t, v)"
          @edit="openEdit(t)"
          @remove="onRemove(t)"
        />
      </div>
      <div v-else class="sc-empty pa-muted">暂无待办任务</div>
    </section>

    <!-- ④ 已完成任务卡片 -->
    <section class="sub-card sc-done">
      <div class="sc-title-row">
        <span class="sc-left">
          <span class="sc-title">已完成任务</span>
          <span class="sc-count pa-muted">{{ doneTasks.length }}</span>
        </span>
        <el-button type="primary" size="small" @click="openAdd(true)">
          <el-icon><Plus /></el-icon>&nbsp;新增
        </el-button>
      </div>
      <div v-if="doneTasks.length" class="task-list pa-scroll">
        <TaskItem
          v-for="t in doneTasks"
          :key="t.id"
          :task="t"
          @toggle="(v) => onToggle(t, v)"
          @edit="openEdit(t)"
          @remove="onRemove(t)"
        />
      </div>
      <div v-else class="sc-empty pa-muted">还没有已完成的任务</div>
    </section>

    <!-- ⑤ 日记卡片 -->
    <section class="sub-card sc-diary">
      <div class="sc-title-row">
        <span class="sc-left">
          <span class="sc-title">日记</span>
          <span class="sc-count sc-count-diary pa-muted">{{ diaryEntries.length }}</span>
        </span>
        <el-button type="primary" size="small" @click="openDiaryAdd">
          <el-icon><Plus /></el-icon>&nbsp;新增
        </el-button>
      </div>
      <div v-if="diaryEntries.length" class="diary-list pa-scroll">
        <div v-for="e in diaryEntries" :key="e.id" class="diary-item">
          <div class="diary-content">{{ e.content }}</div>
          <div class="diary-foot">
            <span class="pa-muted">{{ e.updated_at }}</span>
            <span class="row-actions">
              <el-button size="small" type="warning" circle title="编辑" @click="openDiaryEdit(e)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button size="small" type="danger" circle title="删除" @click="onDiaryRemove(e)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </span>
          </div>
        </div>
      </div>
      <div v-else class="sc-empty pa-muted">今天还没有日记</div>
    </section>

    <TaskEditDialog
      v-model="dialogVisible"
      :task="editing"
      :date-label="dialogDateLabel"
      :initial-done="addDoneFlag"
      @save="onSave"
    />
    <DiaryEditDialog
      v-model="diaryDialogVisible"
      :entry="diaryEditing"
      @save="onDiarySave"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import TaskItem from './TaskItem.vue'
import TaskEditDialog from './TaskEditDialog.vue'
import DiaryEditDialog from './DiaryEditDialog.vue'
import { useTasksStore } from '@/stores/tasks'
import { useDiaryStore } from '@/stores/diary'
import { useWeatherStore } from '@/stores/weather'
import { useSettingsStore } from '@/stores/settings'
import { api } from '@/api'
import { lunarInfo, weekdayCn, today } from '@/utils/date'
import { weatherEmoji, uvLabel, uvColor, aqiColor, tempText } from '@/utils/weather'
import type { Task, DiaryEntry } from '@/types'

const props = defineProps<{ date: string }>()
const emit = defineEmits<{ (e: 'open-settings'): void }>()

const tasksStore = useTasksStore()
const diaryStore = useDiaryStore()
const weatherStore = useWeatherStore()
const settings = useSettingsStore()

const tasks = ref<Task[]>([])
const revision = ref<string | null>(null)
const dialogVisible = ref(false)
const editing = ref<Task | null>(null)
const addDoneFlag = ref(false)

// 日记
const diaryEntries = ref<DiaryEntry[]>([])
const diaryDialogVisible = ref(false)
const diaryEditing = ref<DiaryEntry | null>(null)

const lunar = computed(() => lunarInfo(props.date))
const mdText = computed(() => dayjs(props.date).format('M月D日'))
// 仅当所选日期为今天/昨天/明天时显示相对标签
const relativeDayLabel = computed(() => {
  const diff = dayjs(props.date).startOf('day').diff(dayjs().startOf('day'), 'day')
  if (diff === 0) return '今天'
  if (diff === -1) return '昨天'
  if (diff === 1) return '明天'
  return ''
})
const pendingTasks = computed(() => tasks.value.filter((t) => !t.done))
const doneTasks = computed(() => tasks.value.filter((t) => t.done))
const doneCount = computed(() => doneTasks.value.length)
const rateNum = computed(() => (tasks.value.length ? Math.round((doneCount.value / tasks.value.length) * 100) : 0))
const dialogDateLabel = computed(() => `${props.date} ${weekdayCn(props.date)} · ${lunar.value.lunarText}`)

// ---------------- 天气 ----------------
interface WxMetric { label: string; value: string; color?: string }
const defaultCity = computed(() => settings.weather.cities?.[0]?.name || '')
const wx = computed(() => {
  if (!defaultCity.value) return null
  const data = weatherStore.dataMap[defaultCity.value]
  if (!data) return null
  const city = data.city
  const isToday = props.date === today()
  if (isToday && data.current) {
    const c = data.current
    const metrics: WxMetric[] = [
      { label: '湿度', value: c.humidity != null ? `${c.humidity}%` : '—' },
      { label: '气压', value: c.pressure != null ? `${c.pressure} hPa` : '—' },
      { label: '风', value: `${c.wind_dir || ''} ${c.wind_scale || ''}`.trim() || '—' },
      { label: '风速', value: c.wind_speed != null ? `${c.wind_speed} km/h` : '—' },
      { label: '紫外线', value: uvLabel(c.uv_index), color: uvColor(c.uv_index) },
      { label: '空气', value: c.aqi_category || (c.aqi != null ? String(c.aqi) : '—'), color: aqiColor(c.aqi_category) },
      { label: 'PM2.5', value: c.pm25 != null ? String(c.pm25) : '—' },
      { label: 'PM10', value: c.pm10 != null ? String(c.pm10) : '—' },
      { label: 'O₃', value: c.o3 != null ? String(c.o3) : '—' },
      { label: '能见度', value: c.vis != null ? `${c.vis} km` : '—' }
    ]
    return {
      city,
      emoji: weatherEmoji(c.text, c.icon),
      tempText: `${tempText(c.temp)}C`,
      text: c.text,
      subText: `体感 ${tempText(c.feels_like)}C`,
      metrics
    }
  }
  const d = data.daily?.find((x) => x.date === props.date)
  if (!d) return null
  const metrics: WxMetric[] = [
    { label: '高温', value: tempText(d.temp_max) },
    { label: '低温', value: tempText(d.temp_min) },
    { label: '风', value: `${d.wind_dir_day || ''} ${d.wind_scale_day || ''}`.trim() || '—' },
    { label: '紫外线', value: uvLabel(d.uv_index), color: uvColor(d.uv_index) },
    { label: '湿度', value: d.humidity != null ? `${d.humidity}%` : '—' },
    { label: '气压', value: d.pressure != null ? `${d.pressure} hPa` : '—' },
    { label: '日出', value: d.sunrise || '—' },
    { label: '日落', value: d.sunset || '—' }
  ]
  return {
    city,
    emoji: weatherEmoji(d.text_day, d.icon_day),
    tempText: `${tempText(d.temp_min)}~${tempText(d.temp_max)}`,
    text: d.text_day,
    subText: `${d.week}`,
    metrics
  }
})

// ---------------- 载入 ----------------
async function loadDate(date: string) {
  const day = await tasksStore.loadDay(date, true)
  tasks.value = JSON.parse(JSON.stringify(day.tasks || []))
  revision.value = day.revision
  // 加载当日日记（静默失败）
  try {
    const d = await api.getDiary(date)
    diaryEntries.value = d.entries || []
  } catch {
    diaryEntries.value = []
  }
  // 尝试加载默认城市天气（静默）
  if (defaultCity.value && !weatherStore.dataMap[defaultCity.value]) {
    weatherStore.load(defaultCity.value, 7).catch(() => {})
  }
}

watch(() => props.date, (d) => { if (d) loadDate(d) }, { immediate: true })
watch(defaultCity, (c) => { if (c) weatherStore.load(c, 7).catch(() => {}) })

// ---------------- 保存 ----------------
async function persist() {
  const saved = await tasksStore.saveDay(props.date, tasks.value, revision.value)
  if (saved) {
    revision.value = saved.revision
    tasks.value = JSON.parse(JSON.stringify(saved.tasks))
  }
}

function openAdd(asDone = false) {
  addDoneFlag.value = asDone
  editing.value = null
  dialogVisible.value = true
}
function openEdit(t: Task) {
  editing.value = { ...t }
  dialogVisible.value = true
}
function onSave(payload: Partial<Task>) {
  if (editing.value?.id) {
    const i = tasks.value.findIndex((t) => t.id === editing.value!.id)
    if (i >= 0) tasks.value[i] = { ...tasks.value[i], ...payload } as Task
  } else {
    tasks.value.push({
      id: `tmp_${Date.now()}`,
      title: payload.title || '',
      note: payload.note || '',
      priority: payload.priority || 'normal',
      done: payload.done || false
    })
  }
  persist()
}
async function onToggle(t: Task, v: boolean) {
  t.done = v
  await persist()
}
async function onRemove(t: Task) {
  try {
    await ElMessageBox.confirm(`删除任务「${t.title}」？`, '确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch { return }
  tasks.value = tasks.value.filter((x) => x.id !== t.id)
  await persist()
  ElMessage.success('已删除')
}

// ---------------- 日记 ----------------
async function persistDiary(entries: DiaryEntry[]) {
  const saved = await api.saveDiary(props.date, entries)
  diaryEntries.value = saved.entries || []
  // 同步月历橙色日记圆点（新增/删除后即时生效）
  diaryStore.setCount(props.date, diaryEntries.value.length)
}
function openDiaryAdd() {
  diaryEditing.value = null
  diaryDialogVisible.value = true
}
function openDiaryEdit(e: DiaryEntry) {
  diaryEditing.value = { ...e }
  diaryDialogVisible.value = true
}
async function onDiarySave(content: string) {
  const list = diaryEntries.value.slice()
  if (diaryEditing.value?.id) {
    const i = list.findIndex((x) => x.id === diaryEditing.value!.id)
    if (i >= 0) list[i] = { ...list[i], content }
  } else {
    list.push({ id: `tmp_${Date.now()}`, content })
  }
  await persistDiary(list)
  ElMessage.success('已保存')
}
async function onDiaryRemove(e: DiaryEntry) {
  try {
    await ElMessageBox.confirm('删除这条日记？', '确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch { return }
  await persistDiary(diaryEntries.value.filter((x) => x.id !== e.id))
  ElMessage.success('已删除')
}
</script>

<style scoped>
.day-detail { display: flex; flex-direction: column; gap: 14px; }

/* 通用子卡片：各自不同底色 */
.sub-card {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  padding: 14px 16px;
  display: flex; flex-direction: column; gap: 12px;
}
.sc-date    { background: linear-gradient(135deg, rgba(245,158,11,.10), rgba(245,158,11,.03)); border-color: rgba(245,158,11,.28); }
.sc-weather { background: linear-gradient(135deg, rgba(59,130,246,.12), rgba(59,130,246,.03)); border-color: rgba(59,130,246,.28); }
.sc-todo    { background: linear-gradient(135deg, rgba(16,185,129,.10), rgba(16,185,129,.02)); border-color: rgba(16,185,129,.26); }
.sc-done    { background: linear-gradient(135deg, rgba(139,92,246,.12), rgba(139,92,246,.03)); border-color: rgba(139,92,246,.28); }
.sc-diary   { background: linear-gradient(135deg, rgba(236,72,153,.10), rgba(236,72,153,.02)); border-color: rgba(236,72,153,.26); }

.sc-title-row { display: flex; align-items: center; justify-content: space-between; }
.sc-left { display: flex; align-items: center; gap: 8px; }
.sc-title { font-size: 14px; font-weight: 700; color: var(--color-text-primary); letter-spacing: .5px; }
.sc-hint { font-size: 12px; }
.sc-count {
  font-size: 12px; min-width: 22px; text-align: center;
  padding: 1px 8px; border-radius: 10px;
  background: rgba(139,92,246,.18); color: var(--color-text-secondary);
}
.sc-count-diary { background: rgba(236,72,153,.18); }

/* 空态：紧凑一行，避免无任务时卡片过高 */
.sc-empty { font-size: 12.5px; text-align: center; padding: 8px 0; }

/* 日期卡 */
.date-body { display: flex; flex-direction: column; gap: 5px; }
.date-line { display: flex; align-items: baseline; gap: 10px; }
.d-md { font-size: 26px; font-weight: 800; color: var(--color-text-primary); }
.d-week { font-size: 15px; color: var(--color-primary); font-weight: 600; }
.d-lunar { font-size: 13px; }
.d-tags { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.d-ganzhi { font-size: 11px; }
.d-rel {
  font-size: 12px; font-weight: 700; color: var(--color-primary);
  background: rgba(245,158,11,.15); border: 1px solid rgba(245,158,11,.35);
  padding: 2px 12px; border-radius: 999px;
}

/* 天气卡 */
.wx-main { display: flex; align-items: center; gap: 12px; }
.wx-emoji { font-size: 36px; line-height: 1; }
.wx-temp { font-size: 19px; font-weight: 700; color: var(--color-text-primary); }
.wx-text { font-size: 13px; font-weight: 500; color: var(--color-text-secondary); }
.wx-sub { font-size: 12px; margin-top: 2px; }
.wx-metrics {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px 8px;
  padding-top: 12px; border-top: 1px solid var(--color-border);
}
.wx-metric { font-size: 12.5px; color: var(--color-text-primary); display: flex; flex-direction: column; gap: 2px; }
.wx-metric .pa-muted { font-size: 10.5px; }
.wx-empty { font-size: 12.5px; text-align: center; padding: 6px 0; }

/* 进度 */
.sc-progress { display: flex; flex-direction: column; gap: 7px; }
.dp-text { font-size: 13px; color: var(--color-text-secondary); display: flex; gap: 4px; }
.dp-text b { color: var(--color-primary); }

/* 任务列表 */
.task-list { display: flex; flex-direction: column; gap: 8px; max-height: 260px; overflow-y: auto; }

/* 日记列表 */
.diary-list { display: flex; flex-direction: column; gap: 8px; max-height: 240px; overflow-y: auto; }
.diary-item {
  background: rgba(255,255,255,.04); border: 1px solid var(--color-border);
  border-radius: var(--radius-sm); padding: 8px 10px;
  display: flex; flex-direction: column; gap: 6px;
}
.diary-content { font-size: 13px; color: var(--color-text-primary); white-space: pre-wrap; word-break: break-word; }
.diary-foot { display: flex; align-items: center; justify-content: space-between; }
.diary-foot .pa-muted { font-size: 11px; }
</style>
