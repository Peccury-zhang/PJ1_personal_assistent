# 个人全能助手（Personal Assistant）系统 —— 设计文档

> 工程目录：`E:\Data_center\PJ\PJ1_weekly_report`
> 运行方式：本地 Windows 启动，浏览器操作
> 版本：v0.3（设计稿，已按用户反馈修订）　日期：2026-10-06

---

## 1. 项目概述

**整个系统定名为「个人全能助手」**：一个本地运行的个人效率平台。周报只是其中一项任务/功能模块，后续还将扩展更多助手能力（智能对话、备忘、习惯等，见 §7.4）。本期包含四个界面：

| 界面 | 说明 | 本期是否实现 |
|---|---|---|
| 主界面（日历） | 日历视图 + 当日详情（日期/星期、农历、节日、节气、天气、当日任务、已完成任务）+ 按周批量编辑任务 | ✅ |
| 周报 | 汇总一周任务完成情况，调用 AI（Qwen）生成周报，输出 `.md` 文件 | ✅ |
| 天气 | 当天 + 未来 7 天天气详情（气压、紫外线、风力、污染系数等），支持多城市 | ✅ |
| 智能助手 | 系统同名模块：AI 对话助手界面，本期仅占位 | ❌（仅占位） |

全局约定：**周从周一开始（ISO 8601，周一~周日）**；所有 AI 场景**默认统一使用 `qwen3.8-flash`** 模型，可在设置中通过下拉框随时切换（下拉框动态加载当前阿里云账号可用的全部模型，见 §5.2 / §7.2）。

所有用户数据以 **JSON 格式** 保存在本地 `persistent/` 目录；生成的周报以 **Markdown 格式** 保存在 `weekly_report_output/` 目录。

---

## 2. 参考架构分析

### 2.1 后端参照：`E:\Data_center\yc2_robot\vision_label`

该工程是一个"FastAPI 单体 + 纯静态前端 + JSON 文件存储"的本地工具，核心特点（均已阅读源码确认）：

1. **入口极简**（`app.py`）：
   - `create_app()` 创建 FastAPI 应用，`uvicorn.run(host="127.0.0.1", port=8765)`；
   - `app.include_router(router)` 挂载 `/api` 前缀的 REST 路由（`backend/api.py`）；
   - `app.mount("/", StaticFiles(directory="web", html=True))` 直接托管前端静态文件 → **单进程、单端口，浏览器打开 `http://localhost:8765` 即用**；
   - 统一异常处理器：`ValueError→400`、`FileNotFoundError→404`、自定义 `ConflictError→409`、`RequestValidationError→422`（带中文可操作提示）；
   - 对 `/`、`.js`、`.css`、`.html` 响应加 `Cache-Control: no-cache` 中间件，防止前端缓存新旧接口不兼容。
2. **分层清晰**（`backend/`）：
   - `api.py`：路由 + Pydantic 请求体校验（如 `SaveBody(status, regions, revision)`），只做参数校验与编排，不含存储细节；
   - `store.py`：存储层。JSON 文件读写，**原子写入**（`tempfile.mkstemp` → `json.dump` → `fsync` → `os.replace`）、**乐观并发控制**（`revision` = 文件内容 sha256，保存时比对，不一致抛 `ConflictError`）、`threading.RLock` 串行化写入、路径穿越防护（`p.parent != PROJECTS_DIR` 校验）；
   - `geometry.py` / `export.py`：纯逻辑与导出，与路由解耦。
3. **无数据库**：一切皆 JSON 文件，人类可读、可直接备份。

**本项目完全沿用该模式**：`app.py` + `backend/`（api、store、services）+ `web/`（前端构建产物）+ `persistent/`（数据）。

### 2.2 前端风格参照：`C:\Users\15401\Desktop\G3\qyh_jushen_frontend`

技术栈（`package.json` 已确认）：**Vue 3 + TypeScript + Vite + Element Plus（含 @element-plus/icons-vue）+ Pinia + vue-router + axios + dayjs**。

风格要点（`App.vue`、`layouts/MainLayout.vue`、`styles/modern-theme.css` 已确认）：

1. **布局骨架**：顶部标题栏（logo + 标题 + 用户区）＋ **左侧可折叠侧边栏**（`nav-item` = SvgIcon 图标 + 文字 label + tooltip，激活项高亮）＋ 中央工作区 ＋ 底部状态栏；
2. **主题体系**：CSS 变量驱动的暗色/亮色双主题（`html.dark` / `html.light` 类切换），暗色为默认；
3. **配色**（直接复用其色板）：
   - 暗色：背景 `#0F172A` / 面板 `#1E293B` / 边框 `rgba(248,250,252,0.1)`；
   - 主色（强调）：琥珀 `#F59E0B`，辅助紫 `#8B5CF6`；
   - 语义色：success `#10B981`、danger `#EF4444`、info `#3B82F6`；
   - 文字：`#F8FAFC` / `#CBD5E1` / `#94A3B8`；
   - 圆角 8/12px，阴影 `0 4px 20px rgba(0,0,0,.2)`，过渡 0.2~0.3s ease；
