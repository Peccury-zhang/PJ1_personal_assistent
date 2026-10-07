# 个人全能助手 —— 安装与运行说明

本系统在本地 Windows 运行，浏览器操作。需要两样运行环境：

| 环境 | 用途 | 是否必须 |
|---|---|---|
| **Conda（Python 3.11）** | 运行后端 FastAPI 服务 | ✅ 必须（你已装 Anaconda） |
| **Node.js（LTS，含 npm）** | 构建前端 Vue3 工程 | ✅ 必须（首次需安装） |

> 目录 `install/` 内所有脚本均可**双击运行**。

---

## 一、最省事：一键安装

双击 **`install/install_all.bat`**，它会依次执行：
1. 安装 Node.js（`install_nodejs.bat`）
2. 创建 conda 环境 `personal_system` 并装 Python 依赖（`setup_backend.bat`）
3. 构建前端（`setup_frontend.bat`）

⚠️ **重要**：Node.js 安装后，PATH 需要**重开终端**才生效。如果这是你第一次装 Node.js，一键脚本跑到第 3 步可能提示“未检测到 node”。此时：
> **关闭所有终端窗口 → 重新打开 → 再双击一次 `install/setup_frontend.bat`** 即可。

装完后，双击项目根目录的 **`start.bat`** 启动系统，浏览器自动打开 http://localhost:8765 。

---

## 二、分步安装（推荐，便于排查）

### 步骤 1：安装 Node.js
双击 **`install/install_nodejs.bat`**。
- 脚本优先用 Windows 自带的 `winget` 安装 Node.js LTS；
- 若无 winget，则自动从官网 `https://nodejs.org/dist/` 下载 MSI 安装包并静默安装（会弹 UAC 授权，点“是”）；
- 安装完成后 **务必关闭并重开终端**，验证：
  ```bat
  node -v
  npm -v
  ```
  两条都能打印版本号即成功。

> 手动安装也可以：到 https://nodejs.org 下载 **LTS** 版 Windows Installer (.msi)，一路下一步。

### 步骤 2：创建后端 conda 环境
双击 **`install/setup_backend.bat`**，它会：
- 创建名为 **`personal_system`** 的 conda 环境（Python 3.11）；
- 依据根目录 `requirements.txt` 安装 `fastapi / uvicorn / pydantic / httpx`。

等价的手动命令：
```bat
conda create -n personal_system python=3.11 -y
conda activate personal_system
pip install -r requirements.txt
```

### 步骤 3：构建前端
双击 **`install/setup_frontend.bat`**，它会进入 `frontend/` 执行：
```bat
npm install
npm run build      REM 产物输出到 ../web
```

---

## 三、运行系统

### 方式 A：一键启动（生产模式，推荐日常使用）
双击根目录 **`start.bat`** → 浏览器打开 http://localhost:8765 。
（内部：激活 `personal_system` 环境 → `python app.py` → 自动开浏览器）

手动等价命令：
```bat
conda activate personal_system
python app.py
```

### 方式 B：开发模式（改前端代码时热更新）
需要**两个终端**：
```bat
:: 终端 1 —— 后端
conda activate personal_system
python app.py                      :: http://localhost:8765

:: 终端 2 —— 前端热更新
cd frontend
npm run dev                        :: http://localhost:5173（已代理 /api 到 8765）
```
开发时访问 **http://localhost:5173**，改代码即时刷新。

---

## 四、脚本清单

| 文件 | 作用 |
|---|---|
| `install/install_all.bat` | 一键：Node.js + 后端环境 + 前端构建 |
| `install/install_nodejs.bat` | 安装 Node.js（调用同目录 .ps1） |
| `install/install_nodejs.ps1` | Node.js 实际下载/安装逻辑（winget 优先，MSI 兜底） |
| `install/setup_backend.bat` | 创建 conda 环境 `personal_system` + 装 Python 依赖 |
| `install/setup_frontend.bat` | `npm install` + `npm run build` |
| `start.bat`（根目录） | 一键启动系统并打开浏览器 |
| `requirements.txt`（根目录） | 后端 Python 依赖清单 |

---

## 五、首次运行后的配置

启动后打开浏览器 → 右上角「设置」：
1. **AI（周报生成用）**：
   - Provider 选 `阿里云百炼 (Qwen)`；
   - 填入你的 DashScope **API Key**；
   - 点「加载模型」拉取账号可用模型，默认 `qwen3.8-flash`；
   - 点「测试连接」确认可用。
2. **天气**：
   - Provider 默认 `open_meteo`（无需 Key，开箱即用）；
   - 若要切换到和风天气：Provider 选 `qweather`，API Host 已预填 `k838m3jq58.re.qweatherapi.com`，再补上你的和风 **API Key** 即可。

所有配置保存在 `persistent/settings.json`。

---

## 六、常见问题（FAQ）

**Q1：`node -v` 提示“不是内部或外部命令”？**
A：Node.js 装完没重开终端，PATH 未刷新。关闭所有终端窗口重新打开即可；仍不行则手动到 https://nodejs.org 下载安装。

**Q2：`conda` 命令找不到？**
A：请用「Anaconda Prompt」运行脚本，或把 Anaconda 加入系统 PATH。

**Q3：端口 8765 被占用（`[WinError 10048]`）？**
A：已有一个后端在跑。关闭旧窗口，或改 `app.py` 里的 `PORT`。

**Q4：`npm install` 很慢或失败？**
A：换国内镜像后重试：
```bat
npm config set registry https://registry.npmmirror.com
```

**Q5：打开 http://localhost:8765 只显示一段 JSON 提示“前端尚未构建”？**
A：说明 `web/` 里还没有构建产物，执行 `install/setup_frontend.bat` 生成即可。

---

## 七、卸载 / 清理

- 删除 conda 环境：`conda env remove -n personal_system`
- Node.js：控制面板「程序和功能」卸载，或 `winget uninstall OpenJS.NodeJS.LTS`
- 用户数据都在 `persistent/`，删除前请先备份。
