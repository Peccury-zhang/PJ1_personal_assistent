<template>
  <div class="week-board">
    <div class="wb-head">
      <div class="wb-range">
        <b>{{ rangeText }}</b>
        <span class="pa-muted">（{{ weekId }}）</span>
      </div>
      <div class="wb-stat pa-muted">
        共 {{ total }} 项 · 完成率 {{ rateText }}
      </div>
    </div>

    <div v-loading="loading" class="wb-cols pa-scroll">
      <div v-for="d in days" :key="d.date" class="wb-col" :class="{ weekend: isWeekend(d.date), today: d.date === todayStr }">
        <div class="col-head">
          <div class="col-week">{{ weekdayCn(d.date) }}</div>
          <div class="col-date">{{ shortDate(d.date) }}</div>
          <div class="col-lunar pa-muted">{{ lunarDay(d.date) }}</div>
        </div>

        <div class="col-body pa-scroll">
          <TaskItem
            v-for="t in d.tasks"
            :key="t.id"
            :task="t"
            compact
            @toggle="(v) => onToggle(d, t, v)"
            @edit="openEdit(d, t)"
            @remove="onRemove(d, t)"
          />
          <el-button class="col-add-btn" size="small" @click="openAdd(d)">
            <el-icon><Plus /></el-icon>&nbsp;添加
          </el-button>
        </div>
      </div>
    </div>

    <TaskEditDialog
      v-model="dialogVisible"
      :task="editing.task"
      :date-label="editing.dateLabel"
      @save="onSave"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import TaskItem from './TaskItem.vue'
import TaskEditDialog from './TaskEditDialog.vue'
import { useTasksStore } from '@/stores/tasks'
import { weekdayCn, lunarInfo, today } from '@/utils/date'
import type { Task } from '@/types'

const props = defineProps<{ weekStart: string }>()
const tasksStore = useTasksStore()

interface ColDay { date: string; tasks: Task[] }
const days = ref<ColDay[]>([])
const loading = ref(false)
const todayStr = today()

const dialogVisible = ref(false)
const editing = ref<{ date: string; task: Task | null; dateLabel: string }>({ date: '', task: null, dateLabel: '' })

const sunday = computed(() => dayjs(props.weekStart).add(6, 'day').format('YYYY-MM-DD'))
const rangeText = computed(() => `${dayjs(props.weekStart).format('YYYY年M月D日')} ~ ${dayjs(sunday.value).format('M月D日')}`)
const weekId = computed(() => {
  const iso = dayjs(props.weekStart).isoWeek?.() ?? ''
  return `${dayjs(props.weekStart).year()} 第${iso}周`
})
const total = computed(() => days.value.reduce((s, d) => s + d.tasks.length, 0))
const done = computed(() => days.value.reduce((s, d) => s + d.tasks.filter((t) => t.done).length, 0))
const rateText = computed(() => (total.value ? `${Math.round((done.value / total.value) * 100)}%` : '—'))

function isWeekend(date: string) {
  const w = dayjs(date).day()
  return w === 0 || w === 6
}
function shortDate(date: string) {
  return dayjs(date).format('M/D')
}
function lunarDay(date: string) {
  const info = lunarInfo(date)
  return info.festivals[0] || info.solarTerm || info.dayText
}

async function load() {
  loading.value = true
  try {
    const res = await tasksStore.loadRange(props.weekStart, sunday.value)
    days.value = res.days.map((d) => ({
      date: d.date,
      tasks: JSON.parse(JSON.stringify(d.tasks || []))
    }))
  } finally {
    loading.value = false
  }
}

watch(() => props.weekStart, load, { immediate: true })

async function saveCol(d: ColDay) {
  // 周看板批量编辑，传 null 跳过乐观并发检查
  await tasksStore.saveDay(d.date, d.tasks, null)
}

function openAdd(d: ColDay) {
  editing.value = {
    date: d.date,
    task: null,
    dateLabel: `${d.date} ${weekdayCn(d.date)} · ${lunarInfo(d.date).lunarText}`
  }
  dialogVisible.value = true
}

async function onToggle(d: ColDay, t: Task, v: boolean) {
  t.done = v
  await saveCol(d)
}

function openEdit(d: ColDay, t: Task) {
  editing.value = {
    date: d.date,
    task: { ...t },
    dateLabel: `${d.date} ${weekdayCn(d.date)} · ${lunarInfo(d.date).lunarText}`
  }
  dialogVisible.value = true
}

function onSave(payload: Partial<Task>) {
  const d = days.value.find((x) => x.date === editing.value.date)
  if (!d) return
  if (editing.value.task?.id) {
    const i = d.tasks.findIndex((t) => t.id === editing.value.task!.id)
    if (i >= 0) d.tasks[i] = { ...d.tasks[i], ...payload } as Task
  } else {
    d.tasks.push({ id: `tmp_${Date.now()}`, title: payload.title || '', note: payload.note || '', priority: payload.priority || 'normal', done: payload.done || false })
  }
  saveCol(d)
}

async function onRemove(d: ColDay, t: Task) {
  try {
    await ElMessageBox.confirm(`删除任务「${t.title}」？`, '确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch { return }
  d.tasks = d.tasks.filter((x) => x.id !== t.id)
  await saveCol(d)
  ElMessage.success('已删除')
}
</script>

<style scoped>
.week-board { display: flex; flex-direction: column; height: 100%; gap: 14px; }
.wb-head { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.wb-range { font-size: 16px; color: var(--color-text-primary); }
.wb-range b { font-weight: 700; }
.wb-stat { font-size: 13px; }
.wb-stat .ok { color: var(--color-success); font-weight: 600; }

.wb-cols {
  flex: 1; display: grid; grid-template-columns: repeat(7, minmax(150px, 1fr));
  gap: 10px; overflow-x: auto; min-height: 0;
}
.wb-col {
  display: flex; flex-direction: column;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden; min-height: 300px;
}
.wb-col.today { border-color: var(--color-primary); box-shadow: 0 0 0 1px rgba(245,158,11,.3); }
.wb-col.weekend .col-head { background: color-mix(in srgb, var(--color-bg-tertiary) 60%, transparent); }

.col-head { padding: 10px; text-align: center; border-bottom: 1px solid var(--color-border); }
.col-week { font-size: 13px; font-weight: 700; color: var(--color-text-primary); }
.col-date { font-size: 12px; color: var(--color-primary); margin-top: 2px; }
.col-lunar { font-size: 11px; margin-top: 2px; }

.col-body { flex: 1; padding: 8px; display: flex; flex-direction: column; gap: 6px; overflow-y: auto; min-height: 60px; }
/* 列内添加按钮：跟随任务流式排布，始终位于最下方任务之下 */
.col-add-btn {
  width: 100%;
  border-style: dashed;
  color: var(--color-text-muted);
  background: transparent;
}
.col-add-btn:hover { color: var(--color-primary); border-color: var(--color-primary); }
</style>
