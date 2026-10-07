// 天气展示辅助：图标 emoji、紫外线等级、AQI 颜色

export function weatherEmoji(text = '', icon = ''): string {
  const s = `${text}${icon}`.toLowerCase()
  if (/雷|thunder/.test(s)) return '⛈️'
  if (/雨夹雪|sleet/.test(s)) return '🌨️'
  if (/雪|snow/.test(s)) return '❄️'
  if (/雨|rain|shower|drizzle/.test(s)) return '🌧️'
  if (/雾|霾|fog|haze|mist/.test(s)) return '🌫️'
  if (/阴|overcast/.test(s)) return '☁️'
  if (/多云|cloud|partly/.test(s)) return '⛅'
  if (/晴|clear|sunny/.test(s)) return '☀️'
  return '🌡️'
}

export function uvLabel(uv: number | null | undefined): string {
  if (uv == null) return '—'
  if (uv < 3) return '弱'
  if (uv < 6) return '中等'
  if (uv < 8) return '强'
  if (uv < 11) return '很强'
  return '极强'
}

export function uvColor(uv: number | null | undefined): string {
  if (uv == null) return '#64748b'
  if (uv < 3) return '#10b981'
  if (uv < 6) return '#f59e0b'
  if (uv < 8) return '#fb923c'
  return '#ef4444'
}

// AQI 类别 -> 颜色（类别文案与后端 _aqi_category 对齐）
const AQI_COLOR: Record<string, string> = {
  优: '#10b981',
  良: '#a3e635',
  轻度污染: '#f59e0b',
  中度污染: '#fb923c',
  重度污染: '#ef4444',
  严重污染: '#991b1b'
}

export function aqiColor(category: string): string {
  return AQI_COLOR[category] || '#64748b'
}

export function tempText(v: number | null | undefined, suffix = '°'): string {
  return v == null ? '—' : `${Math.round(v)}${suffix}`
}
