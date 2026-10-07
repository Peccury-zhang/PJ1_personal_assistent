"""个人全能助手 —— 图形启动器（无 cmd 黑窗口版）

【启动】/【停止】/【编译】三个按钮：
  启动 -> 隐藏方式拉起 后端(conda: personal_system, python app.py, :8765)
                     + 前端(npm run dev, :5173)，随后自动打开浏览器
  停止 -> 结束上述两个进程树
  编译 -> 前端 npm run build（产物 -> web/）+ 后端 python -m compileall 字节码校验

对应 start.bat / build.bat 的等价逻辑，但不弹任何命令行窗口；子进程输出重定向到
launcher_backend.log / launcher_frontend.log / launcher_build.log 便于排查问题（统一存放于 log/ 目录）。

打包成 exe：见 build_launcher.bat（PyInstaller --noconsole --onefile）。
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import messagebox

# ---------------------------------------------------------------- 路径与常量
# 打包成 exe 后 __file__ 指向临时解包目录，须用 sys.executable 定位真实目录
if getattr(sys, 'frozen', False):
    ROOT = Path(sys.executable).resolve().parent
else:
    ROOT = Path(__file__).resolve().parent

CONDA_ENV = 'personal_system'
NODE_DIR = r'C:\PROGRA~1\nodejs'          # = C:\Program Files\nodejs
BACKEND_URL = 'http://localhost:8765'
FRONTEND_URL = 'http://localhost:5173'

CREATE_NO_WINDOW = 0x08000000             # 让子进程不创建控制台窗口

LOG_DIR = ROOT / 'log'
LOG_DIR.mkdir(parents=True, exist_ok=True)

BACKEND_LOG = LOG_DIR / 'launcher_backend.log'
FRONTEND_LOG = LOG_DIR / 'launcher_frontend.log'
BUILD_LOG = LOG_DIR / 'launcher_build.log'


def _backend_cmd() -> str:
    # 与 start.bat 一致：在 cmd 里激活 conda 环境后跑后端
    return f'call conda activate {CONDA_ENV} && python app.py'


def _frontend_cmd() -> str:
    # 与 start.bat 一致：把 nodejs 加入 PATH 后进入 frontend 跑 npm run dev
    return f'set "PATH={NODE_DIR};%PATH%" && cd frontend && npm run dev'


def _frontend_build_cmd() -> str:
    # 与 build.bat 一致：进入 frontend 跑 npm run build，产物输出到 ../web
    return f'chcp 65001 >nul && set "PATH={NODE_DIR};%PATH%" && cd frontend && npm run build'


def _backend_compile_cmd() -> str:
    # 后端是 Python(FastAPI)，无传统编译；用 compileall 生成 .pyc 并做语法校验，
    # 若有语法错误则返回非 0 退出码。
    return f'chcp 65001 >nul && call conda activate {CONDA_ENV} && python -m compileall backend app.py'


def _spawn(cmd: str, log_path: Path) -> subprocess.Popen:
    """以隐藏窗口方式启动一个 cmd 子进程，输出追加写入日志文件。"""
    log = open(log_path, 'ab', buffering=0)
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        shell=True,                       # Windows 下等价于 cmd /c "<cmd>"
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
    )


def _run_logged(cmd: str, log) -> int:
    """同步（阻塞）执行 cmd，输出写入已打开的日志文件对象，返回退出码。"""
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
    ).returncode


def _blog(log, text: str) -> None:
    """向日志文件对象写入一段 UTF-8 文本（分隔标题 / 结果标记）。"""
    log.write(text.encode('utf-8', 'replace'))


def _kill_tree(proc: subprocess.Popen | None) -> None:
    """结束进程及其所有子进程（python/node 等）。"""
    if proc is None or proc.poll() is not None:
        return
    subprocess.run(
        f'taskkill /F /T /PID {proc.pid}',
        shell=True,
        creationflags=CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ---------------------------------------------------------------- GUI
class LauncherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.backend: subprocess.Popen | None = None
        self.frontend: subprocess.Popen | None = None
        self.running = False
        self.building = False

        root.title('个人全能助手')
        root.resizable(False, False)
        root.configure(bg='#f5f6f8')

        # 居中显示
        w, h = 480, 260
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f'{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}')

        tk.Label(root, text='个人全能助手', font=('Microsoft YaHei', 16, 'bold'),
                 bg='#f5f6f8', fg='#222').pack(pady=(20, 4))
        tk.Label(root, text=f'后端 {BACKEND_URL}    前端 {FRONTEND_URL}',
                 font=('Microsoft YaHei', 9), bg='#f5f6f8', fg='#888').pack()

        self.status = tk.Label(root, text='● 已停止', font=('Microsoft YaHei', 11),
                               bg='#f5f6f8', fg='#c0392b')
        self.status.pack(pady=(12, 8))

        btns = tk.Frame(root, bg='#f5f6f8')
        btns.pack()
        self.btn_start = tk.Button(btns, text='启动', width=9, height=2,
                                   font=('Microsoft YaHei', 11, 'bold'),
                                   bg='#27ae60', fg='white', activebackground='#2ecc71',
                                   relief='flat', cursor='hand2', command=self.on_start)
        self.btn_start.grid(row=0, column=0, padx=9)
        self.btn_stop = tk.Button(btns, text='停止', width=9, height=2,
                                  font=('Microsoft YaHei', 11, 'bold'),
                                  bg='#c0392b', fg='white', activebackground='#e74c3c',
                                  relief='flat', cursor='hand2', state='disabled',
                                  command=self.on_stop)
        self.btn_stop.grid(row=0, column=1, padx=9)
        self.btn_build = tk.Button(btns, text='编译', width=9, height=2,
                                   font=('Microsoft YaHei', 11, 'bold'),
                                   bg='#2980b9', fg='white', activebackground='#3498db',
                                   relief='flat', cursor='hand2', command=self.on_build)
        self.btn_build.grid(row=0, column=2, padx=9)

        self.build_status = tk.Label(root, text='编译：待命', font=('Microsoft YaHei', 9),
                                     bg='#f5f6f8', fg='#888')
        self.build_status.pack(pady=(12, 0))

        root.protocol('WM_DELETE_WINDOW', self.on_close)

    # ---- 状态刷新（必须在主线程调用，用 root.after 转投）----
    def _set_status(self, text: str, color: str) -> None:
        self.status.config(text=text, fg=color)

    def on_start(self) -> None:
        if self.running:
            return
        if not (ROOT / 'app.py').exists():
            messagebox.showerror('找不到程序', f'未在以下目录找到 app.py：\n{ROOT}\n请把本程序放在项目根目录。')
            return
        self.running = True
        self.btn_start.config(state='disabled')
        self.btn_stop.config(state='normal')
        self._set_status('● 启动中…', '#e67e22')
        threading.Thread(target=self._do_start, daemon=True).start()

    def _do_start(self) -> None:
        try:
            # 清空旧日志
            for p in (BACKEND_LOG, FRONTEND_LOG):
                try:
                    p.write_text('', encoding='utf-8')
                except Exception:
                    pass
            self.backend = _spawn(_backend_cmd(), BACKEND_LOG)
            time.sleep(4)                       # 等待后端就绪（同 start.bat）
            self.frontend = _spawn(_frontend_cmd(), FRONTEND_LOG)
            time.sleep(3)                       # 等待前端就绪
            webbrowser.open(FRONTEND_URL)
            self.root.after(0, lambda: self._set_status('● 运行中', '#27ae60'))
        except Exception as e:                  # noqa: BLE001
            self.root.after(0, lambda: self._set_status('● 启动失败', '#c0392b'))
            self.root.after(0, lambda: messagebox.showerror('启动失败', str(e)))

    def on_stop(self) -> None:
        if not self.running:
            return
        self._set_status('● 停止中…', '#e67e22')
        self.btn_stop.config(state='disabled')
        threading.Thread(target=self._do_stop, daemon=True).start()

    def _do_stop(self) -> None:
        _kill_tree(self.frontend)
        _kill_tree(self.backend)
        self.frontend = None
        self.backend = None
        self.running = False
        self.root.after(0, lambda: self._set_status('● 已停止', '#c0392b'))
        self.root.after(0, lambda: self.btn_start.config(state='normal'))

    # ---- 编译：前端 npm run build + 后端 compileall 字节码校验 ----
    def _set_build_status(self, text: str, color: str) -> None:
        self.build_status.config(text=text, fg=color)

    def on_build(self) -> None:
        if self.building:
            return
        if not (ROOT / 'app.py').exists():
            messagebox.showerror('找不到程序', f'未在以下目录找到 app.py：\n{ROOT}\n请把本程序放在项目根目录。')
            return
        self.building = True
        self.btn_build.config(state='disabled')
        self._set_build_status('编译中…', '#e67e22')
        threading.Thread(target=self._do_build, daemon=True).start()

    def _do_build(self) -> None:
        fe_ok = be_ok = False
        try:
            with open(BUILD_LOG, 'wb', buffering=0) as log:
                _blog(log, '==== [1/2] 前端编译：npm run build -> web/ ====\n')
                self.root.after(0, lambda: self._set_build_status('编译中：前端 npm run build…', '#e67e22'))
                fe_ok = _run_logged(_frontend_build_cmd(), log) == 0
                fe_text = '成功 -> web/' if fe_ok else '失败'
                _blog(log, f'\n[前端编译{fe_text}]\n')

                _blog(log, '\n==== [2/2] 后端字节码校验：python -m compileall ====\n')
                self.root.after(0, lambda: self._set_build_status('编译中：后端 compileall…', '#e67e22'))
                be_ok = _run_logged(_backend_compile_cmd(), log) == 0
                be_text = '成功' if be_ok else '失败'
                _blog(log, f'\n[后端字节码校验{be_text}]\n')
        except Exception as e:                  # noqa: BLE001
            self.root.after(0, lambda: messagebox.showerror('编译异常', str(e)))

        if fe_ok and be_ok:
            self.root.after(0, lambda: self._set_build_status('编译成功 ✓（web/ 已更新）', '#27ae60'))
        else:
            self.root.after(0, lambda: self._set_build_status('编译失败 ✗（详见 launcher_build.log）', '#c0392b'))
            self.root.after(0, lambda: messagebox.showerror(
                '编译失败', f'编译未通过，请查看日志：\n{BUILD_LOG}'))
        self.root.after(0, self._build_finished)

    def _build_finished(self) -> None:
        self.building = False
        self.btn_build.config(state='normal')

    def on_close(self) -> None:
        # 关闭窗口时若仍在运行，先结束子进程，避免残留 node/python
        if self.running:
            _kill_tree(self.frontend)
            _kill_tree(self.backend)
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
