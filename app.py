"""入口：python app.py  →  http://localhost:8765

架构参照 E:\\Data_center\\yc2_robot\\vision_label\\app.py：
FastAPI 单体 + 统一异常处理 + 静态前端托管 + no-cache 中间件。
前端为 Vite 构建产物（web/）；开发态前端跑在 Vite dev server 并代理 /api。
"""
from __future__ import annotations

import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Windows 控制台默认用 GBK，直接 print 中文会变乱码；强制 stdout/stderr 用 UTF-8。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.api import router  # noqa: E402
from backend.store import ConflictError, _ensure_dirs, migrate_legacy_to_user  # noqa: E402
from backend import users as users_mod  # noqa: E402

HOST = '127.0.0.1'
PORT = 8765

# 无需登录即可访问的接口
AUTH_WHITELIST = {'/api/health', '/api/auth/login'}


def create_app() -> FastAPI:
    app = FastAPI(title='个人全能助手', version='0.4')
    _ensure_dirs()
    users_mod.ensure_seed()
    # 多用户隔离：把引入账户体系之前的旧任务/周报归属到首个账户
    _seed = users_mod.list_users()
    if _seed:
        migrate_legacy_to_user(_seed[0]['id'])

    @app.exception_handler(ConflictError)
    async def conflict(request, exc):
        return JSONResponse(status_code=409, content={'detail': str(exc)})

    @app.exception_handler(FileNotFoundError)
    async def missing(request, exc):
        return JSONResponse(status_code=404, content={'detail': str(exc)})

    @app.exception_handler(RequestValidationError)
    async def validation_err(request, exc):
        # exc.errors() 的 input/ctx 可能含 bytes 等不可序列化对象，只保留安全字段
        errs = [{'loc': list(e.get('loc', [])), 'msg': e.get('msg'), 'type': e.get('type')}
                for e in exc.errors()]
        return JSONResponse(status_code=422, content={'detail': errs})

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse(status_code=400, content={'detail': str(exc)})

    app.include_router(router)

    @app.get('/api/health')
    def health():
        return {'ok': True, 'app': '个人全能助手'}

    # 托管前端构建产物（存在时）；开发态无 web/ 则给出提示页
    web_dir = ROOT / 'web'
    if web_dir.exists() and (web_dir / 'index.html').exists():
        app.mount('/', StaticFiles(directory=str(web_dir), html=True), name='web')
    else:
        @app.get('/')
        def index_placeholder():
            return JSONResponse(content={
                'detail': '前端尚未构建。开发态请访问 Vite dev server（默认 http://localhost:5173），'
                          '或执行 cd frontend && npm install && npm run build 后再打开本地址。',
                'api_docs': '/docs',
            })

    @app.middleware('http')
    async def auth_guard(request, call_next):
        path = request.url.path
        if path.startswith('/api/') and path not in AUTH_WHITELIST:
            token = (request.headers.get('authorization') or '').removeprefix('Bearer ').strip()
            if not users_mod.get_session_user(token):
                return JSONResponse(status_code=401, content={'detail': '未登录或登录已过期'})
        return await call_next(request)

    @app.middleware('http')
    async def no_cache(request, call_next):
        r = await call_next(request)
        path = request.url.path
        if path == '/' or path.split('/')[-1].endswith(('.js', '.css', '.html')):
            r.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return r

    return app


if __name__ == '__main__':
    print('=' * 56)
    print('  个人全能助手  |  python app.py')
    print(f'  →  http://localhost:{PORT}')
    print(f'  API 文档  →  http://localhost:{PORT}/docs')
    print('=' * 56)
    uvicorn.run(create_app(), host=HOST, port=PORT, log_level='info')
