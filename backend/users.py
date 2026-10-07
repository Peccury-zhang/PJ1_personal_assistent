"""用户与会话管理：persistent/users.json + PBKDF2 加盐哈希 + 落盘 Bearer Token。

设计目标：简单 + 安全，且无需引入数据库。
- 账户 ID：自增整数（10001 起），可读且稳定；
- 密码：仅存 PBKDF2-HMAC-SHA256(password, salt, 120000) 的 hex 与独立 salt，不存明文；
- 会话：登录签发 secrets.token_urlsafe(32)，持久化到 persistent/sessions.json，
  重启服务 / 重启浏览器后仍可免登录直接进入（有效期 30 天）。
"""
from __future__ import annotations

import hashlib
import json
import secrets
import time
from pathlib import Path

from . import store

USERS_FILE = store.PERSISTENT_DIR / 'users.json'
SESSIONS_FILE = store.PERSISTENT_DIR / 'sessions.json'

PBKDF2_ROUNDS = 120_000
SESSION_TTL_SECONDS = 30 * 24 * 3600  # 30 天，配合前端 localStorage 实现“下次直接打开”
LEVELS = ('admin', 'user')

# token -> {'uid': int, 'exp': float}（内存缓存，变更时落盘）
_SESSIONS: dict[str, dict] = {}
_SESSIONS_LOADED = False


class AuthError(ValueError):
    """登录/鉴权失败。"""


# ---------------------------------------------------------------- 密码哈希
def _hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                               bytes.fromhex(salt_hex), PBKDF2_ROUNDS).hex()


def _new_salt() -> str:
    return secrets.token_hex(16)


def verify_password(password: str, salt_hex: str, expected_hex: str) -> bool:
    return secrets.compare_digest(_hash_password(password, salt_hex), expected_hex)


# ---------------------------------------------------------------- 存储
def _load_users() -> list[dict]:
    store._ensure_dirs()
    if not USERS_FILE.exists():
        return []
    try:
        return json.loads(USERS_FILE.read_text(encoding='utf-8'))
    except Exception:
        return []


def _save_users(users: list[dict]) -> None:
    store.atomic_json(USERS_FILE, users)


def _public(u: dict) -> dict:
    return {'id': u['id'], 'username': u['username'], 'level': u['level'],
            'created_at': u.get('created_at'), 'avatar': u.get('avatar', '')}


def _next_id(users: list[dict]) -> int:
    return max([u['id'] for u in users], default=10000) + 1


