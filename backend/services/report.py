"""周报生成：聚合一周任务数据 -> 构造 Prompt -> 流式调用 LLM -> 保存 Markdown。

关键原则（weekly_report.md §7.3）：AI 输出不直接落盘，前端可编辑后调用 save 才写文件。
"""
from __future__ import annotations

import time
import uuid
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
    """聚合一周数据（start 应为周一）。

    只统计到今天为止：晚于今天的日期尚未发生，其“已完成”不计入周报总结。
    """
    from datetime import date as _d
    start, end = week_bounds(start)
    stat_end = min(end, _d.today().isoformat())  # 超过今天的部分不纳入统计
    if stat_end < start:
        stats = {'days': [], 'summary': {'total': 0, 'done': 0, 'rate': 0.0}}
    else:
        stats = store.range_stats(uid, start, stat_end)
    undone = []
    for day in stats['days']:
        for t in day['tasks']:
            if not t['done']:
                undone.append({'date': day['date'], 'title': t['title'], 'priority': t['priority']})
    iso_year, iso_week, _ = _iso_week(start)
    return {
        'week_id': f'{iso_year}-W{iso_week:02d}',
        'iso_year': iso_year,
        'iso_week': iso_week,
        'week_start': start,
        'week_end': end,
        'summary': stats['summary'],
        'days': stats['days'],
        'undone': undone,
    }


def build_next_week_data(uid: int, start: str) -> dict:
    """聚合下周（已设计/安排）数据，供周报“下周计划”部分使用。"""
    from datetime import date as _d, timedelta
    y, m, d = map(int, week_bounds(start)[0].split('-'))
    next_monday = (_d(y, m, d) + timedelta(days=7)).isoformat()
    next_sunday = (_d(y, m, d) + timedelta(days=13)).isoformat()
    stats = store.range_stats(uid, next_monday, next_sunday)
    planned = []
    for day in stats['days']:
        for t in day['tasks']:
            planned.append({'date': day['date'], 'title': t['title'], 'done': t['done'], 'priority': t['priority']})
    return {
        'week_start': next_monday,
        'week_end': next_sunday,
        'summary': stats['summary'],
        'planned': planned,
    }


def _iso_week(date_str: str) -> tuple[int, int, int]:
    from datetime import date as _d
    y, m, d = map(int, date_str.split('-'))
    return _d(y, m, d).isocalendar()


def build_prompt(week_data: dict, next_data: dict,
                 template_text: str | None = None, title: str = '') -> list:
    """构造周报生成的 messages。两大任务：本周已完成总结 + 下周计划总结。"""
    s = week_data['summary']
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
    planned_text = '、'.join(f"{p['title']}({p['date']})" for p in next_data['planned']) or '无'

    if template_text:
        # 有模板：章节结构完全以模板为准，禁止添加模板之外的任何内容
        system = (
            '你是一名资深的工作周报撰写助手。根据用户提供的一周任务数据与下周已安排任务，'
            '并完全依照用户提供的参考模板，输出周报正文。'
            '要求：1) 章节结构与模板完全一致：只输出模板中已有的段落/小节'
            '（如模板只有“本周周报”与“下周任务计划”两块，就只输出这两块），'
            '禁止添加模板中没有的内容（如本周概览、未完成与风险、总结评语等），禁止自行合并、新增或改名小节；'
            '2) 模板中的称呼、开头行、日期括号等行文格式照模板样式保留，但日期与条目等具体内容必须来自所给任务数据；'
            '3) 本周已完成任务整理进模板的本周部分，下周已安排任务整理进模板的下周计划部分；'
            '4) 若某部分没有对应数据（如下周没有已安排任务），该部分下只写“暂无”，不得自行编造或展开；'
            '5) 严格基于所给数据，不得编造数据中不存在的任务或事实；模板中的示例条目不要照抄；'
            '6) 所有行必须顶格书写：行首禁止制表符/空格等缩进（模板行首的不可见缩进字符是排版残留，不要模仿），'
            '否则正文会被 Markdown 渲染成代码块；'
            '7) 段落与条目之间保留一个空行即可，不要复制模板中的连续多个空行；'
            '8) 直接输出周报正文，不要额外解释。'
        )
    else:
        system = (
            '你是一名资深的工作周报撰写助手。根据用户提供的一周任务数据与下周已安排任务，输出 Markdown 格式周报。'
            '要求：1) 必须包含两大核心部分：【本周工作完成情况】（总结本周所有已完成的任务与产出）与【下周工作计划】（总结下周已经设计或安排的任务）；'
            '2) 可辅以【本周概览】【未完成与风险】等小节；'
            '3) 本周概览给出完成率与一句话总评；'
            '4) 严格基于所给数据，不得编造数据中不存在的任务或事实；'
            '5) 若下周没有已安排任务，【下周工作计划】下只写“暂无”；'
            '6) 直接输出 Markdown 正文，不要额外解释。'
        )
    user_parts = [
        f"周报标题：{title or '（自拟）'}",
        f"周期：{week_data['week_start']} ~ {week_data['week_end']}（{week_data['week_id']}）",
        f"统计：总任务 {s['total']}，已完成 {s['done']}，完成率 {round(s['rate']*100,1)}%",
        '本周按天明细：\n' + '\n'.join(lines),
        f"本周未完成任务清单：{undone_text}",
        f"下周（{next_data['week_start']} ~ {next_data['week_end']}）已安排任务：{planned_text}",
    ]
    if template_text:
        user_parts.append('参考模板如下：\n```markdown\n' + template_text + '\n```')
        user_parts.append(
            '请完全按照上面模板的段落结构输出：模板有的段落才输出，模板没有的内容一律不要出现；'
            '下周没有已安排任务时，下周部分只写“暂无”；'
            '所有行顶格书写、行首不要任何缩进；空行最多一个。'
        )
    return [{'role': 'system', 'content': system}, {'role': 'user', 'content': '\n'.join(user_parts)}]


