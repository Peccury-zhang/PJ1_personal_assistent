"""LLM Provider 抽象：统一走 OpenAI 兼容协议（/v1/chat/completions、/v1/models）。

设计要点（见 weekly_report.md §7）：
- 不引入 LangChain，轻封装 httpx；
- 一个 OpenAICompatProvider 通吃 dashscope / deepseek / zhipu / openai / ollama；
- chat_stream 产出 token 迭代器，供 FastAPI SSE 转发；
- list_models 动态拉取账号可用模型，失败回退内置清单。
"""
from __future__ import annotations

import json
from typing import Iterator

import httpx

# Provider 预设：前端选择 provider 后自动填充 base_url
PROVIDER_PRESETS = {
    'dashscope': {
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'label': '阿里云百炼 (Qwen)',
    },
    'deepseek': {'base_url': 'https://api.deepseek.com/v1', 'label': 'DeepSeek'},
    'zhipu': {'base_url': 'https://open.bigmodel.cn/api/paas/v4', 'label': '智谱 GLM'},
    'openai': {'base_url': 'https://api.openai.com/v1', 'label': 'OpenAI'},
    'ollama': {'base_url': 'http://localhost:11434/v1', 'label': 'Ollama (本地)'},
}

# 内置兜底模型清单（拉取 /models 失败时使用）
FALLBACK_MODELS = {
    'dashscope': ['qwen3.8-flash', 'qwen-flash', 'qwen3.8-max', 'qwen3.7-plus', 'qwen-plus', 'qwen-max', 'qwen-turbo', 'qwq-plus'],
    'deepseek': ['deepseek-chat', 'deepseek-reasoner'],
    'zhipu': ['glm-4-flash', 'glm-4-air', 'glm-4-plus'],
    'openai': ['gpt-4o-mini', 'gpt-4o'],
    'ollama': ['qwen3:8b', 'llama3.1'],
}

TIMEOUT = httpx.Timeout(120.0, connect=10.0)


class LLMError(ValueError):
    pass


def _headers(api_key: str) -> dict:
    h = {'Content-Type': 'application/json'}
    if api_key:
        h['Authorization'] = f'Bearer {api_key}'
    return h


def chat(base_url: str, api_key: str, model: str, messages: list,
         temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """单轮对话，返回完整文本。用于测试连接等场景。"""
    url = base_url.rstrip('/') + '/chat/completions'
    body = {'model': model, 'messages': messages, 'temperature': temperature, 'max_tokens': max_tokens}
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(url, headers=_headers(api_key), json=body)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        raise LLMError(f'模型接口返回错误 {e.response.status_code}: {e.response.text[:300]}')
    except httpx.HTTPError as e:
        raise LLMError(f'无法连接模型接口: {e}')
    try:
        return data['choices'][0]['message']['content']
    except Exception:
        raise LLMError(f'响应格式异常: {json.dumps(data, ensure_ascii=False)[:300]}')


def chat_stream(base_url: str, api_key: str, model: str, messages: list,
                temperature: float = 0.7, max_tokens: int = 4096) -> Iterator[str]:
    """流式对话，逐段 yield 文本增量。用于 SSE。"""
    url = base_url.rstrip('/') + '/chat/completions'
    body = {'model': model, 'messages': messages, 'temperature': temperature,
            'max_tokens': max_tokens, 'stream': True}
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            with client.stream('POST', url, headers=_headers(api_key), json=body) as r:
                if r.status_code != 200:
                    detail = r.read().decode('utf-8', 'ignore')[:300]
                    raise LLMError(f'模型接口返回错误 {r.status_code}: {detail}')
                for line in r.iter_lines():
                    if not line or not line.startswith('data:'):
                        continue
                    payload = line[5:].strip()
                    if payload == '[DONE]':
                        break
                    try:
                        obj = json.loads(payload)
                        delta = obj['choices'][0].get('delta', {})
                        text = delta.get('content')
                        if text:
                            yield text
                    except Exception:
                        continue
    except httpx.HTTPError as e:
        raise LLMError(f'无法连接模型接口: {e}')


def list_models(base_url: str, api_key: str, provider: str) -> dict:
    """拉取账号可用模型列表（GET /models）。失败时回退内置清单。

    返回 {models: [...], source: 'remote'|'fallback', error?: str}
    """
    url = base_url.rstrip('/') + '/models'
    fallback = FALLBACK_MODELS.get(provider, [])
    try:
        with httpx.Client(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
            r = client.get(url, headers=_headers(api_key))
            r.raise_for_status()
            data = r.json()
        items = data.get('data', data) if isinstance(data, dict) else data
        models = []
        for it in items:
            mid = it.get('id') if isinstance(it, dict) else str(it)
            if mid:
                models.append(mid)
        models = sorted(set(models))
        if not models:
            return {'models': fallback, 'source': 'fallback', 'error': '接口返回空列表'}
        return {'models': models, 'source': 'remote'}
    except Exception as e:
        return {'models': fallback, 'source': 'fallback', 'error': str(e)[:200]}


def test_connection(ai_cfg: dict) -> dict:
    """用给定配置发一条最小对话验证可用性。"""
    try:
        reply = chat(
            ai_cfg['base_url'], ai_cfg.get('api_key', ''), ai_cfg['model'],
            [{'role': 'user', 'content': 'ping'}],
            temperature=0.1, max_tokens=8,
        )
        return {'ok': True, 'model': ai_cfg['model'], 'reply': reply[:100]}
    except LLMError as e:
        return {'ok': False, 'error': str(e)}
