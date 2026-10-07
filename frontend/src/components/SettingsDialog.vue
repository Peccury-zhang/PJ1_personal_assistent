<template>
  <el-dialog
    :model-value="modelValue"
    title="设置"
    width="780px"
    top="6vh"
    :close-on-click-modal="false"
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
    @open="onOpen"
  >
    <el-tabs v-model="tab" tab-position="left" class="settings-tabs">
      <!-- ============================ AI ============================ -->
      <el-tab-pane label="AI 模型" name="ai">
        <el-form :model="ai" label-width="96px" label-position="right" class="pa-form">
          <el-form-item label="服务商">
            <el-select v-model="ai.provider" style="width: 100%" @change="applyProvider">
              <el-option
                v-for="(p, key) in providers"
                :key="key"
                :label="p.label"
                :value="key"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="Base URL">
            <el-input v-model="ai.base_url" placeholder="OpenAI 兼容接口地址" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input
              v-model="ai.api_key"
              type="password"
              show-password
              :placeholder="ai.has_api_key ? `已保存：${ai.api_key_masked}（留空则不修改）` : '请填写 API Key'"
            />
          </el-form-item>
          <el-form-item label="模型">
            <div class="row-gap">
              <el-select
                v-model="ai.model"
                filterable
                allow-create
                default-first-option
                placeholder="选择或输入模型名"
                style="flex: 1"
              >
                <el-option v-for="m in modelOptions" :key="m" :label="m" :value="m" />
              </el-select>
              <el-button :loading="loadingModels" @click="loadModels">
                <el-icon><Refresh /></el-icon>&nbsp;加载模型
              </el-button>
            </div>
            <div v-if="modelSource" class="hint">
              <el-tag size="small" :type="modelSource === 'remote' ? 'success' : 'warning'">
                {{ modelSource === 'remote' ? '账号可用模型' : '内置兜底清单' }}
              </el-tag>
              <span v-if="modelError" class="pa-muted"> {{ modelError }}</span>
            </div>
          </el-form-item>
          <el-form-item label="AI可用列表">
            <div class="enabled-box">
              <el-select
                v-model="ai.enabled_models"
                multiple
                filterable
                clearable
                placeholder="点击下拉选择要启用的模型"
                popper-class="enabled-select-popper"
                style="width: 100%"
                @change="saveEnabledModels"
              >
                <el-option v-for="m in availableModels" :key="m" :label="m" :value="m" />
              </el-select>
              <div class="hint pa-muted">勾选的模型才会出现在其他界面（如周报）的模型选择列表中</div>
            </div>
          </el-form-item>
          <el-form-item label="温度">
            <el-slider v-model="ai.temperature" :min="0" :max="2" :step="0.1" show-input :show-input-controls="false" />
          </el-form-item>
          <el-form-item label="最大 tokens">
            <el-input-number v-model="ai.max_tokens" :min="256" :max="32768" :step="256" />
          </el-form-item>
          <el-form-item>
            <el-button :loading="testing" @click="testConn">
              <el-icon><Connection /></el-icon>&nbsp;测试连接
            </el-button>
            <span v-if="testResult" :class="testResult.ok ? 'ok-text' : 'err-text'">
              {{ testResult.ok ? `连接成功（${testResult.model}）` : `失败：${testResult.error}` }}
            </span>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- ============================ 天气 ============================ -->
      <el-tab-pane label="天气" name="weather">
        <el-form :model="weather" label-width="96px" label-position="right" class="pa-form">
          <el-form-item label="数据源">
            <el-radio-group v-model="weather.provider">
              <el-radio-button value="open_meteo">Open-Meteo（免费免Key）</el-radio-button>
              <el-radio-button value="qweather">和风天气</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <template v-if="weather.provider === 'qweather'">
            <el-form-item label="API Host">
              <el-input v-model="weather.api_host" placeholder="如 k838m3jq58.re.qweatherapi.com" />
              <div class="hint pa-muted">免费订阅为专属 API Host（控制台「项目管理」中查看）</div>
            </el-form-item>
            <el-form-item label="API Key">
              <el-input
                v-model="weather.api_key"
                type="password"
                show-password
                :placeholder="weather.has_api_key ? `已保存：${weather.api_key_masked}（留空则不修改）` : '请填写和风 API Key'"
              />
            </el-form-item>
          </template>
          <el-form-item label="缓存分钟">
            <el-input-number v-model="weather.cache_minutes" :min="1" :max="1440" :step="5" />
          </el-form-item>

          <el-form-item label="城市列表">
            <div class="city-box">
              <div class="row-gap">
                <el-input
                  v-model="cityKeyword"
                  placeholder="搜索城市，如：上海 / Shanghai"
                  @keyup.enter="doSearchCity"
                  style="flex: 1"
                />
                <el-button :loading="searchingCity" @click="doSearchCity">
                  <el-icon><Search /></el-icon>&nbsp;搜索
                </el-button>
              </div>
              <div v-if="cityResults.length" class="search-results pa-scroll">
                <div
                  v-for="(c, i) in cityResults"
                  :key="i"
                  class="search-item"
                  @click="addCity(c)"
                >
                  <span>{{ c.name }}</span>
                  <span class="pa-muted">{{ c.adm || '' }} {{ c.lat?.toFixed?.(2) }},{{ c.lon?.toFixed?.(2) }}</span>
                </div>
              </div>
              <div class="city-tags">
                <el-tag
                  v-for="(c, i) in weather.cities"
                  :key="i"
                  closable
                  size="large"
                  @close="removeCity(i)"
                >
                  {{ c.name }}
                </el-tag>
                <span v-if="!weather.cities.length" class="pa-muted">尚未添加城市</span>
              </div>
            </div>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveAll">
        <el-icon><Check /></el-icon>&nbsp;保存
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { useSettingsStore } from '@/stores/settings'
import type { AiConfig, WeatherConfig, CityItem, ProviderPreset } from '@/types'

