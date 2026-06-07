import logging
import os
from datetime import datetime
from textwrap import shorten

from .config import OUTPUT_DIR, CATEGORIES

OUTPUT_DIR = os.path.abspath(OUTPUT_DIR)

logger = logging.getLogger(__name__)


def write_markdown(items: dict[str, list[dict]]) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    filepath = os.path.join(OUTPUT_DIR, f'news_{today}.md')

    lines = []
    lines.append(f'# 每日新闻速递 — {today}')
    lines.append('')
    lines.append(f'共收录 **{sum(len(v) for v in items.values())}** 条新闻')
    lines.append('')

    toc = ['## 目录', '']
    for cat in items:
        if items[cat]:
            toc.append(f'- [{cat}](#{cat})')
    toc.append('')
    lines.extend(toc)

    for category in items:
        if not items[category]:
            continue
        icon = CATEGORIES.get(category, {}).get('icon', '')
        lines.append(f'---')
        lines.append(f'## {icon} {category}  ({len(items[category])} 条)')
        lines.append('')

        for i, item in enumerate(items[category], 1):
            title = item['title']
            link = item['link']
            summary = shorten(item.get('summary', ''), width=200, placeholder='...')
            source = item.get('source', '')
            pub = item.get('published', '')

            lines.append(f'**{i}. [{title}]({link})**')
            lines.append(f'> {pub} · {source}')
            if summary:
                lines.append(f'> {summary}')
            lines.append('')

    content = '\n'.join(lines)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info(f'Markdown written to {filepath}')
    return filepath


def write_html(items: dict[str, list[dict]]) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    filepath = os.path.join(OUTPUT_DIR, f'news_{today}.html')

    total = sum(len(v) for v in items.values())
    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="zh-CN">',
        '<head>',
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f'<title>每日新闻速递 — {today}</title>',
        '<style>',
        'body { font-family: "Segoe UI", system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; color: #333; }',
        'h1 { text-align: center; color: #1a1a1a; }',
        'h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; margin-top: 30px; }',
        '.item { background: #fff; border-radius: 8px; padding: 12px 16px; margin: 8px 0; box-shadow: 0 1px 3px rgba(0,0,0,.1); }',
        '.item a { font-weight: 600; color: #2c3e50; text-decoration: none; }',
        '.item a:hover { color: #3498db; }',
        '.meta { font-size: .85em; color: #888; margin-top: 4px; }',
        '.summary { font-size: .9em; color: #555; margin-top: 4px; }',
        '.toc { background: #fff; border-radius: 8px; padding: 12px 20px; margin: 20px 0; }',
        '.toc a { color: #3498db; }',
        '.footer { text-align: center; color: #aaa; font-size: .85em; margin-top: 40px; }',
        '</style>',
        '</head>',
        '<body>',
        f'<h1>每日新闻速递 — {today}</h1>',
        f'<p style="text-align:center;">共收录 <strong>{total}</strong> 条新闻</p>',
        '<div class="toc"><strong>目录</strong><ul>',
    ]

    for cat in items:
        if items[cat]:
            html_parts.append(f'<li><a href="#{cat}">{cat}</a></li>')
    html_parts.append('</ul></div>')

    for category in items:
        if not items[category]:
            continue
        icon = CATEGORIES.get(category, {}).get('icon', '')
        html_parts.append(f'<h2 id="{category}">{icon} {category} ({len(items[category])} 条)</h2>')

        for i, item in enumerate(items[category], 1):
            title = item['title']
            link = item['link']
            summary = shorten(item.get('summary', ''), width=200, placeholder='...')
            source = item.get('source', '')
            pub = item.get('published', '')

            html_parts.append('<div class="item">')
            html_parts.append(f'<div><strong>{i}.</strong> <a href="{link}" target="_blank">{title}</a></div>')
            html_parts.append(f'<div class="meta">{pub} · {source}</div>')
            if summary:
                html_parts.append(f'<div class="summary">{summary}</div>')
            html_parts.append('</div>')

    html_parts.append(f'<div class="footer">Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>')
    html_parts.append('</body></html>')

    content = '\n'.join(html_parts)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info(f'HTML written to {filepath}')
    return filepath
