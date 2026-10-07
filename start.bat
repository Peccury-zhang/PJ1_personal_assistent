@echo off
chcp 65001 >nul
REM ============================================================
REM  一键启动「个人全能助手」（开发模式）
REM  顺序：激活 conda 环境 -> 启动后端(8765) -> 启动前端开发服务器(5173)
REM  前端开发服务器带热更新：改前端代码保存后自动刷新，无需编译。
REM  改后端 Python 代码：需在 PA-Backend 窗口重启（Ctrl+C 后重跑 start.bat）。
REM ============================================================
cd /d "%~dp0"

echo ============================================
echo   启动 个人全能助手（开发模式）
echo   后端 API   http://localhost:8765
echo   前端界面   http://localhost:5173   ^<-- 浏览器打开这个
echo ============================================

REM --- 1) 启动后端（独立窗口，窗口内自行激活 conda） ---
start "PA-Backend" cmd /k "call conda activate personal_system && python app.py"

REM --- 等待后端就绪 ---
echo 等待后端启动...
timeout /t 4 /nobreak >nul

REM --- 2) 启动前端开发服务器（独立窗口） ---
start "PA-Frontend" cmd /k "set PATH=C:\PROGRA~1\nodejs;%%PATH%% && cd frontend && npm run dev"

timeout /t 3 /nobreak >nul

REM --- 3) 打开浏览器 ---
start "" http://localhost:5173

echo.
echo 已启动。请保持弹出的 PA-Backend / PA-Frontend 两个窗口运行，关闭即停止服务。
echo 本窗口可以关闭。
timeout /t 5 /nobreak >nul
exit