const props = defineProps<{ modelValue: boolean; focusTab?: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const settings = useSettingsStore()
const tab = ref<'ai' | 'weather'>('ai')

const ai = reactive<AiConfig>({} as AiConfig)
const weather = reactive<WeatherConfig>({ cities: [] } as WeatherConfig)

const providers = ref<Record<string, ProviderPreset>>({
  dashscope: { base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', label: '阿里云百炼 (Qwen)' }
})

const modelOptions = ref<string[]>([])
const modelSource = ref('')
const modelError = ref('')
const loadingModels = ref(false)
const testing = ref(false)
const testResult = ref<{ ok: boolean; model?: string; error?: string } | null>(null)
const saving = ref(false)

// AI 可用列表 = 拉取到的账号模型 ∪ 已勾选 ∪ 当前默认模型
const availableModels = computed(() => {
  const set = new Set<string>(modelOptions.value)
  ;(ai.enabled_models || []).forEach((m) => set.add(m))
  if (ai.model) set.add(ai.model)
  return [...set]
})

const cityKeyword = ref('')
const cityResults = ref<CityItem[]>([])
const searchingCity = ref(false)

async function onOpen() {
  await settings.load()
  Object.assign(ai, JSON.parse(JSON.stringify(settings.ai)), { api_key: '' })
  if (!Array.isArray(ai.enabled_models)) ai.enabled_models = []
  // 从其他界面跳转进来时定位到指定页签（如周报「模型管理」→ ai）
  if (props.focusTab === 'ai' || props.focusTab === 'weather') tab.value = props.focusTab
  const w = JSON.parse(JSON.stringify(settings.weather))
  Object.assign(weather, w, { api_key: '', cities: w.cities || [] })
  modelOptions.value = []
  modelSource.value = ''
  modelError.value = ''
  testResult.value = null
  try {
    const p = await api.getProviders()
    if (p && Object.keys(p).length) providers.value = p
  } catch { /* 用内置兜底 */ }
  // 打开即尝试加载一次模型
  loadModels(true)
}

function applyProvider(key: string) {
  const preset = providers.value[key]
  if (preset?.base_url) ai.base_url = preset.base_url
  modelOptions.value = []
  modelSource.value = ''
  loadModels(true)
}

async function loadModels(silent = false) {
  loadingModels.value = true
  try {
    const res = await api.getModels({ provider: ai.provider, base_url: ai.base_url, api_key: ai.api_key })
    modelOptions.value = res.models || []
    modelSource.value = res.source
    modelError.value = res.error || ''
    if (!silent) {
      if (res.source === 'remote') ElMessage.success(`已加载 ${modelOptions.value.length} 个模型`)
      else ElMessage.warning('无法拉取账号模型，已用内置清单：' + (res.error || ''))
    }
  } catch (e: any) {
    modelSource.value = 'fallback'
    modelError.value = e?.message || '加载失败'
  } finally {
    loadingModels.value = false
  }
}

// 勾选/取消模型后立即保存设置，周报等界面的模型列表随之即时更新
async function saveEnabledModels() {
  try {
    await settings.save({ ai: { ...ai } })
  } catch { /* interceptor 提示 */ }
}

async function testConn() {
  testing.value = true
  testResult.value = null
  try {
    const res = await api.testAi({ ...ai })
    testResult.value = res
    if (res.ok) ElMessage.success('连接成功')
    else ElMessage.error('连接失败：' + res.error)
  } catch (e: any) {
    testResult.value = { ok: false, error: e?.message || '未知错误' }
  } finally {
    testing.value = false
  }
}

async function doSearchCity() {
  if (!cityKeyword.value.trim()) return
  searchingCity.value = true
  try {
    cityResults.value = await settings.load().then(() => api.searchCities(cityKeyword.value.trim()))
    if (!cityResults.value.length) ElMessage.info('未找到匹配城市')
  } catch { /* interceptor 已提示 */ } finally {
    searchingCity.value = false
  }
}

function addCity(c: CityItem) {
  const exists = weather.cities.some((x) => x.name === c.name && String(x.id) === String(c.id))
  if (exists) { ElMessage.info('该城市已在列表中'); return }
  weather.cities.push({ name: c.name, id: c.id, lat: c.lat, lon: c.lon })
}

function removeCity(i: number) {
  weather.cities.splice(i, 1)
}

async function saveAll() {
  saving.value = true
  try {
    await settings.save({
      ai: { ...ai },
      weather: { ...weather, cities: weather.cities }
    })
    ElMessage.success('设置已保存')
    emit('update:modelValue', false)
  } catch { /* interceptor 已提示 */ } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.settings-tabs { --el-tabs-header-height: 42px; }
.settings-tabs :deep(.el-tabs__nav) { width: 108px; }
.settings-tabs :deep(.el-tabs__item) { text-align: left; padding: 0 18px; }
.settings-tabs :deep(.el-tabs__content) { padding-left: 18px; }

.pa-form { padding-top: 4px; }
.row-gap { display: flex; gap: 8px; width: 100%; align-items: center; }
.hint { margin-top: 6px; font-size: 12px; display: flex; align-items: center; gap: 6px; }
.ok-text { color: var(--color-success); margin-left: 10px; font-size: 13px; }
.err-text { color: var(--color-danger); margin-left: 10px; font-size: 13px; }

.city-box { width: 100%; }
.search-results {
  margin-top: 8px; max-height: 180px; overflow-y: auto;
  border: 1px solid var(--color-border); border-radius: var(--radius-sm);
}
.search-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; cursor: pointer; font-size: 13px;
  border-bottom: 1px solid var(--color-border);
}
.search-item:last-child { border-bottom: none; }
.search-item:hover { background: var(--color-surface-hover); }
.city-tags { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }

/* AI 可用列表下拉框 */
.enabled-box { width: 100%; }
</style>

<style>
/* 下拉浮层挂载在 body，需全局样式：选中项黄色对号 */
.enabled-select-popper .el-select-dropdown__item.is-selected {
  color: #f5c518;
  font-weight: 700;
}
</style>
