import dayjs from 'dayjs'
import isoWeek from 'dayjs/plugin/isoWeek'
import { Solar } from 'lunar-javascript'

dayjs.extend(isoWeek)

export const WEEK_CN = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

export function fmt(d: dayjs.ConfigType, pattern = 'YYYY-MM-DD'): string {
  return dayjs(d).format(pattern)
}

export function today(): string {
  return dayjs().format('YYYY-MM-DD')
}

/** 该日期所在周的周一（ISO，周一起始） */
export function mondayOfWeek(d: dayjs.ConfigType): dayjs.Dayjs {
  return dayjs(d).isoWeekday(1).startOf('day')
}

export interface MonthCell {
  date: string          // YYYY-MM-DD
  day: number           // 日
  inMonth: boolean      // 是否属于当前月
  isToday: boolean
  weekIndex: number     // 0-6，周一为 0
}

/**
 * 生成月视图矩阵：6 行 × 7 列，周一为一周起始。
 * @param year  四位年
 * @param month 1-12
 */
export function monthMatrix(year: number, month: number): MonthCell[][] {
  const first = dayjs(`${year}-${String(month).padStart(2, '0')}-01`)
  const start = mondayOfWeek(first) // 该月 1 号所在周的周一
  const todayStr = today()
  const weeks: MonthCell[][] = []
  let cursor = start
  for (let w = 0; w < 6; w++) {
    const row: MonthCell[] = []
    for (let i = 0; i < 7; i++) {
      row.push({
        date: cursor.format('YYYY-MM-DD'),
        day: cursor.date(),
        inMonth: cursor.month() === first.month(),
        isToday: cursor.format('YYYY-MM-DD') === todayStr,
        weekIndex: i
      })
      cursor = cursor.add(1, 'day')
    }
    weeks.push(row)
  }
  return weeks
}

export interface LunarInfo {
  lunarText: string      // 如「正月初一」/「廿三」
  monthText: string      // 农历月
  dayText: string        // 农历日
  festivals: string[]    // 公历 + 农历节日
  solarTerm: string      // 节气名（当天非节气日则为空）
  ganZhi: string         // 干支日
  isMonthStart: boolean  // 农历初一（月视图优先显示月份）
}

/** 农历 / 节气 / 节日（离线计算，lunar-javascript） */
export function lunarInfo(dateStr: string): LunarInfo {
  const d = dayjs(dateStr)
  const solar = Solar.fromYmd(d.year(), d.month() + 1, d.date())
  const lunar = solar.getLunar()
  const dayText = lunar.getDayInChinese()
  const monthText = lunar.getMonthInChinese()
  const festivals = [...solar.getFestivals(), ...lunar.getFestivals()].filter(Boolean)
  return {
    lunarText: `农历${monthText}月${dayText}`,
    monthText,
    dayText,
    festivals,
    solarTerm: lunar.getJieQi() || '',
    ganZhi: `${lunar.getYearInGanZhi()}年 ${lunar.getMonthInGanZhi()}月 ${lunar.getDayInGanZhi()}日`,
    isMonthStart: dayText === '初一'
  }
}

/** 月视图单元格里显示的农历短语：优先节日 > 节气 > 初一(月份) > 农历日 */
export function lunarCellText(dateStr: string): string {
  const info = lunarInfo(dateStr)
  if (info.festivals.length) return info.festivals[0]
  if (info.solarTerm) return info.solarTerm
  if (info.isMonthStart) return `${info.monthText}月`
  return info.dayText
}

/** 中文星期 */
export function weekdayCn(dateStr: string): string {
  return WEEK_CN[dayjs(dateStr).isoWeekday() - 1]
}

/** 优先级显示配置 */
export const PRIORITY_META: Record<string, { label: string; color: string }> = {
  high: { label: '高', color: '#ef4444' },
  normal: { label: '中', color: '#f59e0b' },
  low: { label: '低', color: '#3b82f6' }
}
