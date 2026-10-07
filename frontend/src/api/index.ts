import client, { TOKEN_KEY } from './client'
import type {
  ServerSettings, SettingsPatch, Task, DayData, RangeResult,
  WeatherData, CityItem, WeekData, ReportRecord, ModelListResult, ProviderPreset,
  AuthUser, LoginResult, UserPayload, DiaryEntry, DiaryData, DiaryRangeResult
} from '@/types'

export { TOKEN_KEY }

export const api = {
  // ---- auth ----
  login: (username: string, password: string): Promise<LoginResult> =>
    client.post('/auth/login', { username, password }).then((r) => r.data),
  logout: (): Promise<{ ok: boolean }> => client.post('/auth/logout').then((r) => r.data),
  me: (): Promise<AuthUser> => client.get('/auth/me').then((r) => r.data),

  // ---- users（管理员） ----
  listUsers: (): Promise<{ users: AuthUser[] }> => client.get('/users').then((r) => r.data),
  createUser: (payload: UserPayload): Promise<AuthUser> =>
    client.post('/users', payload).then((r) => r.data),
  updateUser: (id: number, payload: UserPayload): Promise<AuthUser> =>
    client.put(`/users/${id}`, payload).then((r) => r.data),
  deleteUser: (id: number): Promise<{ ok: boolean }> =>
    client.delete(`/users/${id}`).then((r) => r.data),
  setAvatar: (id: number, avatar: string): Promise<AuthUser> =>
    client.put(`/users/${id}/avatar`, { avatar }).then((r) => r.data),

  // ---- settings / ai ----
  getSettings: (): Promise<ServerSettings> => client.get('/settings').then((r) => r.data),
  putSettings: (patch: SettingsPatch): Promise<ServerSettings> =>
    client.put('/settings', patch).then((r) => r.data),
  testAi: (ai: Partial<ServerSettings['ai']>): Promise<{ ok: boolean; model?: string; reply?: string; error?: string }> =>
    client.post('/settings/test-ai', { ai }).then((r) => r.data),
  getProviders: (): Promise<Record<string, ProviderPreset>> =>
    client.get('/ai/providers').then((r) => r.data),
  getModels: (params: { provider?: string; base_url?: string; api_key?: string }): Promise<ModelListResult> =>
    client.get('/ai/models', { params }).then((r) => r.data),

  // ---- tasks ----
  rangeStats: (start: string, end: string): Promise<RangeResult> =>
    client.get('/tasks', { params: { start, end } }).then((r) => r.data),
  getDay: (date: string): Promise<DayData> =>
    client.get(`/tasks/${date}`).then((r) => r.data),
  putDay: (date: string, tasks: Task[], revision?: string | null): Promise<DayData> =>
    client.put(`/tasks/${date}`, { tasks, revision }).then((r) => r.data),

  // ---- diary ----
  getDiary: (date: string): Promise<DiaryData> =>
    client.get(`/diary/${date}`).then((r) => r.data),
  saveDiary: (date: string, entries: DiaryEntry[]): Promise<DiaryData> =>
    client.put(`/diary/${date}`, { entries }).then((r) => r.data),
  diaryRange: (start: string, end: string): Promise<DiaryRangeResult> =>
    client.get('/diary', { params: { start, end } }).then((r) => r.data),

  // ---- weather ----
  getWeather: (city: string, days = 7): Promise<WeatherData> =>
    client.get('/weather', { params: { city, days } }).then((r) => r.data),
  searchCities: (keyword: string): Promise<CityItem[]> =>
    client.get('/weather/cities', { params: { keyword } }).then((r) => r.data),

  // ---- reports ----
  weekData: (start: string): Promise<WeekData> =>
    client.get('/reports/week-data', { params: { start } }).then((r) => r.data),
  saveReport: (start: string, markdown: string): Promise<ReportRecord> =>
    client.post('/reports/save', { start, markdown }).then((r) => r.data),
  listReports: (): Promise<{ reports: ReportRecord[] }> =>
    client.get('/reports').then((r) => r.data),
  getReport: (id: string): Promise<ReportRecord> =>
    client.get(`/reports/${id}`).then((r) => r.data)
}

// ------------------------------------------------------------------ SSE 流式生成
export interface StreamHandlers {
  onDelta: (text: string) => void
  onDone?: () => void
  onError?: (msg: string) => void
}

/**
 * 调用 POST /api/reports/generate，读取 SSE 流。
 * 返回 abort() 用于中途取消。
 */
export function streamReport(start: string, handlers: StreamHandlers): () => void {
  const ctrl = new AbortController()
  const run = async () => {
    try {
      const resp = await fetch('/api/reports/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(localStorage.getItem(TOKEN_KEY) ? { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` } : {})
        },
        body: JSON.stringify({ start }),
        signal: ctrl.signal
      })
      if (!resp.ok || !resp.body) {
        let msg = `HTTP ${resp.status}`
        try {
          const j = await resp.json()
          if (j?.detail) msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
        } catch { /* ignore */ }
        handlers.onError?.(msg)
        return
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        // SSE 以空行分隔事件
        let idx: number
        while ((idx = buffer.indexOf('\n\n')) >= 0) {
          const rawEvent = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          const line = rawEvent.split('\n').find((l) => l.startsWith('data:'))
          if (!line) continue
          const payload = line.slice(5).trim()
          if (!payload) continue
          try {
            const obj = JSON.parse(payload)
            if (obj.delta) handlers.onDelta(obj.delta)
            else if (obj.done) handlers.onDone?.()
            else if (obj.error) handlers.onError?.(obj.error)
          } catch { /* 忽略半包 */ }
        }
      }
      handlers.onDone?.()
    } catch (e: any) {
      if (e?.name === 'AbortError') return
      handlers.onError?.(e?.message || '生成失败')
    }
  }
  run()
  return () => ctrl.abort()
}

export default api
