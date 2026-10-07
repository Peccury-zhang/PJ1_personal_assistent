import { defineStore } from 'pinia'
import { api } from '@/api'
import type { AiConfig, WeatherConfig, SettingsPatch } from '@/types'

const LS_THEME = 'pa.theme'
const LS_WEEK_START = 'pa.week_start'

interface State {
  theme: 'dark' | 'light'
  weekStart: 1
  ai: AiConfig
  weather: WeatherConfig
  loaded: boolean
  loading: boolean
}

const DEFAULT_AI: AiConfig = {
  provider: 'dashscope',
  base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  model: 'qwen3.8-flash',
  temperature: 0.7,
  max_tokens: 4096,
  report_style: '简洁要点式'
}

const DEFAULT_WEATHER: WeatherConfig = {
  provider: 'open_meteo',
  api_host: 'k838m3jq58.re.qweatherapi.com',
  cities: [],
  cache_minutes: 30
}

export const useSettingsStore = defineStore('settings', {
  state: (): State => ({
    theme: (localStorage.getItem(LS_THEME) as 'dark' | 'light') || 'dark',
    weekStart: 1,
    ai: { ...DEFAULT_AI },
    weather: { ...DEFAULT_WEATHER },
    loaded: false,
    loading: false
  }),
  getters: {
    aiReady: (s) => !!s.ai.has_api_key || s.ai.provider === 'ollama',
    weatherProviderLabel: (s) => (s.weather.provider === 'qweather' ? '和风天气' : 'Open-Meteo')
  },
  actions: {
    async load(force = false) {
      if (this.loaded && !force) return
      this.loading = true
      try {
        const data = await api.getSettings()
        this.ai = { ...DEFAULT_AI, ...data.ai }
        this.weather = { ...DEFAULT_WEATHER, ...data.weather }
        this.loaded = true
      } finally {
        this.loading = false
      }
    },
    async save(patch: SettingsPatch) {
      const data = await api.putSettings(patch)
      this.ai = { ...DEFAULT_AI, ...data.ai }
      this.weather = { ...DEFAULT_WEATHER, ...data.weather }
      return data
    },
    setTheme(theme: 'dark' | 'light') {
      this.theme = theme
      localStorage.setItem(LS_THEME, theme)
      const el = document.documentElement
      el.classList.toggle('dark', theme === 'dark')
      el.classList.toggle('light', theme === 'light')
    },
    toggleTheme() {
      this.setTheme(this.theme === 'dark' ? 'light' : 'dark')
    }
  }
})
