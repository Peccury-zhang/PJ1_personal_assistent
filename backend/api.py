"""REST API：/api/* 路由 + Pydantic 校验。

异常统一处理在 app.py：ValueError->400 / FileNotFoundError->404 / ConflictError->409 / 校验失败->422。
"""
from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import store, users
from .services import ai, report, weather

router = APIRouter(prefix='/api')


# ---------------------------------------------------------------- 鉴权依赖
def _bearer_token(request: Request) -> str:
    return (request.headers.get('authorization') or '').removeprefix('Bearer ').strip()


def current_user(request: Request) -> dict:
    user = users.get_session_user(_bearer_token(request))
    if not user:
        raise HTTPException(status_code=401, detail='未登录或登录已过期')
    return user


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user['level'] != 'admin':
        raise HTTPException(status_code=403, detail='需要管理员权限')
    return user


# ---------------------------------------------------------------- auth
class LoginBody(BaseModel):
    username: str
    password: str


@router.post('/auth/login')
def login(body: LoginBody):
    user = users.authenticate(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail='用户名或密码错误')
    token = users.create_session(user)
    return {'token': token, 'user': users._public(user)}


@router.post('/auth/logout')
def logout(request: Request, user: dict = Depends(current_user)):
    users.destroy_session(_bearer_token(request))
    return {'ok': True}


@router.get('/auth/me')
def me(user: dict = Depends(current_user)):
    return users._public(user)


# ---------------------------------------------------------------- users（仅管理员）
class UserCreateBody(BaseModel):
    username: str
    password: str
    level: str = 'user'


class UserUpdateBody(BaseModel):
    username: str | None = None
    password: str | None = None
    level: str | None = None


@router.get('/users')
def list_users(admin: dict = Depends(require_admin)):
    return {'users': users.list_users()}


@router.post('/users')
def create_user(body: UserCreateBody, admin: dict = Depends(require_admin)):
    return users.create_user(body.username, body.password, body.level)


@router.put('/users/{uid}')
def update_user(uid: int, body: UserUpdateBody, admin: dict = Depends(require_admin)):
    return users.update_user(uid, body.username, body.password, body.level)


@router.delete('/users/{uid}')
def delete_user(uid: int, admin: dict = Depends(require_admin)):
    return users.delete_user(uid, admin['id'])


class AvatarBody(BaseModel):
    avatar: str = ''


@router.put('/users/{uid}/avatar')
def set_avatar(uid: int, body: AvatarBody, user: dict = Depends(current_user)):
    # 仅本人或管理员可修改头像
    if user['id'] != uid and user['level'] != 'admin':
        raise HTTPException(status_code=403, detail='只能修改自己的头像')
    return users.set_avatar(uid, body.avatar)


# ---------------------------------------------------------------- settings
class AiCfg(BaseModel):
    provider: str = 'dashscope'
    base_url: str = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    api_key: str = ''
    model: str = 'qwen3.8-flash'
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1, le=32768)
    report_style: str = '简洁要点式'


class CityItem(BaseModel):
    name: str
    id: str = ''
    lat: float | None = None
    lon: float | None = None


class WeatherCfg(BaseModel):
    provider: Literal['qweather', 'open_meteo'] = 'open_meteo'
    api_host: str = 'k838m3jq58.re.qweatherapi.com'
    api_key: str = ''
    cities: list[CityItem] = []
    cache_minutes: int = Field(default=30, ge=1, le=1440)


class SettingsBody(BaseModel):
    ai: AiCfg | None = None
    weather: WeatherCfg | None = None


@router.get('/settings')
def get_settings():
    return store.mask_settings(store.load_settings())


@router.put('/settings')
def put_settings(body: SettingsBody):
    data = body.model_dump(exclude_none=True)
    # pydantic 模型转普通 dict
    if 'weather' in data and data['weather']:
        data['weather']['cities'] = [dict(c) for c in data['weather']['cities']]
    saved = store.save_settings(data)
    return store.mask_settings(saved)


class TestAiBody(BaseModel):
    ai: AiCfg


