import { defineStore } from 'pinia'
import { api } from '@/api'
import type { WeatherData, CityItem } from '@/types'

interface State {
  activeCity: string | null
  // 城市名 -> 天气数据缓存
  dataMap: Record<string, WeatherData>
  loadingCity: string | null
  searchResults: CityItem[]
  searching: boolean
}

export const useWeatherStore = defineStore('weather', {
  state: (): State => ({
    activeCity: null,
    dataMap: {},
    loadingCity: null,
    searchResults: [],
    searching: false
  }),
  actions: {
    /** 加载某城市天气（默认取缓存，force 强制刷新） */
    async load(city: string, days = 7, force = false) {
      if (!force && this.dataMap[city]) {
        this.activeCity = city
        return this.dataMap[city]
      }
      this.loadingCity = city
      this.activeCity = city
      try {
        // 后端有 30min 缓存；前端 force 时加时间戳绕过浏览器缓存即可
        const data = await api.getWeather(city, days)
        this.dataMap[city] = data
        return data
      } finally {
        this.loadingCity = null
      }
    },
    /** 批量加载多个城市（用于多城市并排查看） */
    async loadMany(cities: CityItem[], days = 7) {
      for (const c of cities) {
        // 逐个加载，避免瞬时并发过多；失败不阻断其余
        try { await this.load(c.name, days) } catch { /* skip */ }
      }
    },
    async search(keyword: string) {
      if (!keyword.trim()) { this.searchResults = []; return [] }
      this.searching = true
      try {
        const res = await api.searchCities(keyword.trim())
        this.searchResults = res || []
        return this.searchResults
      } finally {
        this.searching = false
      }
    },
    clearCache(city?: string) {
      if (city) delete this.dataMap[city]
      else this.dataMap = {}
    }
  }
})