4. **组件习惯**：`el-tooltip`、`el-dropdown`、`el-button-group` 等 Element Plus 组件 + 自研 `SvgIcon.vue` 图标组件。

> 取舍：参考工程中的 Three.js / vue-flow / xterm / protobuf 等与本项目无关，不引入。

---

## 3. 总体架构与技术栈

```
┌────────────────────────── 浏览器 (http://localhost:8765) ──────────────────────────┐
│  Vue3 + TS + Element Plus 单页应用（构建产物由 FastAPI 托管）                        │
│  视图：Calendar / Report / Weather / Butler(占位)   Pinia stores   axios            │
└───────────────────────────────────┬────────────────────────────────────────────────┘
                                    │ REST /api/*  (JSON, SSE 流式)
┌───────────────────────────────────▼────────────────────────────────────────────────┐
│  FastAPI 单体后端  (app.py + backend/)                                              │
│  ├─ api.py        路由 + Pydantic 校验 + 统一异常处理                                │
│  ├─ store.py      persistent/ JSON 原子读写 + revision 乐观并发                      │
│  ├─ services/                                                                       │
│  │   ├─ calendar.py   农历/节气/节日（后端计算，lunardate + 节气表）                  │
│  │   ├─ weather.py    天气 Provider 抽象 + 本地缓存（和风/Open-Meteo）                │
│  │   ├─ ai.py         LLM Provider 抽象（OpenAI 兼容：DashScope-Qwen / Ollama / …）  │
│  │   └─ report.py     周报数据聚合 + Prompt 模板 + Markdown 落盘                      │
│  └─ config        persistent/settings.json（API Key、模型、城市列表）                 │
└──────────────┬──────────────────────────────┬──────────────────────────────────────┘
               │                              │
     persistent/*.json（任务/设置/        weekly_report_output/*.md（周报产物）
     天气缓存/周报元数据）                 外部：DashScope API、和风天气 API
```

### 技术栈清单（均为开源，除云端 API 本身）

| 层 | 选型 | 版本 | 开源协议 | 选择理由 |
|---|---|---|---|---|
| 后端框架 | FastAPI + uvicorn | ≥0.110 | MIT / BSD | 与 vision_label 一致，自带 Pydantic 校验、SSE 流式支持 |
| 数据校验 | Pydantic v2 | ≥2.5 | MIT | 请求体模型化，错误信息可中文化 |
| HTTP 客户端 | httpx | ≥0.27 | BSD | 后端调用天气/LLM API，支持异步与流式 |
| 农历/节气 | lunardate + sxtwl（寿星天文历） | — | MIT / GPL 双许可注意¹ | 农历日期、二十四节气、传统节日推算 |
| 前端框架 | Vue 3 + TypeScript + Vite | ^3.4 / ^5.3 / ^5.4 | MIT | 与 qyh_jushen_frontend 一致 |
| UI 组件库 | Element Plus + @element-plus/icons-vue | ^2.5 | MIT | 参考工程同款；日历、表单、抽屉、消息组件齐全 |
| 状态管理 | Pinia | ^2.1 | MIT | 参考工程同款 |
| 路由 | vue-router | ^4.2 | MIT | 四个视图切换 |
| HTTP | axios | ^1.6 | MIT | 参考工程同款 |
| 日期 | dayjs | ^1.11 | MIT | 周次计算、格式化 |
| Markdown | md-editor-v3 | ^5 | MIT/Apache | 周报编辑 + 实时预览渲染 |
| 图标 | Element Plus icons + iconify(json 离线包) | — | MIT / Apache | 侧边栏图标：Calendar、Document、Cloudy/Sunny、House、Setting |

> ¹ `sxtwl` 为 GPL，若介意可只用 `lunardate`（MIT，农历）+ 内置节气近似公式（VSOP87 精简版，误差 ±1 天内），或前端改用 `lunar-javascript`（MIT，农历/节气/节日一体，纯 JS 离线计算）。**推荐方案：前端 `lunar-javascript` 负责日历渲染层的农历/节气/节日展示，后端不再重复实现**，详见 §5.1。

### 目录结构规划

