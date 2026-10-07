import { defineStore } from 'pinia'
import { api } from '@/api'

interface State {
  // 当前月视图区间内有日记的日期 -> 条数（稀疏，无日记的日期不在其中）
  rangeMap: Record<string, number>
}

export const useDiaryStore = defineStore('diary', {
  state: (): State => ({
    rangeMap: {}
  }),
  getters: {
    countOf: (s) => (date: string) => s.rangeMap[date] || 0,
    hasDiary: (s) => (date: string) => (s.rangeMap[date] || 0) > 0
  },
  actions: {
    /** 拉取区间内每天的日记条数，供月历打橙色圆点。失败静默（不阻塞月历）。 */
    async loadRange(start: string, end: string) {
      const res = await api.diaryRange(start, end)
      this.rangeMap = res.diary || {}
      return res
    },
    /** 保存/删除日记后立即更新某天计数，保证月历橙点实时刷新，无需重拉整月。 */
    setCount(date: string, count: number) {
      if (count > 0) this.rangeMap[date] = count
      else delete this.rangeMap[date]
    }
  }
})
