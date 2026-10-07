<template>
  <div class="month-cal">
    <div class="week-head">
      <div v-for="(w, i) in WEEK_CN" :key="w" class="week-head-cell" :class="{ weekend: i >= 5 }">
        {{ w }}
      </div>
    </div>
    <div class="grid">
      <div
        v-for="(week, wi) in weeks"
        :key="wi"
        class="week-row"
      >
        <div
          v-for="cell in week"
          :key="cell.date"
          class="cell"
          :class="{
            'out-month': !cell.inMonth,
            today: cell.isToday,
            selected: cell.date === selected,
            weekend: cell.weekIndex >= 5
          }"
          @click="emit('select', cell.date)"
        >
          <div class="cell-top">
            <span class="day-num">{{ cell.day }}</span>
            <span class="dots">
              <span v-if="hasTasks(cell.date)" class="dot" />
              <span v-if="hasDiary(cell.date)" class="dot dot-diary" />
            </span>
          </div>
          <div class="lunar" :class="lunarClass(cell.date)">{{ lunarCellText(cell.date) }}</div>
          <div v-if="hasTasks(cell.date)" class="bar">
            <div class="bar-fill" :style="{ width: pct(cell.date) + '%' }" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { monthMatrix, lunarCellText, lunarInfo, WEEK_CN } from '@/utils/date'

const props = defineProps<{
  year: number
  month: number
  selected: string
  stats: Record<string, { total: number; done: number }>
  // 有日记的日期 -> 条数（稀疏）
  diary: Record<string, number>
}>()
const emit = defineEmits<{ (e: 'select', date: string): void }>()

const weeks = computed(() => monthMatrix(props.year, props.month))

function statsOf(date: string) {
  return props.stats[date] || { total: 0, done: 0 }
}
function hasTasks(date: string) {
  return statsOf(date).total > 0
}
function hasDiary(date: string) {
  return (props.diary[date] || 0) > 0
}
function pct(date: string) {
  const s = statsOf(date)
  return s.total ? Math.round((s.done / s.total) * 100) : 0
}
function lunarClass(date: string) {
  const info = lunarInfo(date)
  if (info.festivals.length) return 'lunar-festival'
  if (info.solarTerm) return 'lunar-term'
  return ''
}
</script>

<style scoped>
/* 固定格尺寸：每个月大小一致，不随窗口拉伸 */
.month-cal {
  --cw: 92px;   /* 格宽 */
  --ch: 84px;   /* 格高 */
  --gap: 8px;
  display: flex; flex-direction: column; gap: 6px;
  width: fit-content; margin: 0 auto;
}
.week-head { display: grid; grid-template-columns: repeat(7, var(--cw)); gap: var(--gap); }
.week-head-cell {
  text-align: center; font-size: 12px; font-weight: 600;
  color: var(--color-text-muted); padding: 6px 0;
}
.week-head-cell.weekend { color: var(--color-primary); }

.grid { display: flex; flex-direction: column; gap: var(--gap); }
.week-row { display: grid; grid-template-columns: repeat(7, var(--cw)); gap: var(--gap); }

.cell {
  position: relative;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  padding: 7px 8px;
  cursor: pointer;
  transition: all var(--transition-fast);
  overflow: hidden;
  display: flex; flex-direction: column;
  height: var(--ch);
}
.cell:hover { border-color: var(--color-border-hover); transform: translateY(-1px); }
.cell.out-month { opacity: .38; }
.cell.weekend { background: color-mix(in srgb, var(--color-bg-secondary) 92%, var(--color-primary)); }
.cell.today { border-color: var(--color-info); }
.cell.today .day-num { color: var(--color-info); }
.cell.selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(245, 158, 11, .25);
  background: var(--color-surface-hover);
}

.cell-top { display: flex; align-items: center; justify-content: space-between; }
.day-num { font-size: 16px; font-weight: 700; color: var(--color-text-primary); }
/* 右上角圆点纵向容器：绿点(任务)在上，橙点(日记)在下 */
.dots { display: flex; flex-direction: column; align-items: center; gap: 3px; flex-shrink: 0; }
/* 当天有任务即在右上角显示绿色小圆点 */
.dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--color-success);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-success) 22%, transparent);
  flex-shrink: 0;
}
/* 当天有日记则在绿点下方显示橙色小圆点 */
.dot-diary {
  background: #f97316;
  box-shadow: 0 0 0 2px color-mix(in srgb, #f97316 22%, transparent);
}

.lunar { font-size: 11px; color: var(--color-text-muted); margin-top: 2px; }
.lunar-festival { color: var(--color-danger); font-weight: 600; }
.lunar-term { color: var(--color-success); font-weight: 600; }

.bar { position: absolute; left: 0; bottom: 0; width: 100%; height: 3px; background: var(--color-bg-tertiary); }
.bar-fill { height: 100%; background: var(--color-primary); transition: width .3s ease; }

/* 窄屏：改为自适应列宽，避免固定尺寸溢出 */
@media (max-width: 1100px) {
  .month-cal { --cw: minmax(0, 1fr); width: 100%; }
  .cell { height: auto; min-height: 64px; }
}
</style>
