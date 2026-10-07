@echo off
chcp 65001 >nul
REM ============================================================
REM  后端环境安装：创建 conda 环境 personal_system + 安装 Python 依赖
REM  双击运行即可。需要已安装 Anaconda/Miniconda。
REM ============================================================
setlocal
set ENV_NAME=personal_system
set PY_VER=3.11
cd /d "%~dp0.."

echo ============================================
echo   [1/2] 创建 conda 环境: %ENV_NAME% (python=%PY_VER%)
echo ============================================
call conda env list | findstr /R "^%ENV_NAME% " >nul
if %errorlevel%==0 (
    echo 环境 %ENV_NAME% 已存在，跳过创建。
) else (
    call conda create -n %ENV_NAME% python=%PY_VER% -y
    if errorlevel 1 ( echo [ERR] conda 环境创建失败 & pause & exit /b 1 )
)

echo.
echo ============================================
echo   [2/2] 安装 Python 依赖 (requirements.txt)
echo ============================================
call conda run -n %ENV_NAME% python -m pip install --upgrade pip
call conda run -n %ENV_NAME% python -m pip install -r requirements.txt
if errorlevel 1 ( echo [ERR] 依赖安装失败 & pause & exit /b 1 )

echo.
echo [OK] 后端环境就绪。
echo      启动后端： conda activate %ENV_NAME% ^&^& python app.py
echo      然后浏览器打开 http://localhost:8765
pause
endlocal
