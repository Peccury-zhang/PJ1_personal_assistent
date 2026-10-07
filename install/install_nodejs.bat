@echo off
chcp 65001 >nul
REM 双击本文件即可安装 Node.js（内部调用 install_nodejs.ps1）
echo ============================================
echo   Node.js 安装器
echo ============================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_nodejs.ps1"
echo.
pause
