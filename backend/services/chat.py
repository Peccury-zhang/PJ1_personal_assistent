"""AI 助手会话：按用户隔离的多轮对话持久化 + 流式回复。

设计要点：
- 索引 persistent/chats/<uid>/index.json 只存轻量元数据（标题/时间/条数），
  正文 persistent/chats/<uid>/<sid>.json 存完整消息；目录按 uid 隔离，互不可见；
- 消息内容为有序 blocks（text / image），图片以 dataURL 内联在 blocks 中，
  因此「删除会话」即连图片内容一并删除，无需额外清理；
- 回复走 ai.chat_stream（OpenAI 兼容协议），历史按窗口裁剪后转 messages，
  用户消息中的图片转 image_url part 供视觉模型理解；
- 助手回复文本按 Markdown 图片语法切分为 text/image 交替的 blocks，
  前端按序渲染，图片不会被挤到末尾；
- 联网搜索开启时先由 websearch 抓取结果：结果以 search block 存入助手消息
  （前端卡片排版、随会话重加载），同时注入模型上下文要求带 [序号] 引用作答。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Iterator

from .. import store
from . import ai, websearch

CHATS_DIR = store.PERSISTENT_DIR / 'chats'
SID_RE = re.compile(r'^[A-Za-z0-9_-]{4,64}$')
# Markdown 行内图片：![alt](src) 或 ![alt](src "title")
IMG_MD_RE = re.compile(r'!\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
# 送入模型的历史消息窗口（条数），避免上下文过长
HISTORY_WINDOW = 8
# 单张图片 dataURL 长度上限（约对应原始 10MB）
MAX_IMAGE_DATA_LEN = 10 * 1024 * 1024 * 4 // 3

SYSTEM_PROMPT = (
    '你是「个人全能助手」内置的 AI 助手，负责回答用户的问题并协助处理日常事务。'
    '要求：1) 使用与用户相同的语言作答；2) 输出 Markdown 格式，善用标题、列表、表格与代码块；'
    '3) 所有行顶格书写，行首不要制表符/空格缩进，避免被渲染成代码块；'
    '4) 若用户附带图片，先理解图片内容再作答；5) 不确定的内容如实说明，不要编造。'
)


# ---------------------------------------------------------------- 路径与索引
def user_chats_dir(uid: int) -> Path:
    return CHATS_DIR / str(uid)


def _index_file(uid: int) -> Path:
    return user_chats_dir(uid) / 'index.json'


def _session_file(uid: int, sid: str) -> Path:
    if not SID_RE.match(sid or ''):
        raise ValueError('会话 ID 非法')
    return user_chats_dir(uid) / f'{sid}.json'


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%S')


def _new_id(prefix: str) -> str:
    return f'{prefix}{time.strftime("%y%m%d%H%M%S")}{hashlib.sha1(os.urandom(8)).hexdigest()[:6]}'


def load_index(uid: int) -> dict:
    f = _index_file(uid)
    if not f.exists():
        return {'sessions': []}
    try:
        data = json.loads(f.read_text(encoding='utf-8'))
    except Exception:
        return {'sessions': []}
    data.setdefault('sessions', [])
    return data


def _save_index(uid: int, index: dict) -> None:
    store.atomic_json(_index_file(uid), index)


def _meta(session: dict) -> dict:
    return {
        'id': session['id'],
        'title': session.get('title', '新对话'),
        'created_at': session.get('created_at', ''),
        'updated_at': session.get('updated_at', ''),
        'message_count': len(session.get('messages', [])),
    }


def list_sessions(uid: int) -> dict:
    sessions = sorted(load_index(uid)['sessions'],
                      key=lambda s: s.get('updated_at') or '', reverse=True)
    return {'sessions': sessions}


def load_session(uid: int, sid: str) -> dict:
    f = _session_file(uid, sid)
    if not f.exists():
        raise FileNotFoundError(sid)
    data = json.loads(f.read_text(encoding='utf-8'))
    data.setdefault('messages', [])
    return data


def create_session(uid: int, title: str = '') -> dict:
    sid = _new_id('c')
    now = _now()
    session = {'id': sid, 'title': title or '新对话', 'created_at': now,
               'updated_at': now, 'messages': []}
    with store.STORE_LOCK:
        store.atomic_json(_session_file(uid, sid), session)
        index = load_index(uid)
        index['sessions'] = [_meta(session)] + index['sessions']
        _save_index(uid, index)
    return session


def delete_session(uid: int, sid: str) -> dict:
    """删除会话：正文文件（含内联图片）与索引记录一并删除。"""
    with store.STORE_LOCK:
        f = _session_file(uid, sid)
        if f.exists():
            os.unlink(f)
        index = load_index(uid)
        index['sessions'] = [s for s in index['sessions'] if s.get('id') != sid]
        _save_index(uid, index)
    return {'ok': True}


# ---------------------------------------------------------------- 消息
def _normalize_image(img: dict) -> dict:
    data = str(img.get('data') or '').strip()
    if not data.startswith('data:image/'):
        raise ValueError('仅支持图片文件')
    if len(data) > MAX_IMAGE_DATA_LEN:
        raise ValueError('图片过大（单张 <= 10MB）')
    return {'type': 'image', 'data': data, 'name': str(img.get('name') or '')[:80]}


def _title_of(blocks: list) -> str:
    text = ''.join(b.get('text', '') for b in blocks if b.get('type') == 'text').strip()
    if text:
        return re.sub(r'\s+', ' ', text)[:30]
    n = sum(1 for b in blocks if b.get('type') == 'image')
    return f'[图片 {n} 张]' if n else '新对话'


def append_message(uid: int, sid: str, role: str, blocks: list, model: str | None = None) -> dict:
    now = _now()
    msg = {'id': _new_id('m'), 'role': role, 'blocks': blocks, 'created_at': now}
    if model:
        msg['model'] = model
    with store.STORE_LOCK:
        session = load_session(uid, sid)
        session['messages'].append(msg)
        session['updated_at'] = now
        if role == 'user' and session.get('title', '新对话') == '新对话':
            session['title'] = _title_of(blocks)
        store.atomic_json(_session_file(uid, sid), session)
        index = load_index(uid)
        rest = [s for s in index['sessions'] if s.get('id') != sid]
        rest.insert(0, _meta(session))
        index['sessions'] = rest
        _save_index(uid, index)
    return msg


def parse_blocks(md: str) -> list:
    """把 Markdown 文本按图片语法切分为 text/image 交替的有序 blocks。"""
    blocks: list = []
    pos = 0
    for m in IMG_MD_RE.finditer(md):
        if m.start() > pos:
            seg = md[pos:m.start()]
            if seg.strip():
                blocks.append({'type': 'text', 'text': seg})
        src = m.group(1)
        if src.startswith('data:image/') or src.startswith('http://') or src.startswith('https://'):
            blocks.append({'type': 'image', 'data': src, 'name': ''})
        else:
            # 非可内联来源，保留原文避免丢内容
            blocks.append({'type': 'text', 'text': m.group(0)})
        pos = m.end()
    tail = md[pos:]
    if tail.strip():
        blocks.append({'type': 'text', 'text': tail})
    return blocks


# ---------------------------------------------------------------- 模型 messages
def _search_context(results: list) -> str:
    """把搜索结果拼为模型可见的引用上下文。"""
    lines = ['【联网搜索结果】回答时优先依据以下资料，并在引用处标注 [序号]；资料不足时如实说明。']
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.get('title', '')}（{r.get('source', '')}）\n"
                     f"{r.get('snippet', '')}\n链接：{r.get('url', '')}")
    return '\n'.join(lines)


def _to_model_message(msg: dict, with_images: bool) -> dict:
    texts = [b.get('text', '') for b in msg.get('blocks', [])
             if b.get('type') == 'text' and b.get('text', '').strip()]
    images = [b for b in msg.get('blocks', []) if b.get('type') == 'image']
    if msg['role'] != 'user' or not with_images or not images:
        content = '\n\n'.join(texts)
        if images:
            content += f'\n（附图片 {len(images)} 张）'
        return {'role': msg['role'], 'content': content}
    parts = [{'type': 'image_url', 'image_url': {'url': b['data']}} for b in images]
    parts.append({'type': 'text', 'text': '\n\n'.join(texts) or '请描述并分析这些图片'})
    return {'role': 'user', 'content': parts}


def start_reply(uid: int, session_id: str | None, text: str,
                images: list | None = None, model: str | None = None,
                web_search: bool = False):
    """落盘用户消息并构造模型上下文；返回 (sid, token 迭代器, 搜索信息)。

    迭代器耗尽或被中止时都会把已生成的回复追加保存（含 search/图片 blocks）。
    """
    text = (text or '').strip()
    imgs = [_normalize_image(i) for i in (images or [])]
    if not text and not imgs:
        raise ValueError('请输入问题或附加图片')
    settings = store.load_settings()
    ai_cfg = settings['ai']
    if not ai_cfg.get('api_key') and ai_cfg.get('provider') != 'ollama':
        raise ai.LLMError('尚未配置 AI API Key，请在「设置 → AI」中填写')

    search_results: list = []
    search_error = ''
    if web_search and text:
        sr = websearch.search_web(text)
        search_results = sr.get('results') or []
        search_error = sr.get('error') or ''

    if session_id:
        load_session(uid, session_id)  # 校验存在；目录按 uid 隔离即完成归属校验
        sid = session_id
    else:
        sid = create_session(uid)['id']
    user_blocks = imgs + ([{'type': 'text', 'text': text}] if text else [])
    append_message(uid, sid, 'user', user_blocks)

    session = load_session(uid, sid)
    prior = session['messages'][:-1][-HISTORY_WINDOW:]
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    messages += [_to_model_message(m, with_images=False) for m in prior]
    last = _to_model_message(session['messages'][-1], with_images=True)
    if search_results:
        extra = _search_context(search_results)
        if isinstance(last['content'], str):
            last['content'] = (last['content'] + '\n\n' + extra).strip()
        else:
            for part in last['content']:
                if part['type'] == 'text':
                    part['text'] = (part['text'] + '\n\n' + extra).strip()
                    break
            else:
                last['content'].append({'type': 'text', 'text': extra})
    messages.append(last)
    use_model = model or ai_cfg.get('model')

    def gen() -> Iterator[str]:
        buf: list = []
        try:
            for tok in ai.chat_stream(
                ai_cfg['base_url'], ai_cfg.get('api_key', ''), use_model, messages,
                temperature=float(ai_cfg.get('temperature', 0.7)),
                max_tokens=int(ai_cfg.get('max_tokens', 4096)),
            ):
                buf.append(tok)
                yield tok
        finally:
            full = ''.join(buf).strip()
            blocks: list = []
            if search_results:
                blocks.append({'type': 'search', 'results': search_results})
            blocks += parse_blocks(full) if full else [{'type': 'text', 'text': '（本次未获得回复）'}]
            try:
                append_message(uid, sid, 'assistant', blocks, model=use_model)
            except Exception:
                pass

    return sid, gen(), {'results': search_results, 'error': search_error}