```
PJ1_weekly_report/
├─ app.py                     # 入口：python app.py → http://localhost:8765
├─ launcher.py                # 图形启动器源码（tkinter 启动/停止，无黑窗口）
├─ start.bat / build.bat / build_launcher.bat   # 一键启动 / 前端构建 / 启动器打包 exe
├─ backend/
│  ├─ __init__.py
│  ├─ api.py                  # /api/* 路由
│  ├─ store.py                # persistent JSON 存储（原子写 + revision）
│  └─ services/
│     ├─ __init__.py
│     ├─ weather.py           # 天气 Provider + 缓存
│     ├─ ai.py                # LLM Provider（OpenAI 兼容客户端封装）
│     └─ report.py            # 周报生成（数据聚合 + Prompt + 落盘）
├─ frontend/                  # Vue3 工程（开发态）
│  ├─ package.json / vite.config.ts / index.html
│  └─ src/
│     ├─ main.ts / App.vue
│     ├─ router/index.ts
│     ├─ styles/theme.css     # 移植 qyh modern-theme.css 色板
│     ├─ layouts/MainLayout.vue   # 顶栏 + 左侧边栏 + 工作区
│     ├─ components/
│     │  ├─ SvgIcon.vue / PanelContainer.vue
│     │  ├─ calendar/ (MonthGrid.vue, DayDetailDrawer.vue, WeekTaskEditor.vue)
│     │  ├─ weather/ (CityCard.vue, TodayDetail.vue, ForecastStrip.vue, CityPicker.vue)
│     │  └─ report/ (WeekPicker.vue, ReportPreview.vue, AiSettingsDialog.vue)
│     ├─ views/ (CalendarView.vue, ReportView.vue, WeatherView.vue, ButlerView.vue)
│     ├─ stores/ (settings.ts, tasks.ts, weather.ts, report.ts)
│     └─ api/client.ts + 各模块 api
├─ web/                       # 前端构建产物（vite build 输出，FastAPI 托管）
├─ persistent/                # ★ 所有持久化数据（JSON）
│  ├─ tasks/2026-10-06.json   # 按天一个文件
│  ├─ settings.json           # AI/天气配置、城市列表（API Key 本地明文，见 §9 风险）
│  ├─ weather_cache/2026-10-06_北京.json
│  └─ reports_index.json      # 已生成周报的元数据索引
├─ weekly_report_output/      # ★ AI 生成的 .md 周报
│  └─ weekly_report_2026-W41_20261006.md
└─ weekly_report.md           # 本设计文档
```

---

## 4. 数据模型（persistent/ JSON Schema）

### 4.1 任务 `persistent/tasks/YYYY-MM-DD.json`（按天存储，便于原子写与并发控制）

```jsonc
{
  "date": "2026-10-06",
  "tasks": [
    {
      "id": "a1b2c3d4",            // uuid4 hex
      "title": "整理项目文档",
      "note": "可选备注",
      "done": true,
      "priority": "normal",        // low | normal | high
      "created_at": "2026-10-06T09:00:00",
      "done_at": "2026-10-06T15:30:00"
    }
  ],
  "updated": "2026-10-06T15:30:00",
  "revision": "<sha256>"           // store.py 读时计算，写时比对（乐观并发）
}
```

### 4.2 设置 `persistent/settings.json`

```jsonc
{
  "ai": {
    "provider": "dashscope",       // dashscope | ollama | openai | deepseek | zhipu（均走 OpenAI 兼容协议）
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "api_key": "sk-xxxx",
    "model": "qwen3.8-flash",      // 全局统一默认模型，所有 AI 场景共用；可随时在设置下拉框切换
    "temperature": 0.7,
    "max_tokens": 4096,
    "report_style": "简洁要点式"    // 传给 Prompt 的风格偏好
  },
  "weather": {
    "provider": "qweather",        // qweather | open_meteo
    "api_host": "k838m3jq58.re.qweatherapi.com",  // ★ 和风专属 API Host（免费订阅新项目分配，已填入）
    "api_key": "",                 // ★ 和风 API Key —— 待用户从控制台补充（open_meteo 无需 key）
    "cities": [                    // 多城市列表，第一个为默认
      { "name": "北京", "id": "101010100", "lat": 39.90, "lon": 116.41 }
    ],
    "cache_minutes": 30
  }
}
```

### 4.3 周报索引 `persistent/reports_index.json`

```jsonc
{
  "reports": [
    {
      "id": "2026-W41",
      "week_start": "2026-10-05", "week_end": "2026-10-11",
      "generated_at": "2026-10-11T20:00:00",
      "model": "qwen3.8-flash",
      "file": "weekly_report_output/weekly_report_2026-W41_20261011.md",
      "stats": { "total": 23, "done": 19, "rate": 0.83 }
    }
  ]
}
```

