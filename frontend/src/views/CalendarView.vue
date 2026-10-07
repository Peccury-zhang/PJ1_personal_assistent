<template>
  <div class="calendar-view">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="tb-left">
        <el-radio-group v-model="mode" size="default">
          <el-radio-button value="month">
            <el-icon><Calendar /></el-icon>&nbsp;月视图
          </el-radio-button>
          <el-radio-button value="week">
            <el-icon><Grid /></el-icon>&nbsp;周视图
          </el-radio-button>
        </el-radio-group>
      </div>

      <div class="tb-center">
        <el-button-group>
          <el-button @click="nav(-1)"><el-icon><ArrowLeft /></el-icon></el-button>
          <el-button
            class="tb-mid-btn"
            :title="mode === 'month' ? '点击选择年月' : '点击选择年份与周'"
            @click="openPicker"
          >
            {{ mode === 'month' ? `${year} 年 ${month} 月` : `第 ${weekNum} 周` }}
            <el-icon class="tb-mid-caret"><ArrowDown /></el-icon>
          </el-button>
          <el-button @click="nav(1)"><el-icon><ArrowRight /></el-icon></el-button>
        </el-button-group>
      </div>
    </div>

    <!-- 月视图：月历 + 当日详情 -->
    <div v-if="mode === 'month'" class="month-layout">
      <section class="cal-panel pa-card">
        <MonthCalendar
          :year="year"
          :month="month"
          :selected="selectedDate"
          :stats="stats"
          :diary="diaryStore.rangeMap"
          @select="onSelect"
        />
      </section>
      <aside class="detail-panel pa-scroll">
        <DayDetail :date="selectedDate" @open-settings="emit('open-settings')" />
      </aside>
    </div>

    <!-- 周视图：整周看板 -->
    <div v-else class="week-layout pa-card">
      <WeekBoard :week-start="weekStart" />
    </div>

    <!-- 年月 / 年周 快速跳转（滚轮式） -->
    <el-dialog
      v-model="pickerVisible"
      :title="mode === 'month' ? '选择年月' : '选择年份与周'"
      width="380px"
    >
      <div class="tumbler">
        <div class="t-wrap">
          <div class="t-head">年</div>
          <TumblerColumn v-model="pickYear" :options="yearTumbler" />
        </div>
        <div class="t-wrap">
          <div class="t-head">{{ mode === 'month' ? '月' : '周' }}</div>
          <TumblerColumn v-if="mode === 'month'" v-model="pickMonth" :options="monthTumbler" />
          <TumblerColumn v-else v-model="pickWeek" :options="weekTumbler" />
        </div>
      </div>
      <template #footer>
        <el-button @click="pickToday">回到{{ mode === 'month' ? '今天' : '本周' }}</el-button>
        <el-button type="primary" @click="applyPick">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import dayjs from 'dayjs'
import MonthCalendar from '@/components/calendar/MonthCalendar.vue'
import DayDetail from '@/components/calendar/DayDetail.vue'
import WeekBoard from '@/components/calendar/WeekBoard.vue'
import TumblerColumn from '@/components/calendar/TumblerColumn.vue'
import { useTasksStore } from '@/stores/tasks'
import { useDiaryStore } from '@/stores/diary'
import { mondayOfWeek, today } from '@/utils/date'

const emit = defineEmits<{ (e: 'open-settings'): void }>()
const tasksStore = useTasksStore()
const diaryStore = useDiaryStore()

const mode = ref<'month' | 'week'>('month')
const selectedDate = ref(today())

const year = computed(() => dayjs(selectedDate.value).year())
const month = computed(() => dayjs(selectedDate.value).month() + 1)
const weekStart = computed(() => mondayOfWeek(selectedDate.value).format('YYYY-MM-DD'))

// 月视图矩阵覆盖的区间（6 周 × 7 天，周一起始）
const matrixStart = computed(() => mondayOfWeek(dayjs(`${year.value}-${String(month.value).padStart(2, '0')}-01`)).format('YYYY-MM-DD'))
const matrixEnd = computed(() => dayjs(matrixStart.value).add(41, 'day').format('YYYY-MM-DD'))

const stats = computed(() => tasksStore.rangeMap)

// 周视图中央标签：本年第 x 周（ISO 周）
const weekNum = computed(() => dayjs(selectedDate.value).isoWeek())

async function loadMonthRange() {
  // 任务统计与日记打点并行拉取；日记失败不阻塞月历
  await Promise.all([
    tasksStore.loadRange(matrixStart.value, matrixEnd.value),
    diaryStore.loadRange(matrixStart.value, matrixEnd.value).catch(() => {})
  ])
}

watch([year, month], loadMonthRange, { immediate: true })

function onSelect(date: string) {
  selectedDate.value = date
}
function goToday() {
  selectedDate.value = today()
}

