@echo off
chcp 65001 >nul
REM ============================================================
REM  把 launcher.py 打包成图形化 exe（无 cmd 黑窗口，只有启动/停止按钮）
REM  产物：项目根目录下的「个人全能助手.exe」
REM  依赖：conda 环境 personal_system 内的 PyInstaller（脚本会自动安装）
REM  说明：exe 只是启动器，运行时仍调用本机的 conda 环境与 Node，
REM        所以 exe 必须放在项目根目录（与 app.py 同级）双击运行。
REM ============================================================
cd /d "%~dp0"

echo ============================================
echo   打包图形启动器 -^> 个人全能助手.exe
echo ============================================

REM --- 1) 激活 conda 环境 ---
call conda activate personal_system
if errorlevel 1 (
    echo [错误] 无法激活 conda 环境 personal_system，请确认环境存在。
    pause
    exit /b 1
)

REM --- 2) 确保 PyInstaller 已安装 ---
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo 未检测到 PyInstaller，正在安装...
    python -m pip install -q --disable-pip-version-check pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败。
        pause
        exit /b 1
    )
)

REM --- 3) 打包（--noconsole 无黑窗口，--onefile 单文件）---
python -m PyInstaller --noconsole --onefile --clean ^
    --name "个人全能助手" ^
    --distpath "dist" ^
    --workpath "build_tmp" ^
    --specpath "build_tmp" ^
    launcher.py
if errorlevel 1 (
    echo [错误] 打包失败，请检查上方报错。
    pause
    exit /b 1
)

REM --- 4) 把 exe 移动到项目根目录（与 app.py 同级才能正常启动）---
if exist "个人全能助手.exe" del /f /q "个人全能助手.exe"
move /y "dist\个人全能助手.exe" "个人全能助手.exe" >nul
if errorlevel 1 (
    echo.
    echo [错误] 无法替换「个人全能助手.exe」——它很可能正在运行，文件被占用。
    echo        请先关闭正在运行的助手窗口（或任务管理器结束进程），再重新双击本脚本。
    echo        本次构建的新 exe 已保留在 dist\个人全能助手.exe，未被删除。
    pause
    exit /b 1
)

REM --- 5) 清理临时文件（仅在替换成功后执行）---
if exist "dist" rmdir /s /q "dist"
if exist "build_tmp" rmdir /s /q "build_tmp"

echo.
echo ============================================
echo   打包成功：个人全能助手.exe
echo   双击运行，点【启动】即可，无需再看 cmd 窗口。
echo ============================================
pause
