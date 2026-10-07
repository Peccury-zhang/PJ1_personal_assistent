"""周报生成：聚合一周任务数据 -> 构造 Prompt -> 流式调用 LLM -> 保存 Markdown。

关键原则（weekly_report.md §7.3）：AI 输出不直接落盘，前端可编辑后调用 save 才写文件。
"""
from __future__ import annotations

import time
from typing import Iterator

from .. import store
from . import ai


def week_bounds(any_date: str) -> tuple[str, str]:
    """返回该日期所在 ISO 周（周一起始）的 (周一, 周日)。"""
    from datetime import date as _d, timedelta
    y, m, d = map(int, any_date.split('-'))
    cur = _d(y, m, d)
    monday = cur - timedelta(days=cur.weekday())
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def build_week_data(uid: int, start: str) -> dict:
    """聚合一周数据（start 应为周一）。"""
    start, end = week_bounds(start)
    stats = store.range_stats(uid, start, end)
    undone = []
    for day in stats['days']:
        for t in day['tasks']:
            if not t['done']:
                undone.append({'date': day['date'], 'title': t['title'], 'priority': t['priority']})
    iso_year, iso_week, _ = _iso_week(start)
    return {
        'week_id': f'{iso_year}-W{iso_week:02d}',
        'week_start': start,
        'week_end': end,
        'summary': stats['summary'],
        'days': stats['days'],
        'undone': undone,
    }


def _iso_week(date_str: str) -> tuple[int, int, int]:
    from datetime import date as _d
    y, m, d = map(int, date_str.split('-'))
    return _d(y, m, d).isocalendar()


def build_prompt(week_data: dict, style: str) -> list:
    """构造周报生成的 messages。"""
    s = week_data['summary']
    # 精简按天明细，控制 token
    lines = []
    for day in week_data['days']:
        done_titles = [t['title'] for t in day['tasks'] if t['done']]
        todo_titles = [t['title'] for t in day['tasks'] if not t['done']]
        seg = f"{day['date']}（{_cn_week(day['date'])}）：完成 {len(done_titles)}/{day['total']}"
        if done_titles:
            seg += f"｜已完成：{'、'.join(done_titles)}"
        if todo_titles:
            seg += f"｜未完成：{'、'.join(todo_titles)}"
        lines.append(seg)
    undone_text = '、'.join(f"{u['title']}({u['date']})" for u in week_data['undone']) or '无'

    system = (
        '你是一名资深的工作周报撰写助手。根据用户提供的一周任务数据，输出 Markdown 格式周报。'
        '要求：1) 结构包含【本周概览】【完成情况】【亮点与产出】【未完成与风险】【下周计划建议】五个小节，用二级标题；'
        '2) 本周概览给出完成率与一句话总评；'
        f'3) 语言风格{style}；'
        '4) 严格基于所给数据，不得编造数据中不存在的任务或事实；'
        '5) 直接输出 Markdown 正文，不要额外解释。'
    )
    user = (
        f"周期：{week_data['week_start']} ~ {week_data['week_end']}（{week_data['week_id']}）\n"
        f"统计：总任务 {s['total']}，已完成 {s['done']}，完成率 {round(s['rate']*100,1)}%\n"
        f"按天明细：\n" + '\n'.join(lines) + '\n'
        f"未完成任务清单：{undone_text}"
    )
    return [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]


def _cn_week(date_str: str) -> str:
    from datetime import datetime
    names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    try:
        return names[datetime.strptime(date_str, '%Y-%m-%d').weekday()]
    except Exception:
        return ''


def generate_stream(uid: int, start: str) -> Iterator[str]:
    """流式生成周报文本。"""
    settings = store.load_settings()
    ai_cfg = settings['ai']
    if not ai_cfg.get('api_key') and ai_cfg.get('provider') != 'ollama':
        raise ai.LLMError('尚未配置 AI API Key，请在「设置 → AI」中填写')
    week_data = build_week_data(uid, start)
    if week_data['summary']['total'] == 0:
        raise ai.LLMError('该周没有任何任务数据，无法生成周报')
    messages = build_prompt(week_data, ai_cfg.get('report_style', '简洁要点式'))
    yield from ai.chat_stream(
        ai_cfg['base_url'], ai_cfg.get('api_key', ''), ai_cfg['model'], messages,
        temperature=float(ai_cfg.get('temperature', 0.7)),
        max_tokens=int(ai_cfg.get('max_tokens', 4096)),
    )


def save_report(uid: int, start: str, markdown: str) -> dict:
    """保存周报到 weekly_report_output/<uid>/ 并登记索引。返回记录。"""
    week_data = build_week_data(uid, start)
    week_id = week_data['week_id']
    ts = time.strftime('%Y%m%d_%H%M%S')
    filename = f'weekly_report_{week_id}_{ts}.md'
    path = store.report_output_path(uid, filename)
    header = f'<!-- generated_at: {time.strftime("%Y-%m-%dT%H:%M:%S")} | week: {week_id} -->\n\n'
    path.write_text(header + markdown, encoding='utf-8')
    settings = store.load_settings()
    s = week_data['summary']
    record = {
        'id': f'{week_id}_{ts}',
        'week_id': week_id,
        'week_start': week_data['week_start'],
        'week_end': week_data['week_end'],
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'model': settings['ai'].get('model'),
        'file': f'weekly_report_output/{uid}/{filename}',
        'stats': {'total': s['total'], 'done': s['done'], 'rate': s['rate']},
    }
    store.add_report_record(uid, record)
    return record


def read_report(uid: int, record_id: str) -> dict:
    index = store.load_reports_index(uid)
    for r in index.get('reports', []):
        if r.get('id') == record_id:
            path = store.user_report_output_dir(uid) / r['file'].split('/')[-1]
            content = path.read_text(encoding='utf-8') if path.exists() else ''
            return {**r, 'content': content}
    raise FileNotFoundError(record_id)