### 4.4 天气缓存 `persistent/weather_cache/YYYY-MM-DD_<城市>.json`

原始 API 响应 + `fetched_at` 时间戳；`cache_minutes` 内直接读缓存，避免消耗免费配额。

### 4.5 日记 `persistent/diary/<用户ID>/YYYY-MM-DD.json`（按用户+按天存储）

```jsonc
{
  "date": "2026-10-06",
  "entries": [
    { "id": "e1a2b3c4", "content": "今天完成了…", "created_at": "2026-10-06T21:00:00", "updated_at": "2026-10-06T21:00:00" }
  ],
  "updated": "2026-10-06T21:00:00"
}
```

---

## 5. 界面与功能设计

### 5.0 全局布局（MainLayout）

- 复刻 qyh 骨架：**顶部标题栏**（应用名"个人全能助手 · Personal Assistant"＋右侧设置按钮）＋ **左侧固定侧边栏** ＋ 中央工作区；
- 侧边栏导航项（图标 + 文字，可折叠为纯图标，`el-tooltip` 悬浮提示，激活项琥珀色高亮）：

| 导航项 | 图标（Element Plus / iconify） | 路由 |
|---|---|---|
| 主界面 | `Calendar` | `/` |
| 周报 | `Document` | `/report` |
| 天气 | `Cloudy`（iconify: `carbon:partly-cloudy-day`） | `/weather` |
| 智能助手 | `House` | `/butler`（占位页："敬请期待"，未来为 AI 助手对话界面） |
| 设置（底部） | `Setting` | 弹出 Dialog，不占路由 |

- 主题：暗色默认（`#0F172A` 底、`#1E293B` 面板、`#F59E0B` 强调），CSS 变量整体移植 qyh `modern-theme.css`，支持一键切换亮色。

### 5.1 主界面（日历视图）

**布局**：左侧月历网格（约 70%）＋ 右侧"当日详情"面板（约 30%）。

**月历网格（MonthGrid.vue）**：
- 标准 7×6 网格，`el-button-group`/自定义头部切换 上/下月、回到今天；
- 每个日期格内显示：公历日 + 农历日（`lunar-javascript` 前端离线计算，含节日/节气优先显示，如"中秋""立冬"）＋ 右上角状态圆点：**绿点=当天有任务**、绿点下方**橙点=当天有日记**（分别来自 `GET /api/tasks?start=&end=` 与 `GET /api/diary?start=&end=`）＋ 底部任务完成度进度条；
- 今天用琥珀色圆形底强调，选中日用高亮边框；
- 数据来源：打开月份时批量 `GET /api/tasks?start=..&end=..` 拉取该月任务统计。

**当日详情面板（DayDetail.vue）**，点击某天显示：
1. **日期区**：`2026年10月6日 星期二`、农历`丙午年八月廿五`、节日`（无）`、节气`（无，最近：寒露 10-08）`；
2. **天气区**：默认城市当天摘要（天气图标、温度区间、风力、AQI），点击跳转天气页；
3. **当日任务**：任务列表（checkbox 勾选完成、行内编辑、删除、优先级色条），底部快速添加输入框（回车即添加）；
4. **已完成任务**：折叠区展示当日 done 任务及完成时间。

**周任务批量编辑（WeekTaskEditor.vue）**：
- 入口：日历头部"编辑本周"按钮 / 详情面板"周编辑"按钮；
- 打开全屏 `el-drawer`：**周选择器**（`< 2026 第41周 (10.05–10.11) >`，可跳任意周，含"本周"快捷键）；
- 主体为 **7 列看板**（周一~周日），每列一个日期卡片，列内可添加/勾选/删除任务；
- 支持**跨天复制**：选中某任务 →"复制到…"勾选目标日期（应对每周重复任务）；
- 支持"重复任务"快捷项：如"每周一 例会"一键写入本周各列；
- 保存：逐日 `PUT /api/tasks/{date}`（携带 revision，冲突时提示刷新）。

### 5.2 周报界面（ReportView）

**布局**：顶部周选择 ＋ 左侧"本周数据汇总" ＋ 右侧"周报预览/编辑"。

**流程**：
1. 选择周（默认上周/本周可切换）→ `GET /api/reports/week-data?start=..` 返回该周 7 天任务与完成统计（总数、完成数、完成率、按天明细、未完成任务清单）；
2. 左侧展示统计卡片（完成率环形进度 `el-progress type=dashboard`、每日柱状 mini 图）供人工核对；
3. 点击 **"AI 生成周报"** → `POST /api/reports/generate`（SSE 流式返回）→ 后端聚合数据 + Prompt 模板（§7.3）调用 Qwen → token 流实时渲染到右侧 md-editor-v3；
4. 生成后可编辑微调 → 点击 **"保存"** → `POST /api/reports/save` 写入 `weekly_report_output/weekly_report_<ISO周>_<时间戳>.md`，并登记到 `reports_index.json`；
5. 历史周报下拉列表（读索引），可重新打开查看/再次生成覆盖。

