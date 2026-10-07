// 全局共享类型定义（与后端 schema 精确对齐）

export type Priority = 'low' | 'normal' | 'high'

export interface Task {
  id: string
  title: string
  note: string
  done: boolean
  priority: Priority
  created_at?: string
  done_at?: string | null
}

export interface DayData {
  date: string
  tasks: Task[]
  updated?: string | null
  revision: string
}

export interface RangeDay {
  date: string
  total: number
  done: number
  tasks: Task[]
}

export interface RangeResult {
  start: string
  end: string
  days: RangeDay[]
  summary: { total: number; done: number; rate: number }
}

// ---------------- 日记 ----------------
export interface DiaryEntry {
  id: string
  content: string
  created_at?: string
  updated_at?: string
}

export interface DiaryData {
  date: string
  entries: DiaryEntry[]
  updated?: string | null
}

// GET /diary?start=&end= 返回：区间内有日记的日期 -> 条数
export interface DiaryRangeResult {
  start: string
  end: string
  diary: Record<string, number>
}

export interface AiConfig {
  provider: string
  base_url: string
  model: string
  temperature: number
  max_tokens: number
  enabled_models?: string[]
  api_key?: string
  api_key_masked?: string
  has_api_key?: boolean
}

export interface CityItem {
  name: string
  id?: string
  lat?: number | null
  lon?: number | null
  adm?: string
}

export interface WeatherConfig {
  provider: 'open_meteo' | 'qweather'
  api_host: string
  cities: CityItem[]
  cache_minutes: number
  api_key?: string
  api_key_masked?: string
  has_api_key?: boolean
}

// 后端 GET /settings 返回（仅 ai + weather，key 已掩码）
export interface ServerSettings {
  ai: AiConfig
  weather: WeatherConfig
}

// PUT /settings 请求体（局部更新）
export interface SettingsPatch {
  ai?: Partial<AiConfig>
  weather?: Partial<WeatherConfig>
}

export interface CurrentWeather {
  temp: number | null
  feels_like: number | null
  text: string
  icon: string
  humidity: number | null
  pressure: number | null
  wind_dir: string
  wind_speed: number | null
  wind_scale: string
  vis: number | null
  uv_index: number | null
  aqi: number | null
  aqi_category: string
  pm25: number | null
  pm10: number | null
  o3: number | null
}

export interface ForecastDay {
  date: string
  week: string
  temp_max: number | null
  temp_min: number | null
  text_day: string
  icon_day: string
  wind_dir_day: string
  wind_scale_day: string
  uv_index: number | null
  sunrise: string
  sunset: string
  humidity?: number | null
  pressure?: number | null
}

export interface WeatherData {
  city: string
  provider: string
  days_requested: number
  current: CurrentWeather | null
  daily: ForecastDay[]
  fetched_at: string
}

export interface WeekDayItem {
  date: string
  total: number
  done: number
  tasks: Task[]
}

export interface WeekData {
  week_id: string
  week_start: string
  week_end: string
  summary: { total: number; done: number; rate: number }
  days: WeekDayItem[]
  undone: { date: string; title: string; priority: Priority }[]
}

export interface ReportRecord {
  id: string
  week_id: string
  title?: string
  author?: string
  week_start: string
  week_end: string
  generated_at: string
  updated_at?: string
  model: string
  file: string
  stats: { total: number; done: number; rate: number }
  content?: string
}

export interface TemplateItem {
  name: string
  filename: string
}

export interface ModelListResult {
  models: string[]
  source: string
  error?: string
}

export interface ProviderPreset {
  base_url: string
  label: string
}

// ---------------- 用户 / 鉴权 ----------------
export type UserLevel = 'admin' | 'user'

export interface AuthUser {
  id: number
  username: string
  level: UserLevel
  created_at?: string
  avatar?: string
  report_author?: string
}

export interface LoginResult {
  token: string
  user: AuthUser
}

export interface UserPayload {
  username?: string
  password?: string
  level?: UserLevel
}