def built_prompt(uid: int, start: str, template_name: str | None = None, author: str = '') -> dict:
    """按当前周/模板/署名构建默认 prompt（system/user 两段），供「提示词」弹窗展示。"""
    week_data = build_week_data(uid, start)
    next_data = build_next_week_data(uid, start)
    template_text = store.read_template(template_name) if template_name else None
    title = build_title(uid, week_data, author or None)
    msgs = build_prompt(week_data, next_data, template_text, title)
    return {'system': msgs[0]['content'], 'user': msgs[1]['content']}


def load_saved_prompt() -> dict | None:
    """返回用户保存的 prompt 草稿；从未保存过返回 None。"""
    p = store.load_settings().get('report_prompt') or {}
    system, user = str(p.get('system') or ''), str(p.get('user') or '')
    if not system and not user:
        return None
    return {'system': system, 'user': user}


def save_prompt(system: str, user: str) -> dict:
    """保存弹窗中编辑的 prompt 草稿到设置。"""
    saved = {'system': system, 'user': user}
    store.save_settings({'report_prompt': saved})
    return saved


def _cn_week(date_str: str) -> str:
    from datetime import datetime
    names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    try:
        return names[datetime.strptime(date_str, '%Y-%m-%d').weekday()]
    except Exception:
        return ''


def generate_stream(uid: int, start: str, model: str | None = None,
                    template_name: str | None = None, author: str = '',
                    prompt_override: dict | None = None) -> Iterator[str]:
    """流式生成周报文本；prompt_override 非空时按其原样执行，不再自动构建。"""
    settings = store.load_settings()
    ai_cfg = settings['ai']
    if not ai_cfg.get('api_key') and ai_cfg.get('provider') != 'ollama':
        raise ai.LLMError('尚未配置 AI API Key，请在「设置 → AI」中填写')
    week_data = build_week_data(uid, start)
    if week_data['summary']['total'] == 0:
        raise ai.LLMError('该周没有任何任务数据，无法生成周报')
    next_data = build_next_week_data(uid, start)
    template_text = store.read_template(template_name) if template_name else None
    title = build_title(uid, week_data, author or None)
    if prompt_override and (prompt_override.get('system') or prompt_override.get('user')):
        messages = [{'role': 'system', 'content': str(prompt_override.get('system') or '')},
                    {'role': 'user', 'content': str(prompt_override.get('user') or '')}]
    else:
        messages = build_prompt(week_data, next_data, template_text, title)
    use_model = model or ai_cfg['model']
    yield from ai.chat_stream(
        ai_cfg['base_url'], ai_cfg.get('api_key', ''), use_model, messages,
        temperature=float(ai_cfg.get('temperature', 0.7)),
        max_tokens=int(ai_cfg.get('max_tokens', 4096)),
    )


def build_title(uid: int, week_data: dict, author: str | None) -> str:
    """标题规则：xx年xx周周报[--NN]--署名；同一周多份时追加两位序号。"""
    iso_year = week_data['iso_year']
    iso_week = week_data['iso_week']
    base = f'{iso_year}年{iso_week}周周报'
    index = store.load_reports_index(uid)
    same = [r for r in index.get('reports', []) if r.get('week_id') == week_data['week_id']]
    seq = len(same) + 1
    suffix = f'{seq:02d}' if seq >= 2 else ''
    name = author or '未署名'
    return f'{base}{suffix}--{name}'


def save_report(uid: int, start: str, markdown: str, author: str = '',
                model: str | None = None) -> dict:
    """保存周报到 weekly_report_output/<uid>/ 并登记索引。返回记录。"""
    week_data = build_week_data(uid, start)
    week_id = week_data['week_id']
    # 秒级时间戳在同一周内可能碰撞（同周多份周报），追加短随机后缀保证 id/文件名唯一
    ts = f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    filename = f'weekly_report_{week_id}_{ts}.md'
    path = store.report_output_path(uid, filename)
    title = build_title(uid, week_data, author or None)
    header = f'<!-- generated_at: {time.strftime("%Y-%m-%dT%H:%M:%S")} | week: {week_id} | title: {title} -->\n\n'
    path.write_text(header + markdown, encoding='utf-8')
    settings = store.load_settings()
    s = week_data['summary']
    record = {
        'id': f'{week_id}_{ts}',
        'week_id': week_id,
        'title': title,
        'author': author or '',
        'week_start': week_data['week_start'],
        'week_end': week_data['week_end'],
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'model': model or settings['ai'].get('model'),
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