@router.post('/settings/test-ai')
def test_ai(body: TestAiBody):
    cfg = body.ai.model_dump()
    # 若前端未回传明文 key，用已保存的
    if not cfg.get('api_key'):
        cfg['api_key'] = store.load_settings()['ai'].get('api_key', '')
    return ai.test_connection(cfg)


@router.get('/ai/providers')
def ai_providers():
    return ai.PROVIDER_PRESETS


@router.get('/ai/models')
def ai_models(provider: str = Query('dashscope'), base_url: str = Query(None), api_key: str = Query('')):
    settings = store.load_settings()
    ai_cfg = settings['ai']
    prov = provider or ai_cfg.get('provider', 'dashscope')
    burl = base_url or ai.PROVIDER_PRESETS.get(prov, {}).get('base_url') or ai_cfg.get('base_url')
    key = api_key or ai_cfg.get('api_key', '')
    return ai.list_models(burl, key, prov)


# ---------------------------------------------------------------- tasks
class TasksBody(BaseModel):
    tasks: list[dict]
    revision: str | None = Field(default=None, description='乐观并发修订号；缺省则跳过冲突检查')


@router.get('/tasks')
def tasks_range(start: str = Query(...), end: str = Query(...), user: dict = Depends(current_user)):
    return store.range_stats(user['id'], start, end)


@router.get('/tasks/{date}')
def get_task(date: str, user: dict = Depends(current_user)):
    return store.load_day(user['id'], date)


@router.put('/tasks/{date}')
def put_task(date: str, body: TasksBody, user: dict = Depends(current_user)):
    return store.save_day(user['id'], date, body.tasks, body.revision)


# ---------------------------------------------------------------- diary
class DiaryBody(BaseModel):
    entries: list[dict]


@router.get('/diary')
def diary_range(start: str = Query(...), end: str = Query(...), user: dict = Depends(current_user)):
    """区间内每天有日记的条数（date -> count），供日历月视图打橙色圆点。"""
    return {'start': start, 'end': end, 'diary': store.diary_range_counts(user['id'], start, end)}


@router.get('/diary/{date}')
def get_diary(date: str, user: dict = Depends(current_user)):
    return store.load_diary(user['id'], date)


@router.put('/diary/{date}')
def put_diary(date: str, body: DiaryBody, user: dict = Depends(current_user)):
    return store.save_diary(user['id'], date, body.entries)


# ---------------------------------------------------------------- weather
@router.get('/weather')
def get_weather(city: str = Query(...), days: int = Query(7, ge=1, le=7)):
    return weather.get_weather(city, days)


@router.get('/weather/cities')
def weather_cities(keyword: str = Query(...)):
    return weather.search_cities(keyword)


# ---------------------------------------------------------------- reports
@router.get('/reports/week-data')
def week_data(start: str = Query(...), user: dict = Depends(current_user)):
    return report.build_week_data(user['id'], start)


class GenerateBody(BaseModel):
    start: str


@router.post('/reports/generate')
def generate(body: GenerateBody, user: dict = Depends(current_user)):
    def event_stream():
        try:
            for token in report.generate_stream(user['id'], body.start):
                yield f'data: {json.dumps({"delta": token}, ensure_ascii=False)}\n\n'
            yield f'data: {json.dumps({"done": True}, ensure_ascii=False)}\n\n'
        except Exception as e:
            yield f'data: {json.dumps({"error": str(e)}, ensure_ascii=False)}\n\n'
    return StreamingResponse(event_stream(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


class SaveReportBody(BaseModel):
    start: str
    markdown: str = Field(min_length=1)


@router.post('/reports/save')
def save_report(body: SaveReportBody, user: dict = Depends(current_user)):
    return report.save_report(user['id'], body.start, body.markdown)


@router.get('/reports')
def reports(user: dict = Depends(current_user)):
    return store.load_reports_index(user['id'])


@router.get('/reports/{record_id}')
def report_detail(record_id: str, user: dict = Depends(current_user)):
    return report.read_report(user['id'], record_id)
