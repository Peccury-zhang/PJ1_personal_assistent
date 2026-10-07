"""持久化存储层：persistent/ 下的 JSON 文件读写。

设计参照 E:\\Data_center\\yc2_robot\\vision_label\\backend\\store.py：
- 原子写入（临时文件 -> fsync -> os.replace），避免写入中断损坏数据；
- 乐观并发控制（revision = 文件内容 sha256），保存时比对，冲突抛 ConflictError -> 409；
- threading.RLock 串行化写入；
- 路径穿越防护（日期/文件名严格校验）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PERSISTENT_DIR = ROOT / 'persistent'
TASKS_DIR = PERSISTENT_DIR / 'tasks'
WEATHER_CACHE_DIR = PERSISTENT_DIR / 'weather_cache'
SETTINGS_FILE = PERSISTENT_DIR / 'settings.json'
REPORTS_INDEX_FILE = PERSISTENT_DIR / 'reports_index.json'
REPORT_OUTPUT_DIR = ROOT / 'weekly_report_output'

STORE_LOCK = threading.RLock()
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
PRIORITY = ('low', 'normal', 'high')

# 和风免费订阅专属 API Host（用户提供）；API Key 待补充
DEFAULT_SETTINGS = {
    'ai': {
        'provider': 'dashscope',
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'api_key': '',
        'model': 'qwen3.8-flash',
        'temperature': 0.7,
        'max_tokens': 4096,
        'report_style': '简洁要点式',
    },
    'weather': {
        'provider': 'open_meteo',  # 拿到和风 Key 后可切 qweather
        'api_host': 'k838m3jq58.re.qweatherapi.com',
        'api_key': '',
        'cities': [
            {'name': '北京', 'id': '101010100', 'lat': 39.90, 'lon': 116.41},
        ],
        'cache_minutes': 30,
    },
}


class ConflictError(ValueError):
    """乐观并发冲突：文件已被其他窗口/任务更新。"""


def _ensure_dirs() -> None:
    for d in (PERSISTENT_DIR, TASKS_DIR, WEATHER_CACHE_DIR, REPORT_OUTPUT_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- 按用户隔离
# 任务 / 周报索引 / 周报产物均按账户 ID 分目录存放，互不可见
def user_tasks_dir(uid: int) -> Path:
    return TASKS_DIR / str(uid)


def user_reports_index_file(uid: int) -> Path:
    return PERSISTENT_DIR / f'reports_index_{uid}.json'


def user_report_output_dir(uid: int) -> Path:
    return REPORT_OUTPUT_DIR / str(uid)


def migrate_legacy_to_user(uid: int) -> None:
    """把引入多用户之前的扁平旧数据迁移到指定账户名下（仅首次生效）。"""
    with STORE_LOCK:
        legacy_tasks = [p for p in TASKS_DIR.glob('*.json') if p.is_file()]
        if legacy_tasks:
            target = user_tasks_dir(uid)
            target.mkdir(parents=True, exist_ok=True)
            for p in legacy_tasks:
                dest = target / p.name
                if not dest.exists():
                    os.replace(p, dest)
        if REPORTS_INDEX_FILE.exists():
            dest = user_reports_index_file(uid)
            if not dest.exists():
                os.replace(REPORTS_INDEX_FILE, dest)
        legacy_md = [p for p in REPORT_OUTPUT_DIR.glob('*.md') if p.is_file()]
        if legacy_md:
            target = user_report_output_dir(uid)
            target.mkdir(parents=True, exist_ok=True)
            for p in legacy_md:
                dest = target / p.name
                if not dest.exists():
                    os.replace(p, dest)


def atomic_json(path: Path, data) -> None:
    """原子写入 JSON：临时文件 -> fsync -> os.replace。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _revision_of(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------- settings
def load_settings() -> dict:
    """读取设置；缺失字段用默认值补全（深合并一层）。"""
    _ensure_dirs()
    if not SETTINGS_FILE.exists():
        atomic_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        return json.loads(json.dumps(DEFAULT_SETTINGS))
    data = json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
    merged = json.loads(json.dumps(DEFAULT_SETTINGS))
    for section in ('ai', 'weather'):
        if isinstance(data.get(section), dict):
            merged[section].update(data[section])
    return merged


def save_settings(data: dict) -> dict:
    with STORE_LOCK:
        current = load_settings()
        for section in ('ai', 'weather'):
            if isinstance(data.get(section), dict):
                # api_key 为空字符串时表示“不修改”，保留原值
                incoming = dict(data[section])
                if section == 'ai' and not incoming.get('api_key'):
                    incoming['api_key'] = current['ai'].get('api_key', '')
                if section == 'weather' and not incoming.get('api_key'):
                    incoming['api_key'] = current['weather'].get('api_key', '')
                current[section].update(incoming)
        atomic_json(SETTINGS_FILE, current)
        return current


def mask_settings(data: dict) -> dict:
    """返回给前端时掩码 api_key。"""
    out = json.loads(json.dumps(data))
    for section in ('ai', 'weather'):
        key = out.get(section, {}).get('api_key', '')
        if key:
            out[section]['api_key_masked'] = key[:3] + '****' + key[-2:] if len(key) > 6 else '****'
            out[section]['has_api_key'] = True
        else:
            out[section]['api_key_masked'] = ''
            out[section]['has_api_key'] = False
        out[section].pop('api_key', None)
    return out


# ---------------------------------------------------------------- tasks
def _validate_date(date: str) -> str:
    if not DATE_RE.match(date):
        raise ValueError('日期格式必须为 YYYY-MM-DD')
    return date


def task_file(uid: int, date: str) -> Path:
    _validate_date(date)
    return user_tasks_dir(uid) / f'{date}.json'


def _normalize_task(t: dict) -> dict:
    title = str(t.get('title', '')).strip()
    if not title:
        raise ValueError('任务标题不能为空')
    if len(title) > 200:
        raise ValueError('任务标题过长（<=200 字符）')
    priority = t.get('priority', 'normal')
    if priority not in PRIORITY:
        priority = 'normal'
    done = bool(t.get('done', False))
    now = time.strftime('%Y-%m-%dT%H:%M:%S')
    return {
        'id': str(t.get('id') or hashlib.sha1(f'{title}{now}{os.urandom(4).hex()}'.encode()).hexdigest()[:12]),
        'title': title,
        'note': str(t.get('note', ''))[:2000],
        'done': done,
        'priority': priority,
        'created_at': t.get('created_at') or now,
        'done_at': t.get('done_at') or (now if done else None),
    }


def load_day(uid: int, date: str) -> dict:
    """读取某天任务；文件不存在返回空结构。带 revision。"""
    _validate_date(date)
    f = task_file(uid, date)
    if not f.exists():
        return {'date': date, 'tasks': [], 'updated': None, 'revision': '0'}
    raw = f.read_bytes()
    data = json.loads(raw)
    data.setdefault('tasks', [])
    data['date'] = date
    data['revision'] = _revision_of(raw)
    return data


def save_day(uid: int, date: str, tasks: list, expected_revision: str | None = None) -> dict:
    _validate_date(date)
    with STORE_LOCK:
        current = load_day(uid, date)
        if expected_revision is not None and current['revision'] != expected_revision:
            raise ConflictError('任务已被其他窗口更新；本地修改仍保留，请刷新后重试')
        normalized = [_normalize_task(t) for t in tasks]
        data = {
            'date': date,
            'tasks': normalized,
            'updated': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }
        atomic_json(task_file(uid, date), data)
        return load_day(uid, date)


def daterange(start: str, end: str) -> list[str]:
    """返回 [start, end] 闭区间内的所有日期字符串。"""
    from datetime import date as _d, timedelta
    _validate_date(start)
    _validate_date(end)
    y, m, d = map(int, start.split('-'))
    ye, me, de = map(int, end.split('-'))
    cur, last = _d(y, m, d), _d(ye, me, de)
    if cur > last:
        raise ValueError('start 不能晚于 end')
    out = []
    while cur <= last:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def range_stats(uid: int, start: str, end: str) -> dict:
    """区间内每日 total/done 统计 + 明细，供日历月视图与周报使用。"""
    days = []
    for ds in daterange(start, end):
        data = load_day(uid, ds)
        tasks = data['tasks']
        days.append({
            'date': ds,
            'total': len(tasks),
            'done': sum(1 for t in tasks if t['done']),
            'tasks': tasks,
        })
    total = sum(d['total'] for d in days)
    done = sum(d['done'] for d in days)
    return {
        'start': start,
        'end': end,
        'days': days,
        'summary': {'total': total, 'done': done, 'rate': round(done / total, 4) if total else 0.0},
    }


# ---------------------------------------------------------------- reports index
def load_reports_index(uid: int) -> dict:
    _ensure_dirs()
    f = user_reports_index_file(uid)
    if not f.exists():
        return {'reports': []}
    return json.loads(f.read_text(encoding='utf-8'))


def add_report_record(uid: int, record: dict) -> dict:
    with STORE_LOCK:
        index = load_reports_index(uid)
        reports = [r for r in index.get('reports', []) if r.get('id') != record.get('id')]
        reports.insert(0, record)
        index['reports'] = reports
        atomic_json(user_reports_index_file(uid), index)
        return index


def report_output_path(uid: int, filename: str) -> Path:
    """校验周报文件名，防路径穿越；按用户分目录。"""
    safe = Path(filename).name
    if not safe.endswith('.md') or safe != filename:
        raise ValueError('周报文件名非法')
    base = user_report_output_dir(uid)
    base.mkdir(parents=True, exist_ok=True)
    p = (base / safe).resolve()
    if p.parent != base.resolve():
        raise ValueError('周报路径非法')
    return p


# ---------------------------------------------------------------- diary
def user_diary_dir(uid: int) -> Path:
    return PERSISTENT_DIR / 'diary' / str(uid)


def diary_file(uid: int, date: str) -> Path:
    _validate_date(date)
    return user_diary_dir(uid) / f'{date}.json'


def _normalize_diary(e: dict) -> dict:
    content = str(e.get('content', '')).strip()
    if not content:
        raise ValueError('日记内容不能为空')
    if len(content) > 5000:
        raise ValueError('日记内容过长（<=5000 字符）')
    now = time.strftime('%Y-%m-%dT%H:%M:%S')
    return {
        'id': str(e.get('id') or hashlib.sha1(f'{content}{now}{os.urandom(4).hex()}'.encode()).hexdigest()[:12]),
        'content': content,
        'created_at': e.get('created_at') or now,
        'updated_at': now,
    }


def load_diary(uid: int, date: str) -> dict:
    _validate_date(date)
    f = diary_file(uid, date)
    if not f.exists():
        return {'date': date, 'entries': [], 'updated': None}
    data = json.loads(f.read_text(encoding='utf-8'))
    data.setdefault('entries', [])
    data['date'] = date
    return data


def save_diary(uid: int, date: str, entries: list) -> dict:
    _validate_date(date)
    with STORE_LOCK:
        normalized = [_normalize_diary(e) for e in entries]
        data = {
            'date': date,
            'entries': normalized,
            'updated': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }
        atomic_json(diary_file(uid, date), data)
        return load_diary(uid, date)


def diary_range_counts(uid: int, start: str, end: str) -> dict:
    """区间内每天的日记条数（仅返回有日记的日期），供日历月视图打点。"""
    out: dict = {}
    for ds in daterange(start, end):
        f = diary_file(uid, ds)
        if not f.exists():
            continue
        try:
            n = len(json.loads(f.read_text(encoding='utf-8')).get('entries', []))
        except Exception:
            n = 0
        if n:
            out[ds] = n
    return out


# ---------------------------------------------------------------- weather cache
def weather_cache_file(date: str, city: str) -> Path:
    _validate_date(date)
    safe_city = re.sub(r'[^\w\u4e00-\u9fff-]', '_', city)[:40]
    return WEATHER_CACHE_DIR / f'{date}_{safe_city}.json'


def load_weather_cache(date: str, city: str, max_age_minutes: int) -> dict | None:
    f = weather_cache_file(date, city)
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text(encoding='utf-8'))
    except Exception:
        return None
    fetched = data.get('fetched_at')
    if not fetched:
        return None
    try:
        ts = time.mktime(time.strptime(fetched, '%Y-%m-%dT%H:%M:%S'))
    except Exception:
        return None
    if (time.time() - ts) > max_age_minutes * 60:
        return None
    return data


def save_weather_cache(date: str, city: str, payload: dict) -> None:
    payload = dict(payload)
    payload['fetched_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    atomic_json(weather_cache_file(date, city), payload)
