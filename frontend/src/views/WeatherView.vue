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
            <el-radio-button value="multi">多城市对比</el-radio-button>
          </el-radio-group>
          <el-select
            v-if="mode === 'single'"
            v-model="activeCity"
            style="width: 160px"
            @change="onCityChange"
          >
            <el-option v-for="c in cities" :key="c.name + c.id" :label="c.name" :value="c.name" />
          </el-select>
        </div>
        <div class="tb-right">
          <el-tag size="small" type="info" effect="plain">{{ providerLabel }}</el-tag>
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
              <div class="hero-temp">{{ tempText(cur.temp) }}<span class="deg">°C</span></div>
              <div class="hero-feels pa-secondary">体感 {{ tempText(cur.feels_like) }}°C</div>
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
                <div class="fc-temp"><b>{{ tempText(d.temp_max) }}°</b> / {{ tempText(d.temp_min) }}°</div>
                <div class="fc-sub pa-muted">{{ d.wind_scale_day || d.wind_dir_day || '—' }}</div>
                <div class="fc-sub" :style="{ color: uvColor(d.uv_index) }">紫外线 {{ uvLabel(d.uv_index) }}</div>
              </div>
            </div>
          </section>
        </template>
        <el-empty v-else description="暂无天气数据，点击刷新重试" />
      </div>

      <!-- 多城市对比 -->
      <div v-else v-loading="!!loadingCity" class="multi">
        <div
          v-for="c in cities"
          :key="c.name + c.id"
          class="city-card pa-card"
          @click="switchTo(c.name)"
        >
          <template v-if="weatherStore.dataMap[c.name]?.current">
            <div class="cc-head">
              <span class="cc-city">{{ c.name }}</span>
              <span class="cc-emoji">{{ weatherEmoji(weatherStore.dataMap[c.name].current.text, weatherStore.dataMap[c.name].current.icon) }}</span>
            </div>
            <div class="cc-temp">{{ tempText(weatherStore.dataMap[c.name].current.temp) }}°C</div>
            <div class="cc-text pa-secondary">{{ weatherStore.dataMap[c.name].current.text }}</div>
            <div class="cc-metrics">
              <span class="pa-muted">风</span>{{ weatherStore.dataMap[c.name].current.wind_scale || '—' }}
              <span class="pa-muted">空气</span>
              <b :style="{ color: aqiColor(weatherStore.dataMap[c.name].current.aqi_category) }">
                {{ weatherStore.dataMap[c.name].current.aqi_category || '—' }}
              </b>
            </div>
          </template>
          <div v-else class="cc-loading pa-muted">加载中…</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { useSettingsStore } from '@/stores/settings'
import { useWeatherStore } from '@/stores/weather'
import { weatherEmoji, uvLabel, uvColor, aqiColor, tempText } from '@/utils/weather'
import { today } from '@/utils/date'

const emit = defineEmits<{ (e: 'open-settings'): void }>()
const settings = useSettingsStore()
const weatherStore = useWeatherStore()

const mode = ref<'single' | 'multi'>('single')
const activeCity = ref('')
const todayStr = today()

const cities = computed(() => settings.weather.cities || [])
const providerLabel = computed(() => settings.weatherProviderLabel)
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

onMounted(async () => {
  await settings.load()
  if (cities.value.length) {
    activeCity.value = cities.value[0].name
    await weatherStore.load(activeCity.value, 7).catch(() => {})
    // 预载其余城市，便于多城市对比
    weatherStore.loadMany(cities.value, 7)
  }
})
</script>

<style scoped>
.weather-view { display: flex; flex-direction: column; gap: 16px; height: 100%; }

.toolbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.tb-left, .tb-right { display: flex; align-items: center; gap: 10px; }

.single { display: flex; flex-direction: column; gap: 16px; }

.hero { padding: 20px 24px; display: flex; align-items: center; justify-content: space-between; }
.hero-left { display: flex; align-items: center; gap: 16px; }
.hero-emoji { font-size: 56px; line-height: 1; }
.hero-city { font-size: 22px; font-weight: 800; color: var(--color-text-primary); }
.hero-text { font-size: 15px; margin-top: 3px; }
.hero-updated { font-size: 12px; margin-top: 5px; }
.hero-right { text-align: right; }
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

.multi { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
.city-card { padding: 18px; cursor: pointer; transition: all var(--transition-fast); }
.city-card:hover { border-color: var(--color-border-hover); transform: translateY(-2px); }
.cc-head { display: flex; align-items: center; justify-content: space-between; }
.cc-city { font-size: 17px; font-weight: 700; color: var(--color-text-primary); }
.cc-emoji { font-size: 30px; }
.cc-temp { font-size: 34px; font-weight: 800; color: var(--color-primary); margin: 6px 0 2px; }
.cc-text { font-size: 13px; }
.cc-metrics { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--color-border); font-size: 13px; color: var(--color-text-primary); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.cc-metrics .pa-muted { font-size: 11px; }
.cc-loading { padding: 30px 0; text-align: center; font-size: 13px; }

@media (max-width: 768px) {
  .metrics { grid-template-columns: repeat(2, 1fr); }
}
</style>
