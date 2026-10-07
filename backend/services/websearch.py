"""联网搜索：免 API Key 的网页搜索。

设计要点：
- 主源百度：先访问首页预热 Cookie（BAIDUID 等）再搜索，规避裸请求触发的验证码；
  结果块上的 mu 属性即真实目标链接，避免 baidu.com/link 跳转地址；
- 备源 Bing 网页版 / DuckDuckGo（其他网络环境可能可用），Bing 的无结果页(b_no)视为失败；
- 模块级 httpx.Client 复用 Cookie，线程锁保证并发安全；遇验证码自动重建会话重试一次；
- 返回统一结构 {provider, results: [{title, url, snippet, source}], error}；
  结果既供前端卡片排版展示，也注入模型上下文做带引用的回答。
"""
from __future__ import annotations

import html
import re
import threading
import time
import urllib.parse

import httpx

TIMEOUT = httpx.Timeout(15.0, connect=8.0)
HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

_LOCK = threading.Lock()
_client: httpx.Client | None = None
# 搜索结果短缓存（同查询 5 分钟内不重复请求，降低触发反爬概率）
_CACHE: dict = {}
_CACHE_TTL = 300
# 最近一次失败时各搜索源的具体原因（随 error 返回，便于界面上直接诊断）
LAST_ERRORS: list = []


def _clean(s: str) -> str:
    """去注释/标签 + 反转义 + 压缩空白。"""
    s = re.sub(r'<!--.*?-->', '', s or '', flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()


def _domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.replace('www.', '')
    except Exception:
        return ''


def _get_client(warm: bool = False) -> httpx.Client:
    global _client
    if _client is None or warm:
        if _client is not None:
            try:
                _client.close()
            except Exception:
                pass
        _client = httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        try:
            _client.get('https://www.baidu.com/')  # 预热 Cookie，降低验证码概率
        except Exception:
            pass
    return _client


def _is_captcha(resp: httpx.Response) -> bool:
    u = str(resp.url)
    return ('wappass' in u) or ('captcha' in u) or ('安全验证' in resp.text[:2000])


def _baidu(query: str, limit: int) -> list:
    with _LOCK:
        for attempt in range(3):
            if attempt:
                time.sleep(1.2 * attempt)  # 退避后重建会话重试
            c = _get_client(warm=True)
            try:
                r = c.get('https://www.baidu.com/s', params={'wd': query, 'rn': 20},
                          headers={'Referer': 'https://www.baidu.com/'})
            except Exception as e:
                LAST_ERRORS.append(f'baidu 请求异常 {type(e).__name__}: {str(e)[:60]}')
                continue
            if _is_captcha(r):
                LAST_ERRORS.append('baidu 触发验证码')
                continue
            blocks = [p for p in re.split(r'(?=<div class="result c-container)', r.text)
                      if p.startswith('<div class="result c-container')]
            out = []
            for b in blocks:
                mu = re.search(r'\smu="([^"]+)"', b)
                href = re.search(r'<h3[^>]*>.*?<a[^>]*href="([^"]+)"', b, re.S)
                url = (mu.group(1) if mu else '') or (href.group(1) if href else '')
                if not url.startswith('http'):
                    continue
                tm = re.search(r'<h3[^>]*>(.*?)</h3>', b, re.S)
                title = _clean(tm.group(1)) if tm else ''
                if not title:
                    continue
                snippet = ''
                for pat in (r'<[^>]*class="[^"]*summary-text_[^"]*"[^>]*>(.*?)</span>',
                            r'<div class="c-abstract[^"]*"[^>]*>(.*?)</div>',
                            r'<span class="content-right[^"]*"[^>]*>(.*?)</span>'):
                    sm = re.search(pat, b, re.S)
                    if sm:
                        snippet = _clean(sm.group(1))
                        if snippet:
                            break
                out.append({'title': title, 'url': url, 'snippet': snippet,
                            'source': _domain(url)})
                if len(out) >= limit:
                    break
            if out:
                return out
            LAST_ERRORS.append('baidu 无结果块')
    return []


def _bing(query: str, limit: int) -> list:
    url = 'https://www.bing.com/search?' + urllib.parse.urlencode(
        {'q': query, 'mkt': 'zh-CN', 'count': max(limit * 2, 10)})
    with _LOCK:
        r = _get_client().get(url)
    if 'b_no' in r.text:  # 无结果/被识别为机器人时的占位页
        return []
    out = []
    for item in re.findall(r'<li class="b_algo".*?</li>', r.text, re.S):
        m = re.search(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', item, re.S)
        if not m or not m.group(1).startswith('http'):
            continue
        sm = re.search(r'<p[^>]*>(.*?)</p>', item, re.S)
        out.append({
            'title': _clean(m.group(2)),
            'url': m.group(1),
            'snippet': _clean(sm.group(1)) if sm else '',
            'source': _domain(m.group(1)),
        })
        if len(out) >= limit:
            break
    return out


def _duckduckgo(query: str, limit: int) -> list:
    with _LOCK:
        r = _get_client().post('https://html.duckduckgo.com/html/', data={'q': query})
    titles = re.findall(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.S)
    snippets = re.findall(r'<[^>]*class="result__snippet"[^>]*>(.*?)</a>', r.text, re.S)
    out = []
    for i, (href, title) in enumerate(titles):
        if not href.startswith('http'):
            continue
        out.append({
            'title': _clean(title),
            'url': href,
            'snippet': _clean(snippets[i]) if i < len(snippets) else '',
            'source': _domain(href),
        })
        if len(out) >= limit:
            break
    return out


def search_web(query: str, limit: int = 6) -> dict:
    """搜索网页；依次尝试 百度 / Bing / DuckDuckGo，均失败时返回带具体原因的 error。"""
    global LAST_ERRORS
    query = (query or '').strip()
    if not query:
        return {'provider': '', 'results': [], 'error': '搜索关键词为空'}
    hit = _CACHE.get(query)
    if hit and time.time() - hit[0] < _CACHE_TTL:
        return {'provider': 'cache', 'results': hit[1], 'error': ''}
    LAST_ERRORS = []
    for fn, name in ((_baidu, 'baidu'), (_bing, 'bing'), (_duckduckgo, 'duckduckgo')):
        try:
            results = fn(query, limit)
            if results:
                _CACHE[query] = (time.time(), results)
                return {'provider': name, 'results': results, 'error': ''}
        except Exception as e:
            LAST_ERRORS.append(f'{name} {type(e).__name__}: {str(e)[:60]}')
    print('[websearch] fail:', query, LAST_ERRORS, flush=True)
    detail = '；'.join(LAST_ERRORS[:3]) if LAST_ERRORS else '网络不可达或被站点限制'
    return {'provider': '', 'results': [], 'error': f'联网搜索未获取到结果：{detail}'}