def ensure_seed() -> None:
    """首次运行创建默认管理员：peccury / 1234。"""
    with store.STORE_LOCK:
        users = _load_users()
        if users:
            return
        salt = _new_salt()
        users.append({
            'id': 10001,
            'username': 'peccury',
            'level': 'admin',
            'salt': salt,
            'password_hash': _hash_password('1234', salt),
            'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        })
        _save_users(users)


# ---------------------------------------------------------------- 认证 / 会话
def authenticate(username: str, password: str) -> dict | None:
    uname = (username or '').strip()
    for u in _load_users():
        if u['username'] == uname and verify_password(password or '', u['salt'], u['password_hash']):
            return u
    return None


def create_session(user: dict) -> str:
    token = secrets.token_urlsafe(32)
    _load_sessions()
    _SESSIONS[token] = {'uid': user['id'], 'exp': time.time() + SESSION_TTL_SECONDS}
    _save_sessions()
    return token


def _load_sessions() -> None:
    """首次使用时从 sessions.json 载入未过期会话（重启后免登录的关键）。"""
    global _SESSIONS_LOADED
    if _SESSIONS_LOADED:
        return
    _SESSIONS_LOADED = True
    store._ensure_dirs()
    if not SESSIONS_FILE.exists():
        return
    try:
        data = json.loads(SESSIONS_FILE.read_text(encoding='utf-8'))
        now = time.time()
        for t, s in (data or {}).items():
            if isinstance(s, dict) and (s.get('exp') or 0) > now:
                _SESSIONS[t] = {'uid': int(s['uid']), 'exp': float(s['exp'])}
    except Exception:
        pass


def _save_sessions() -> None:
    store.atomic_json(SESSIONS_FILE, _SESSIONS)


def _purge_expired() -> None:
    _load_sessions()
    now = time.time()
    expired = [t for t, s in _SESSIONS.items() if s['exp'] < now]
    if expired:
        for t in expired:
            _SESSIONS.pop(t, None)
        _save_sessions()


def get_session_user(token: str) -> dict | None:
    if not token:
        return None
    _purge_expired()
    sess = _SESSIONS.get(token)
    if not sess:
        return None
    for u in _load_users():
        if u['id'] == sess['uid']:
            return u
    return None


def destroy_session(token: str) -> None:
    _load_sessions()
    if _SESSIONS.pop(token, None) is not None:
        _save_sessions()


# ---------------------------------------------------------------- 用户管理（管理员）
def list_users() -> list[dict]:
    return [_public(u) for u in _load_users()]


def _require_unique_username(users: list[dict], username: str, exclude_id: int | None = None) -> str:
    uname = (username or '').strip()
    if not uname:
        raise ValueError('用户名不能为空')
    if len(uname) > 30:
        raise ValueError('用户名过长（<=30 字符）')
    for u in users:
        if u['username'] == uname and u['id'] != exclude_id:
            raise ValueError(f'用户名「{uname}」已存在')
    return uname


def create_user(username: str, password: str, level: str = 'user') -> dict:
    if level not in LEVELS:
        raise ValueError('用户等级非法')
    if not password:
        raise ValueError('密码不能为空')
    with store.STORE_LOCK:
        users = _load_users()
        uname = _require_unique_username(users, username)
        salt = _new_salt()
        user = {
            'id': _next_id(users),
            'username': uname,
            'level': level,
            'salt': salt,
            'password_hash': _hash_password(password, salt),
            'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }
        users.append(user)
        _save_users(users)
        return _public(user)


def update_user(uid: int, username: str | None = None,
                password: str | None = None, level: str | None = None) -> dict:
    with store.STORE_LOCK:
        users = _load_users()
        target = next((u for u in users if u['id'] == uid), None)
        if not target:
            raise FileNotFoundError('用户不存在')
        if username is not None:
            target['username'] = _require_unique_username(users, username, exclude_id=uid)
        if level is not None:
            if level not in LEVELS:
                raise ValueError('用户等级非法')
            # 不允许把最后一个管理员降级，导致无人可管理
            if level != 'admin' and target['level'] == 'admin' \
                    and sum(1 for u in users if u['level'] == 'admin') <= 1:
                raise ValueError('至少保留一名管理员')
            target['level'] = level
        if password:
            salt = _new_salt()
            target['salt'] = salt
            target['password_hash'] = _hash_password(password, salt)
        _save_users(users)
        return _public(target)


# ---------------------------------------------------------------- 头像
# 仅接受前端 canvas 压缩后的 data URL；限制长度防止 users.json 膨胀
AVATAR_MAX_CHARS = 400_000
AVATAR_PREFIXES = (
    'data:image/png;base64,',
    'data:image/jpeg;base64,',
    'data:image/webp;base64,',
)


def set_avatar(uid: int, data_url: str) -> dict:
    """保存头像（data URL）；传空串表示清除。"""
    avatar = (data_url or '').strip()
    if avatar:
        if not avatar.startswith(AVATAR_PREFIXES):
            raise ValueError('头像仅支持 jpg/png/webp 格式图像')
        if len(avatar) > AVATAR_MAX_CHARS:
            raise ValueError('头像过大，请选择较小的图片')
    with store.STORE_LOCK:
        users = _load_users()
        target = next((u for u in users if u['id'] == uid), None)
        if not target:
            raise FileNotFoundError('用户不存在')
        target['avatar'] = avatar
        _save_users(users)
        return _public(target)


def delete_user(uid: int, operator_id: int) -> dict:
    with store.STORE_LOCK:
        users = _load_users()
        target = next((u for u in users if u['id'] == uid), None)
        if not target:
            raise FileNotFoundError('用户不存在')
        if uid == operator_id:
            raise ValueError('不能删除当前登录的账户')
        if target['level'] == 'admin' and sum(1 for u in users if u['level'] == 'admin') <= 1:
            raise ValueError('至少保留一名管理员')
        users = [u for u in users if u['id'] != uid]
        _save_users(users)
        # 失效该用户的所有会话
        _load_sessions()
        for t in [t for t, s in _SESSIONS.items() if s['uid'] == uid]:
            _SESSIONS.pop(t, None)
        _save_sessions()
        return {'ok': True}
