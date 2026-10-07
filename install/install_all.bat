@echo off
chcp 65001 >nul
REM ============================================================
REM  一键安装（按顺序）：
REM    1) Node.js   2) 后端 conda 环境   3) 前端构建
REM  注意：Node.js 安装后需要【重开终端】PATH 才生效，
REM        因此本脚本会在装完 Node 后提示你手动继续。
REM ============================================================
echo ============================================
echo   个人全能助手 —— 一键安装
echo ============================================
echo.
echo [步骤 1] 安装 Node.js ...
call "%~dp0install_nodejs.bat"
echo.
echo [步骤 2] 创建后端 conda 环境 ...
call "%~dp0setup_backend.bat"
echo.
echo [步骤 3] 构建前端 ...
echo   若刚安装 Node.js，请【关闭本窗口并重开】后再单独运行 setup_frontend.bat
call "%~dp0setup_frontend.bat"
echo.
echo ============================================
echo   全部完成！运行 start.bat 启动系统。
echo ============================================
pause