// ---------------- 年月 / 年周 快速跳转 ----------------
const pickerVisible = ref(false)
const pickYear = ref(year.value)
const pickMonth = ref(month.value)
const pickWeek = ref(weekNum.value)

const yearOptions = computed(() => {
  const cur = dayjs().year()
  const out: number[] = []
  for (let y = cur - 10; y <= cur + 10; y++) out.push(y)
  return out
})
// 该年 ISO 周总数 = 12-28 所在 ISO 周
const weekOptions = computed(() => {
  const n = dayjs(`${pickYear.value}-12-28`).isoWeek()
  return Array.from({ length: n }, (_, i) => i + 1)
})

// 滚轮列数据源
const yearTumbler = computed(() => yearOptions.value.map((y) => ({ value: y, label: String(y) })))
const monthTumbler = computed(() => Array.from({ length: 12 }, (_, i) => ({ value: i + 1, label: `${i + 1} 月` })))
const weekTumbler = computed(() => weekOptions.value.map((w) => ({ value: w, label: `第 ${w} 周` })))

function openPicker() {
  // 默认进入当年当月（周视图为当年当周）
  const now = dayjs()
  pickYear.value = now.year()
  pickMonth.value = now.month() + 1
  pickWeek.value = now.isoWeek()
  pickerVisible.value = true
}
function applyPick() {
  if (mode.value === 'month') {
    const mm = String(pickMonth.value).padStart(2, '0')
    const dim = dayjs(`${pickYear.value}-${mm}-01`).daysInMonth()
    const d = Math.min(dayjs(selectedDate.value).date(), dim)
    selectedDate.value = `${pickYear.value}-${mm}-${String(d).padStart(2, '0')}`
  } else {
    const base = dayjs(`${pickYear.value}-01-04`).isoWeek(pickWeek.value)
    selectedDate.value = mondayOfWeek(base).format('YYYY-MM-DD')
  }
  pickerVisible.value = false
}
function pickToday() {
  goToday()
  pickerVisible.value = false
}
function nav(delta: number) {
  if (mode.value === 'month') {
    selectedDate.value = dayjs(selectedDate.value).add(delta, 'month').format('YYYY-MM-DD')
  } else {
    selectedDate.value = dayjs(selectedDate.value).add(delta * 7, 'day').format('YYYY-MM-DD')
  }
}
</script>

<style scoped>
.calendar-view { display: flex; flex-direction: column; height: 100%; gap: 14px; }

.toolbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
}
.tb-left { justify-self: start; }
.tb-center { grid-column: 2; justify-self: center; display: flex; align-items: center; gap: 14px; }
/* 导航中间按钮：月视图显示年月、周视图显示第 x 周（点击弹出选择器） */
.tb-mid-btn { min-width: 108px; font-weight: 600; }
.tb-mid-caret { margin-left: 4px; }

/* 滚轮式年月/年周选择器 */
.tumbler { display: flex; gap: 12px; }
.t-wrap { flex: 1; display: flex; flex-direction: column; align-items: center; }
.t-head {
  font-size: 12px; color: var(--color-text-secondary);
  padding-bottom: 4px; margin-bottom: 4px; width: 100%; text-align: center;
  border-bottom: 1px solid var(--color-border);
}

.month-layout {
  flex: 1; min-height: 0;
  display: grid;
  /* 左栏按内容（固定月历）宽度，右栏 480px 容纳子卡片；整体居中消除大片留白 */
  grid-template-columns: auto 480px;
  grid-template-rows: minmax(0, 1fr);
  justify-content: center;
  gap: 16px;
}
.cal-panel {
  padding: 16px; min-height: 0;
  display: flex; overflow: auto;
  align-items: flex-start; justify-content: center;
}
.detail-panel { padding: 0; min-height: 0; overflow-y: auto; background: transparent; border: none; box-shadow: none; }

.week-layout { flex: 1; min-height: 0; padding: 16px; display: flex; }
.week-layout > * { flex: 1; min-height: 0; }

@media (max-width: 760px) {
  /* 窄屏工具栏改为纵向居中堆叠 */
  .toolbar { grid-template-columns: 1fr; justify-items: center; row-gap: 10px; }
  .tb-left, .tb-center { grid-column: 1; justify-self: center; }
}

@media (max-width: 1100px) {
  /* 窄屏改为自然高度纵向堆叠，交由外层 .content 滚动，避免 grid 行拉伸导致重叠 */
  .calendar-view { height: auto; min-height: 100%; }
  .month-layout { grid-template-columns: 1fr; grid-template-rows: auto; justify-content: stretch; }
  .cal-panel { overflow: visible; }
  .detail-panel { overflow: visible; min-height: 0; }
}
</style>
