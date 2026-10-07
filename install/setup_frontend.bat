@echo off
chcp 65001 >nul
REM ============================================================
REM  前端构建：npm install + npm run build（产物输出到 ../web）
REM  运行前请先执行 install_nodejs.bat 安装 Node.js，并重开终端。
REM ============================================================
setlocal
cd /d "%~dp0..\frontend"

where node >nul 2>nul
if errorlevel 1 (
    echo [ERR] 未检测到 node。请先运行 install\install_nodejs.bat，
    echo        安装完成后【关闭并重开终端】再运行本脚本。
    pause & exit /b 1
)

echo ============================================
echo   [1/2] npm install
echo ============================================
call npm install
if errorlevel 1 ( echo [ERR] npm install 失败 & pause & exit /b 1 )

echo.
echo ============================================
echo   [2/2] npm run build  (输出到 ../web)
echo ============================================
call npm run build
if errorlevel 1 ( echo [ERR] 构建失败 & pause & exit /b 1 )

echo.
echo [OK] 前端构建完成。启动后端后浏览器打开 http://localhost:8765
pause
endlocal
