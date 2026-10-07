<template>
  <div class="weather-view">
    <!-- 无城市 -->
    <el-empty v-if="!cities.length" description="尚未配置城市">
      <el-button type="primary" @click="emit('open-settings')">
        <el-icon><Setting /></el-icon>&nbsp;去添加城市
      </el-button>
    </el-empty>

    <template v-else>
      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="tb-left">
          <el-radio-group v-model="mode">
            <el-radio-button value="single">单城市</el-radio-button>
            <el-radio-button value="multi">多城市</el-radio-button>
          </el-radio-group>
          <div v-if="mode === 'single'" class="tb-city-row">
            <span class="tb-label">默认城市：</span>
            <el-select v-model="activeCity" style="width: 160px" @change="onCityChange">
              <el-option v-for="c in cities" :key="c.name + c.id" :label="c.name" :value="c.name" />
            </el-select>
            <el-button size="small" @click="addCityVisible = true">管理城市</el-button>
          </div>
        </div>
        <div class="tb-right">
          <span class="tb-label">服务：</span>
          <el-select v-model="providerSel" style="width: 150px" @change="onProviderChange">
            <el-option label="Open-Meteo" value="open_meteo" />
            <el-option label="和风天气" value="qweather" />
          </el-select>
          <el-button :loading="!!loadingCity" @click="refresh">
            <el-icon><Refresh /></el-icon>&nbsp;刷新
          </el-button>
        </div>
      </div>

      <!-- 单城市 -->
      <div v-if="mode === 'single'" v-loading="!!loadingCity" class="single">
        <template v-if="cur">
          <section class="hero pa-card">
            <div class="hero-left">
              <div class="hero-emoji">{{ weatherEmoji(cur.text, cur.icon) }}</div>
              <div>
                <div class="hero-city">{{ data.city }}</div>
                <div class="hero-text pa-secondary">{{ cur.text }}</div>
                <div class="hero-updated pa-muted">更新于 {{ timeOf(data.fetched_at) }}</div>
              </div>
            </div>
            <div class="hero-right">
              <div class="hero-temp">{{ tempText(cur.temp, '') }}<span class="deg">℃</span></div>
              <div class="hero-feels pa-secondary">体感 {{ tempText(cur.feels_like, '') }}℃</div>
            </div>
          </section>

          <section class="metrics pa-card">
            <div v-for="m in metrics" :key="m.label" class="metric">
              <div class="metric-label pa-muted">{{ m.label }}</div>
              <div class="metric-value" :style="m.color ? { color: m.color } : {}">{{ m.value }}</div>
            </div>
          </section>

          <section class="forecast">
            <div class="fc-title">未来 {{ data.daily.length }} 天预报</div>
            <div class="fc-strip pa-scroll">
              <div v-for="d in data.daily" :key="d.date" class="fc-card pa-card" :class="{ 'fc-today': d.date === todayStr }">
                <div class="fc-week">{{ d.date === todayStr ? '今天' : d.week }}</div>
                <div class="fc-date pa-muted">{{ shortDate(d.date) }}</div>
                <div class="fc-emoji">{{ weatherEmoji(d.text_day, d.icon_day) }}</div>
                <div class="fc-text">{{ d.text_day }}</div>
                <div class="fc-temp"><b>{{ tempText(d.temp_max) }}</b> / {{ tempText(d.temp_min) }}</div>
                <div class="fc-sub pa-muted">{{ d.wind_scale_day || d.wind_dir_day || '—' }}</div>
                <div class="fc-sub pa-muted">{{ hpa(d.pressure) }}</div>
                <div class="fc-sub" :style="{ color: uvColor(d.uv_index) }">紫外线 {{ uvLabel(d.uv_index) }}</div>
              </div>
            </div>
          </section>
        </template>
        <el-empty v-else description="暂无天气数据，点击刷新重试" />
      </div>

      <!-- 多城市：每城一行，显示未来七天天气 -->
      <div v-else v-loading="!!loadingCity" class="multi">
        <div
          v-for="c in cities"
          :key="c.name + c.id"
          class="mrow pa-card"
          @click="switchTo(c.name)"
        >
          <template v-if="weatherStore.dataMap[c.name]?.daily?.length">
            <div class="mrow-city">
              <div class="mrow-name">{{ c.name }}</div>
            </div>
            <div class="mrow-days">
              <div v-for="d in weatherStore.dataMap[c.name].daily.slice(0, 7)" :key="d.date" class="mrow-day">
                <div class="d-week">{{ d.date === todayStr ? '今天' : d.week }}</div>
                <div class="d-emoji">{{ weatherEmoji(d.text_day, d.icon_day) }}</div>
                <div class="d-text">{{ d.text_day }}</div>
                <div class="d-temp"><b>{{ tempText(d.temp_max) }}</b> / {{ tempText(d.temp_min) }}</div>
                <div class="d-sub pa-muted">风 {{ d.wind_scale_day || d.wind_dir_day || '—' }}</div>
                <div class="d-sub pa-muted">{{ hpa(d.pressure) }}</div>
                <div class="d-sub" :style="{ color: uvColor(d.uv_index) }">紫外线 {{ uvLabel(d.uv_index) }}</div>
              </div>
            </div>
          </template>
          <div v-else class="mrow-loading pa-muted">加载中…</div>
        </div>
      </div>
    </template>

    <!-- 管理城市弹窗：搜索添加 + 已添加城市可删除 -->
    <el-dialog v-model="addCityVisible" title="管理城市" width="460px">
      <div class="mc-sec">
        <div class="mc-sec-title">搜索添加</div>
        <div class="add-city-row">
          <el-input
            v-model="cityKeyword"
            placeholder="搜索城市，如：上海 / Shanghai"
            style="flex: 1"
            @keyup.enter="doSearchCity"
          />
          <el-button :loading="searchingCity" @click="doSearchCity">搜索</el-button>
        </div>
        <div class="pa-muted add-city-tip">仅能添加 Open-Meteo 与和风天气支持的城市，以搜索结果为准，点击结果即添加。</div>
        <div v-if="cityResults.length" class="add-city-results pa-scroll">
          <div v-for="(c, i) in cityResults" :key="i" class="add-city-item" @click="addCity(c)">
            <span>{{ c.name }}</span>
            <span class="pa-muted">{{ c.adm || '' }} {{ c.lat?.toFixed?.(2) }},{{ c.lon?.toFixed?.(2) }}</span>
          </div>
        </div>
      </div>
      <div class="mc-sec">
        <div class="mc-sec-title">已添加城市</div>
        <div v-if="cities.length" class="mc-list pa-scroll">
          <div v-for="(c, i) in cities" :key="c.name + c.id" class="mc-item">
            <span class="mc-name">{{ c.name }}</span>
            <span class="pa-muted mc-coord">{{ c.lat?.toFixed?.(2) }},{{ c.lon?.toFixed?.(2) }}</span>
            <el-button size="small" text type="danger" @click="removeCity(i)">删除</el-button>
          </div>
        </div>
        <div v-else class="pa-muted add-city-tip">尚未添加城市</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { useSettingsStore } from '@/stores/settings'