**AI 设置入口**：本页右上角"AI 设置"按钮打开 `AiSettingsDialog`（也在全局设置中复用，对全系统所有 AI 场景生效）：
- Provider 下拉（DashScope-Qwen / DeepSeek / 智谱 / OpenAI / Ollama 本地）→ 自动填充 base_url；
- API Key（password 输入，保存后仅回显 `sk-****` 掩码）、temperature 滑杆；
- **模型下拉框（可随时切换）**：填好 Key 后点击"加载模型"，后端调用 `GET /api/ai/models` → 透传 DashScope 兼容端点 `GET {base_url}/models`，**动态拉取当前阿里云账号开通可用的全部模型**填充下拉（如 qwen3.8-flash / qwen3.8-max / qwen3.7-plus / qwen-flash / qwq-plus 等）；拉取失败时回退到内置常用模型清单，并支持手动输入模型名；默认选中 `qwen3.8-flash`；
- 全局生效：settings.json 只存一个 `ai.model`，周报、未来的管家助手等所有 AI 功能统一使用该模型，切换一次全局生效；
- **"测试连接"** 按钮：后端用该配置（含所选模型）发一条 `ping` 对话验证可用性；
- 保存 → `PUT /api/settings`（落盘 `persistent/settings.json`）。

### 5.3 天气界面（WeatherView）

**布局**（追求视觉美观，卡片化 + 渐变背景随天气变化）：
- **顶部**：`CityPicker`（`el-select` 多选 + 搜索，管理城市列表增删；每个已选城市一个页签/卡片，**支持多城市并列查看**）；
- **当前城市主卡片（TodayDetail）**：
  - 大号温度 + 天气现象图标 + 体感温度；
  - 详情网格（2×4 小卡）：**气压 hPa、紫外线指数（等级色）、风向风力（级 + km/h）、污染系数 AQI（等级色 + PM2.5/PM10/O₃ 分项）**、湿度、能见度、日出日落；
  - 卡片背景渐变色随天气现象/昼夜切换（晴=蓝橙渐变、雨=深灰蓝、雪=冷白等）；
- **未来 7 天（ForecastStrip）**：横向 7 张日卡（日期/星期、昼夜图标、高低温条、风力、AQI 色点），hover 抬升阴影；
- **数据链路**：前端 `GET /api/weather?city=北京&days=7` → 后端 weather.py：先查 `persistent/weather_cache/`（30 min 内命中直接返回）→ 未命中调 Provider API → 归一化为统一 schema → 写缓存 → 返回；
- 主界面当日详情的天气摘要复用同一接口（`days=1`）。

**天气 Provider 对比与选型**：

| Provider | 免费额度 | 字段覆盖 | 城市检索 | 结论 |
|---|---|---|---|---|
| **和风天气 QWeather** | 免费订阅 1000 次/天 | 实况(气压/紫外线/风/AQI 单独接口)+7 天预报+生活指数+城市 GeoAPI | 官方 GeoAPI，国内数据权威 | **主选**（✅ 已确认注册，见下方注册指引） |
| **Open-Meteo** | 非商用免费、**无需 Key**、无严格限次 | forecast API(气压/紫外线/风) + 独立 air-quality API(AQI/PM2.5) | 自带 geocoding API | **兜底**（零配置即可跑通，适合开发期） |
| UAPI(uapis.cn) | 免费无需注册 | 一个接口全含(extended/forecast/indices) | 中文城市名直查 | 备选，第三方聚合稳定性存疑 |

> 实现为 `WeatherProvider` 抽象基类 + 两个实现，settings 中一键切换；开发期先用 `open_meteo`（无需任何 Key 即可联调），拿到和风 Key 后切 `qweather`。

**和风天气注册指引（用户操作）**：
1. 打开官网 **https://dev.qweather.com** → 右上角「注册」，用手机号/邮箱注册并完成实名认证；
2. 登录后进入控制台 **https://console.qweather.com** → 「项目管理」→「创建项目」；
3. 订阅选择 **「免费订阅」**（1000 次/天，含实况、7 天预报、空气质量、GeoAPI，足够本系统使用），认证方式选 **API Key**；
4. 创建后在项目详情里复制 **API Key**，填入本系统「设置 → 天气」即可；
5. API Host：本项目已获取到免费订阅专属域名 **`k838m3jq58.re.qweatherapi.com`**（已填入 settings.weather.api_host），所有和风请求以 `https://{api_host}/...` 为基地址；**仍需补充控制台中的 API Key**（填入 settings.weather.api_key）。

