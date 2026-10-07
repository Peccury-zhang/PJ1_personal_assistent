import { defineStore } from 'pinia'
import { api } from '@/api'
import type { Task, DayData, RangeDay } from '@/types'
import { ElMessage } from 'element-plus'

interface State {
  // 当前月视图区间的每日统计（date -> RangeDay）
  rangeMap: Record<string, RangeDay>
  rangeLoaded: { start: string; end: string } | null
  // 当前选中日
  currentDate: string | null
  currentDay: DayData | null
  loading: boolean
  saving: boolean
}

export const useTasksStore = defineStore('tasks', {
  state: (): State => ({
    rangeMap: {},
    rangeLoaded: null,
    currentDate: null,
    currentDay: null,
    loading: false,
    saving: false
  }),
  getters: {
    statsOf: (s) => (date: string) => s.rangeMap[date] || { total: 0, done: 0 }
  },
  actions: {
    async loadRange(start: string, end: string) {
      this.loading = true
      try {
        const res = await api.rangeStats(start, end)
        const map: Record<string, RangeDay> = {}
        for (const d of res.days) map[d.date] = d
        this.rangeMap = map
        this.rangeLoaded = { start, end }
        return res
      } finally {
        this.loading = false
      }
    },
    async loadDay(date: string, force = false) {
      if (!force && this.currentDay && this.currentDate === date) return this.currentDay
      this.currentDate = date
      const day = await api.getDay(date)
      this.currentDay = day
      return day
    },
    /** 保存某天任务；带乐观并发（revision）。冲突时提示并返回 null。 */
    async saveDay(date: string, tasks: Task[], revision?: string | null): Promise<DayData | null> {
      this.saving = true
      try {
        const saved = await api.putDay(date, tasks, revision)
        this.currentDay = saved
        // 同步更新区间统计缓存
        this.rangeMap[date] = {
          date,
          total: saved.tasks.length,
          done: saved.tasks.filter((t) => t.done).length,
          tasks: saved.tasks
        }
        return saved
      } catch (e: any) {
        // 409：并发冲突，提示刷新
        if (String(e?.message || '').includes('其他窗口')) {
          ElMessage.warning('该日任务已在别处更新，已为你刷新最新数据')
          await this.loadDay(date, true)
        }
        return null
      } finally {
        this.saving = false
      }
    }
  }
})
