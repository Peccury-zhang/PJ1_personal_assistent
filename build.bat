@echo off
chcp 65001 >nul
REM ============================================================
REM  编译前端 -> web/（生产单端口模式）
REM  何时需要跑：改了前端代码且想用 http://localhost:8765 单端口访问时。
REM  编译完成后无需重启后端（静态文件 no-cache），刷新浏览器即可。
REM  开发模式下（start.bat 的 5173）有热更新，不需要跑本脚本。
REM ============================================================
cd /d "%~dp0frontend"
set PATH=C:\PROGRA~1\nodejs;%PATH%

echo ============================================
echo   编译前端 -^> ..\web
echo ============================================
call npm run build
if errorlevel 1 (
    echo.
    echo 编译失败，请检查上方报错。
    pause
    exit /b 1
)

echo.
echo 编译成功 -^> ..\web
echo 现在只需运行后端（python app.py 或 start.bat），打开 http://localhost:8765 即可。
pause