import { useWeatherStore } from '@/stores/weather'
import { weatherEmoji, uvLabel, uvColor, aqiColor, tempText } from '@/utils/weather'
import { today } from '@/utils/date'
import type { CityItem } from '@/types'

const emit = defineEmits<{ (e: 'open-settings'): void }>()
const settings = useSettingsStore()
const weatherStore = useWeatherStore()

const mode = ref<'single' | 'multi'>('single')
const activeCity = ref('')
const todayStr = today()

// 记住最后一次使用的默认城市，下次进入优先恢复
const LS_CITY = 'weather_last_city'
watch(activeCity, (v) => { if (v) localStorage.setItem(LS_CITY, v) })

const cities = computed(() => settings.weather.cities || [])

// 气压展示：不带「气压」字样，直接如 1012hPa
function hpa(v: number | null | undefined): string {
  return v == null ? '—' : `${Math.round(v)}hPa`
}
const providerSel = ref<'open_meteo' | 'qweather'>('open_meteo')
const loadingCity = computed(() => weatherStore.loadingCity)
const data = computed(() => weatherStore.dataMap[activeCity.value])
const cur = computed(() => data.value?.current || null)

const metrics = computed(() => {
  if (!cur.value) return []
  const c = cur.value
  return [
    { label: '气压', value: c.pressure != null ? `${Math.round(c.pressure)} hPa` : '—' },
    { label: '湿度', value: c.humidity != null ? `${c.humidity}%` : '—' },
    { label: '风力', value: `${c.wind_dir || ''} ${c.wind_scale || ''}`.trim() || '—' },
    { label: '风速', value: c.wind_speed != null ? `${c.wind_speed} km/h` : '—' },
    { label: '紫外线', value: `${uvLabel(c.uv_index)}${c.uv_index != null ? ` (${c.uv_index})` : ''}`, color: uvColor(c.uv_index) },
    { label: '空气质量', value: `${c.aqi_category || '—'}${c.aqi != null ? ` ${c.aqi}` : ''}`, color: aqiColor(c.aqi_category) },
    { label: 'PM2.5', value: c.pm25 != null ? `${Math.round(c.pm25)}` : '—' },
    { label: '能见度', value: c.vis != null ? `${c.vis} km` : '—' }
  ]
})