---

## 6. 后端 API 设计

统一前缀 `/api`，异常处理沿用 vision_label 模式（ValueError→400 / FileNotFoundError→404 / ConflictError→409 / 校验失败→422 中文提示）。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/settings` | 读设置（api_key 掩码返回） |
| PUT | `/api/settings` | 写设置（Pydantic `SettingsBody` 校验） |
| POST | `/api/settings/test-ai` | 用给定 AI 配置（含所选模型）发测试对话，返回成功/错误信息 |
| GET | `/api/ai/models` | 透传 `{base_url}/models`，返回当前账号可用模型列表（供设置页模型下拉框；失败时返回内置兜底清单） |
| GET | `/api/tasks/{date}` | 单日任务（含 revision） |
| PUT | `/api/tasks/{date}` | 保存单日任务（`TasksBody{tasks, revision}`，乐观并发） |
| GET | `/api/tasks?start=&end=` | 区间任务统计（日历月视图/周数据用，返回每日 total/done） |
| GET | `/api/diary/{date}` | 单日日记 |
| PUT | `/api/diary/{date}` | 保存单日日记 |
| GET | `/api/diary?start=&end=` | 区间内有日记的日期→条数（月历橙色圆点） |
| GET | `/api/calendar/{date}` | 农历/节日/节气（后端计算，供当日详情面板；前端 lunar-javascript 已可算，此接口作为一致性兜底） |
| GET | `/api/weather?city=&days=` | 归一化天气（走缓存） |
| GET | `/api/weather/cities?keyword=` | 城市搜索（透传 Provider GeoAPI） |
| GET | `/api/reports/week-data?start=` | 周任务聚合数据（生成周报的原料 + 左侧统计） |
| POST | `/api/reports/generate` | **SSE 流式**生成周报（`text/event-stream`，逐 token 推送） |
| POST | `/api/reports/save` | 保存 md 到 weekly_report_output/ 并登记索引 |
| GET | `/api/reports` | 历史周报索引列表 |
| GET | `/api/reports/{id}` | 读取某份周报 md 原文 |

---

## 7. AI 框架与工具选型（重点论证）

### 7.1 结论先行

| 决策点 | 选择 | 理由 |
|---|---|---|
| 调用协议 | **OpenAI 兼容协议（/v1/chat/completions）** | 事实标准；DashScope(Qwen)、DeepSeek、智谱、Ollama、vLLM、LM Studio 全部支持，换供应商只改 base_url+key+model 三个值 |
| 客户端库 | **`openai` 官方 Python SDK（开源，Apache-2.0）** 或裸 `httpx` | 一行 `client = OpenAI(api_key=..., base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")` 即接通 Qwen；支持 `stream=True` 直接对接 FastAPI SSE |
| 编排框架 | **不引入 LangChain/LlamaIndex**（保持轻封装 `services/ai.py`） | 本项目 AI 场景是"结构化数据 → 单轮/少轮生成"，无 RAG、无多步 Agent 链；LangChain 抽象层重、依赖多、调试成本高。封装一个 ~150 行的 Provider 类足够，未来若做"个人管家 Agent"可平滑升级（见 7.4） |
| 默认模型 | **qwen3.8-flash**（DashScope，全局统一） | 用户指定。flash 档速度快、价格低，对周报总结这类结构化数据生成任务质量足够；全系统所有 AI 场景统一用一个模型，简化配置。若某次需要更高质量，可在设置下拉框临时切 qwen3.8-max / qwen3.7-plus |
| 模型下拉框 | **动态加载账号可用模型**：`GET {base_url}/models`（OpenAI 兼容标准端点，DashScope 支持） | 阿里云账号开通的模型随账号动态变化，写死清单会过时；动态拉取 + 内置兜底清单 + 允许手动输入，三层保障 |
| 流式输出 | SSE（FastAPI `StreamingResponse`） | 周报生成 10~30s，流式大幅改善体验；openai SDK stream 迭代器直接转发 |
| 本地离线方案 | **Ollama + Qwen3 开源权重** | Qwen 系列模型本身开源（Apache-2.0 / Qwen license），Ollama（MIT）本地跑 `qwen3:8b` 等，base_url=`http://localhost:11434/v1`，零 API 费用、数据不出本机 |

### 7.2 Provider 抽象（services/ai.py 设计）

```python
class LLMProvider:                      # 统一接口，settings.ai.provider 切换
    def chat(self, messages, **kw) -> str: ...
    def chat_stream(self, messages, **kw) -> Iterator[str]: ...

class OpenAICompatProvider(LLMProvider):  # 一个实现通吃所有 OpenAI 兼容端点
    # dashscope / deepseek / zhipu / openai / ollama / vllm 仅 base_url+key+model 不同
```

内置 Provider 预设表（前端下拉自动填 base_url）：

| provider | base_url | 推荐模型 | 开源情况 |
|---|---|---|---|
| dashscope | `https://dashscope.aliyuncs.com/compatible-mode/v1` | **qwen3.8-flash（默认）**；下拉动态加载账号全部可用模型 | SDK 开源；**Qwen 模型权重开源**（可在 Ollama 本地部署） |
| deepseek | `https://api.deepseek.com/v1` | deepseek-chat | 模型权重开源 |
| zhipu | `https://open.bigmodel.cn/api/paas/v4` | glm-4-flash（长期免费） | 部分开源 |
| openai | `https://api.openai.com/v1` | gpt-4o-mini | 闭源 |
| ollama | `http://localhost:11434/v1` | qwen3:8b / llama3.1 | Ollama 与模型均开源，完全本地 |

### 7.3 周报 Prompt 模板（report.py 内置，用户风格偏好注入）

```
[System]
你是一名资深的工作周报撰写助手。根据用户提供的一周任务数据，输出 Markdown 周报。
要求：1) 结构含【本周概览】【完成情况】【亮点与产出】【未完成与风险】【下周计划建议】；
2) 概览给出完成率与一句话总评；3) 语言{report_style}；4) 不得编造数据中不存在的事实。

[User]
周期：2026-10-05 ~ 2026-10-11（第41周）
统计：总任务 23，已完成 19，完成率 82.6%
按天明细：<JSON: 每日 tasks[{title, done, priority, done_at}]>
未完成任务：<清单>
```

生成结果前端可编辑，保存时才写文件——**AI 输出永远不直接落盘**，人工把关。

### 7.4 未来 AI 扩展路线（「智能助手」模块预留）

系统整体即「个人全能助手」，本期先落地日历/周报/天气三大功能；「智能助手」界面未来承载 AI 对话（统一走 §7.2 的 Provider 抽象与全局模型配置）：

| 阶段 | 能力 | 建议工具（开源） |
|---|---|---|
| 现在 | 周报总结（单轮生成 + SSE 流式） | openai SDK 轻封装 |
| 近期 | 任务智能拆解/日程建议（结构化输出） | Qwen function-calling / JSON mode + Pydantic 解析 |
| 中期 | 智能助手对话（查任务、查天气、记备忘） | **LangGraph**（MIT）或 **Qwen-Agent**（Apache-2.0，阿里官方、对 Qwen 工具调用优化最好）；工具即现有 /api 接口 |
| 远期 | 长期记忆/知识检索（历史周报问答） | ChromaDB 或 LanceDB（本地嵌入式向量库，Apache-2.0）+ DashScope text-embedding-v3（或本地 bge-m3） |
| 可选 | 桌面级 LLM 工具生态 | MCP（Model Context Protocol，Anthropic 开源）——把本系统 API 包成 MCP Server，可直接被 IDE/助手调用 |

### 7.5 前端 AI 相关开源组件

- **md-editor-v3**（MIT）：周报 Markdown 编辑 + 渲染，支持流式追加；
- **lunar-javascript**（MIT）：农历/节气/传统节日纯前端离线计算，零 API 依赖；
- **Element Plus**（MIT）：全部交互组件。

---

## 8. 本地运行 / 构建 / 打包方案（Windows）

> 环境约定：后端运行于 conda 环境 `personal_system`（`pip install -r requirements.txt`）；前端开发/构建需 Node 18+（默认装于 `C:\Program Files\nodejs`）。

### 8.1 开发态（一键 start.bat，或手动两终端）

`start.bat`（推荐）：自动按序 ① 激活 conda 环境并启动后端 `python app.py`（:8765）→ ② 启动前端热更新 `npm run dev`（:5173）→ ③ 打开浏览器。会弹出 PA-Backend / PA-Frontend 两个窗口，保持运行即可；改前端代码保存后自动热更新，改后端代码需在 PA-Backend 窗口重启。

手动等价命令：

```bat
:: 终端 1 —— 后端
cd /d E:\Data_center\PJ\PJ1_weekly_report
conda activate personal_system
python app.py            :: → http://localhost:8765 (API)

:: 终端 2 —— 前端热更新（Node 18+）
cd frontend
npm install
npm run dev              :: → http://localhost:5173，vite proxy /api → 8765
```

### 8.2 生产态（单进程单端口，build.bat 编译前端）

```bat
build.bat        :: 等价 cd frontend && npm run build，产物输出到 ../web/
python app.py    :: 浏览器打开 http://localhost:8765（FastAPI 托管 web/，单端口）
```

改了前端代码且想用 8765 单端口访问时跑一次 `build.bat`；编译后无需重启后端（静态文件 no-cache），刷新浏览器即可。开发态 5173 有热更新，无需编译。

### 8.3 图形启动器（无 cmd 黑窗口，打包成 exe）

- `launcher.py`：tkinter 小窗口，仅【启动】/【停止】两个按钮；以隐藏进程方式（`CREATE_NO_WINDOW`）拉起后端（conda: personal_system）与前端（`npm run dev`），停止/关窗时用 `taskkill /F /T` 结束整个进程树；子进程输出写入 `launcher_backend.log` / `launcher_frontend.log` 便于排错。
- `build_launcher.bat`：用 PyInstaller（`--noconsole --onefile`）把 `launcher.py` 打包为项目根目录的 `个人全能助手.exe`（首次自动安装 PyInstaller）。
- 使用：双击 exe → 点【启动】，自动开浏览器。exe 属「轻量启动器」，运行时仍依赖本机 conda 环境与 Node，故必须放在项目根目录（与 `app.py` 同级）。

### 8.4 上传 GitHub（.gitignore 约定）

仅提交源码与配置；以下由 `.gitignore` 忽略：

- **构建产物**：`web/`、`frontend/node_modules/`、`__pycache__/`、PyInstaller 产物（`dist/`、`build_tmp/`、`*.spec`、`个人全能助手.exe`）；
- **运行时/敏感数据**：`persistent/`（含 api_key、账户凭据、会话令牌）、`weekly_report_output/`、`launcher_*.log`；
- **保留提交**：`frontend/package-lock.json`（锁定依赖版本）。

---

## 9. 风险与对策

| 风险 | 对策 |
|---|---|
| API Key 明文存 `settings.json` | 本机个人工具可接受；文件加入 `.gitignore`，前端回显永远掩码；可选支持环境变量 `DASHSCOPE_API_KEY` 覆盖 |
| 天气免费配额耗尽 | 30min 缓存 + 当日详情/周报表复用同一缓存；Open-Meteo 兜底无限量 |
| AI 生成质量不稳/超时 | SSE 流式可见进度；失败保留已生成部分；Prompt 中强约束"不得编造"；生成后可编辑再保存 |
| 多标签页并发编辑任务冲突 | 沿用 vision_label revision 乐观锁：409 时提示"数据已被其他窗口更新，请刷新后重试" |
| 农历/节气计算精度 | lunar-javascript 覆盖 1900–2100 年，节气精确到日，满足展示需求 |
| 前端缓存导致新旧接口不兼容 | 沿用 vision_label no-cache 中间件 |

---

## 10. 开发里程碑

| 阶段 | 内容 | 交付物 |
|---|---|---|
| M1 骨架 | app.py + backend/store.py + frontend 脚手架 + MainLayout 侧边栏/主题 | 可打开的空壳四页面 |
| M2 日历与任务 | MonthGrid + DayDetail + 任务 CRUD + 按天 JSON 持久化 + revision | 主界面可用 |
| M3 周编辑 | WeekTaskEditor（周选择、7 列看板、跨天复制） | 批量编辑可用 |
| M4 天气 | weather.py 双 Provider + 缓存 + WeatherView + 主界面天气摘要 | 天气页可用 |
| M5 AI 周报 | ai.py + report.py + SSE 流式 + AiSettingsDialog + md 保存/索引 | 周报端到端跑通 |
| M6 打磨 | 农历/节日/节气接入、亮暗主题、start.bat、构建发布到 web/ | v1.0 |

---

## 附：用户反馈落实情况（v0.3 修订记录）

| # | 反馈 | 落实 |
|---|---|---|
| 1 | 系统名改为「个人全能助手」 | 已全局更名（标题/顶栏/概述/路由）；原「个人管家」导航项相应改为「智能助手」，避免与系统名重复 |
| 2 | 和风天气 Host：k838m3jq58.re.qweatherapi.com | 已填入 settings.weather.api_host；❗此值为专属 **API Host**（非 API Key），**API Key 仍需补充** |
| — | （历史）周一起始 / qwen3.8-flash / 模型下拉框 | 均已在 v0.2 落实，本版保留 |

仍待确认（不阻塞开发）：
1. **和风天气 API Key**：你提供的 `k838m3jq58.re.qweatherapi.com` 是 Host，请到控制台项目详情里复制 **API Key**（另一串字符）告诉我；未提供前天气功能先走 Open-Meteo 兜底。
2. 周报文件命名 `weekly_report_2026-W41_<时间戳>.md` 是否可接受？