function timeOf(ts: string) {
  return ts ? dayjs(ts.replace('T', ' ')).format('HH:mm') : '—'
}
function shortDate(d: string) {
  return dayjs(d).format('M/D')
}

async function onCityChange(city: string) {
  if (!weatherStore.dataMap[city]) await weatherStore.load(city, 7).catch(() => {})
}
async function refresh() {
  if (mode.value === 'multi') {
    for (const c of cities.value) weatherStore.clearCache(c.name)
    await weatherStore.loadMany(cities.value, 7)
  } else {
    await weatherStore.load(activeCity.value, 7, true).catch(() => {})
  }
  ElMessage.success('已刷新')
}
function switchTo(city: string) {
  activeCity.value = city
  mode.value = 'single'
}

// 切换天气服务：持久化到设置后清缓存重拉；未配置和风时后端报「无法获取数据」
async function onProviderChange(p: 'open_meteo' | 'qweather') {
  const prev = settings.weather.provider
  try {
    // 回传完整 weather 对象：后端对缺失字段填默认值，局部传参会清空 cities
    await settings.save({ weather: { ...settings.weather, provider: p, api_key: '' } })
  } catch {
    providerSel.value = prev
    return
  }
  weatherStore.clearCache()
  if (mode.value === 'multi') await weatherStore.loadMany(cities.value, 7)
  else await weatherStore.load(activeCity.value, 7, true).catch(() => {})
}

// ---------------- 添加城市 ----------------
const addCityVisible = ref(false)
const cityKeyword = ref('')
const cityResults = ref<CityItem[]>([])
const searchingCity = ref(false)

async function doSearchCity() {
  const kw = cityKeyword.value.trim()
  if (!kw) return
  searchingCity.value = true
  try {
    cityResults.value = await api.searchCities(kw)
    if (!cityResults.value.length) ElMessage.info('未找到匹配城市')
  } catch { /* interceptor 已提示 */ } finally {
    searchingCity.value = false
  }
}

// 点击搜索结果即添加：立即持久化到设置，并预拉该城市天气
async function addCity(c: CityItem) {
  const exists = cities.value.some((x) => x.name === c.name && String(x.id) === String(c.id))
  if (exists) { ElMessage.info('该城市已在列表中'); return }
  const next = [...cities.value, { name: c.name, id: c.id || '', lat: c.lat, lon: c.lon }]
  try {
    // 回传完整 weather 对象：后端对缺失字段填默认值，局部传参会清空 cities
    await settings.save({ weather: { ...settings.weather, api_key: '', cities: next } })
  } catch { return }
  cityResults.value = cityResults.value.filter((x) => !(x.name === c.name && String(x.id) === String(c.id)))
  ElMessage.success(`已添加城市：${c.name}`)
  if (!activeCity.value) activeCity.value = c.name
  weatherStore.load(c.name, 7).catch(() => {})
}

// 删除已添加城市：立即持久化；若删的是当前默认城市则回落到第一个
async function removeCity(i: number) {
  const target = cities.value[i]
  if (!target) return
  const next = cities.value.filter((_, x) => x !== i)
  try {
    await settings.save({ weather: { ...settings.weather, api_key: '', cities: next } })
  } catch { return }
  weatherStore.clearCache(target.name)
  if (activeCity.value === target.name) {
    activeCity.value = next[0]?.name || ''
    if (activeCity.value) weatherStore.load(activeCity.value, 7).catch(() => {})
  }
  ElMessage.success(`已删除城市：${target.name}`)
}

onMounted(async () => {
  await settings.load()
  providerSel.value = settings.weather.provider || 'open_meteo'
  if (cities.value.length) {
    // 优先用上次选择的默认城市，已删除则回落第一个
    const saved = localStorage.getItem(LS_CITY) || ''
    activeCity.value = cities.value.some((c) => c.name === saved) ? saved : cities.value[0].name
    await weatherStore.load(activeCity.value, 7).catch(() => {})
    // 预载其余城市，便于多城市对比
    weatherStore.loadMany(cities.value, 7)
  }
})
</script>

<style scoped>
.weather-view { display: flex; flex-direction: column; gap: 16px; height: 100%; }

.toolbar { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.tb-left, .tb-right { display: flex; align-items: center; gap: 10px; }
.tb-left { flex-direction: column; align-items: flex-start; }
.tb-city-row { display: flex; align-items: center; gap: 10px; }
.tb-label { font-size: 13px; color: var(--color-text-secondary); }

.single { display: flex; flex-direction: column; gap: 16px; }

.hero { padding: 20px 24px; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; }
.hero-left { display: flex; align-items: center; gap: 16px; }
.hero-emoji { font-size: 56px; line-height: 1; }
.hero-city { font-size: 22px; font-weight: 800; color: var(--color-text-primary); }
.hero-text { font-size: 15px; margin-top: 3px; }
.hero-updated { font-size: 12px; margin-top: 5px; }
.hero-right { grid-column: 2; text-align: center; }
.hero-temp { font-size: 46px; font-weight: 800; color: var(--color-primary); line-height: 1; }
.hero-temp .deg { font-size: 20px; font-weight: 600; }
.hero-feels { font-size: 13px; margin-top: 6px; }

.metrics { padding: 18px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.metric { display: flex; flex-direction: column; gap: 5px; }
.metric-label { font-size: 12px; }
.metric-value { font-size: 16px; font-weight: 700; color: var(--color-text-primary); }

.forecast { display: flex; flex-direction: column; gap: 10px; }
.fc-title { font-size: 14px; font-weight: 600; color: var(--color-text-primary); }
.fc-strip { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 4px; }
.fc-card {
  flex: 0 0 auto; width: 118px; padding: 14px 10px; text-align: center;
  display: flex; flex-direction: column; gap: 5px; align-items: center;
}
.fc-card.fc-today { border-color: var(--color-primary); box-shadow: 0 0 0 1px rgba(245,158,11,.3); }
.fc-week { font-size: 13px; font-weight: 700; color: var(--color-text-primary); }
.fc-date { font-size: 11px; }
.fc-emoji { font-size: 30px; margin: 4px 0; }
.fc-text { font-size: 12px; color: var(--color-text-secondary); }
.fc-temp { font-size: 13px; color: var(--color-text-primary); }
.fc-temp b { color: var(--color-primary); }
.fc-sub { font-size: 11px; }

.multi { display: flex; flex-direction: column; gap: 12px; }
.mrow { display: flex; align-items: center; gap: 18px; padding: 14px 18px; cursor: pointer; transition: all var(--transition-fast); }
.mrow:hover { border-color: var(--color-border-hover); }
.mrow-city { flex: 0 0 90px; }
.mrow-name { font-size: 16px; font-weight: 700; color: var(--color-text-primary); }
.mrow-days { display: flex; gap: 8px; flex: 1; min-width: 0; }
.mrow-day {
  flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; gap: 3px;
  padding: 8px 4px; border-radius: 8px; background: rgba(127, 127, 127, .08);
}
.d-week { font-size: 12px; font-weight: 700; color: var(--color-text-primary); }
.d-emoji { font-size: 22px; line-height: 1.2; }
.d-text { font-size: 11px; color: var(--color-text-secondary); }
.d-temp { font-size: 12px; color: var(--color-text-primary); }
.d-temp b { color: var(--color-primary); }
.d-sub { font-size: 10px; color: var(--color-text-secondary); white-space: nowrap; }
.mrow-loading { width: 100%; text-align: center; padding: 18px 0; font-size: 13px; }

/* 管理城市弹窗 */
.mc-sec + .mc-sec { margin-top: 16px; }
.mc-sec-title { font-size: 13px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 8px; }
.mc-list { max-height: 220px; display: flex; flex-direction: column; gap: 4px; }
.mc-item {
  display: flex; align-items: center; gap: 10px; padding: 6px 10px;
  border-radius: 6px; background: rgba(127, 127, 127, .08);
}
.mc-name { font-size: 13px; font-weight: 600; color: var(--color-text-primary); }
.mc-coord { flex: 1; font-size: 11px; }
.add-city-row { display: flex; gap: 8px; }
.add-city-tip { margin: 8px 0; font-size: 12px; line-height: 1.6; }
.add-city-results { max-height: 260px; display: flex; flex-direction: column; }
.add-city-item {
  display: flex; justify-content: space-between; gap: 10px; padding: 8px 10px;
  border-radius: 6px; cursor: pointer; font-size: 13px; color: var(--color-text-primary);
}
.add-city-item:hover { background: rgba(127, 127, 127, .15); }

@media (max-width: 768px) {
  .metrics { grid-template-columns: repeat(2, 1fr); }
}
</style>
