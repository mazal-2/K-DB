#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""md2card.py — markdown 转小红书笔记风卡片
用法: python md2card.py input.md output.html
markdown 约定:
  ---        分页（每页一个 <section>）
  # 大标题   页内主标题（首页为封面大标题）
  ## 小标题  页标题
  **xx**    马克笔黄色高亮
  > 引用    黄色提示卡
  - 列表 / | 表格 | 原生渲染
"""
import re, sys, html

PAPER_CSS = '''
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #ddd; font-family: "Noto Serif SC","SimSun","Source Han Serif SC",serif; }
  .poster {
    width: 1080px; height: 1440px;
    background-color: #fff;
    background-image:
      linear-gradient(rgba(160,160,160,.16) 1px, transparent 1px),
      linear-gradient(90deg, rgba(160,160,160,.16) 1px, transparent 1px);
    background-size: 42px 42px;
    padding: 90px 96px 64px;
    display: flex; flex-direction: column;
    color: #191919; overflow: hidden;
  }
  .poster + .poster { margin-top: 48px; }
  .tag-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 56px; }
  .tag { display:inline-block; background:#191919; color:#fff; font-size:24px; padding:8px 22px; letter-spacing:2px; }
  .pageno { font-size: 22px; color: #9a9a9a; letter-spacing: 2px; }
  h1 { font-size: 76px; line-height: 1.35; font-weight: 900; margin-bottom: 32px; letter-spacing: 2px; }
  h2 { font-size: 58px; line-height: 1.4; font-weight: 900; margin-bottom: 40px; letter-spacing: 2px; }
  h1 .u, h2 .u { background: linear-gradient(transparent 60%, #ffe45c 60%); }
  .sub { font-size: 32px; color: #555; line-height: 1.8; margin-bottom: 48px; }
  p.body, li, .t { font-size: 34px; line-height: 1.9; letter-spacing: 1px; }
  p.body + p.body { margin-top: 28px; }
  mark { background: #191919; color: #fff; padding: 6px 16px; font-weight: 700;
         -webkit-box-decoration-break: clone; box-decoration-break: clone; }
  .hl-blue { color: #191919; font-weight: 700; }
  .card { border: none; padding: 0; margin-top: 40px; background: transparent; }
  .card.blue { background: transparent; }
  .card .ct { font-size: 34px; font-weight: 900; margin-bottom: 16px; }
  .card.yellow { background: transparent; }
  code { background:#f0f0f0; padding:2px 12px; }
  ul { list-style: none; margin-top: 30px; }
  li { padding-left: 48px; position: relative; margin-bottom: 24px; }
  li::before { content: "—"; position: absolute; left: 0; color: #191919; }
  table { width: 100%; border-collapse: collapse; margin-top: 36px; }
  th { background: #191919; color: #fff; font-size: 28px; padding: 18px 20px; text-align: left; font-weight: 700; }
  td { font-size: 28px; padding: 17px 20px; border-bottom: 1px solid #ccc; line-height: 1.6; }
  tr:last-child td { border-bottom: none; }
  td.k { font-weight: 700; white-space: nowrap; }
  .step { display: flex; align-items: flex-start; gap: 26px; margin-top: 36px; }
  .step .n { flex:0 0 60px; height:60px; background:#191919; color:#fff; font-size:30px; font-weight:700;
             display:flex; align-items:center; justify-content:center; margin-top:6px; }
  .step .t b { font-weight: 900; }
  .arrow { display:none; }
  .footer { margin-top: auto; padding-top: 28px; border-top: 1px solid #bbb;
            display:flex; justify-content:space-between; font-size:22px; color:#9a9a9a; letter-spacing:2px; }
  .grow { flex: 1; }
  /* 金句框：左上/右下角标 */
  blockquote, .quote-box {
    margin-top: 48px; padding: 44px 40px; background: #f2f2ee;
    font-size: 38px; font-weight: 900; line-height: 1.75; position: relative;
  }
  blockquote::before, .quote-box::before { content: "「"; position:absolute; left:-6px; top:-34px;
    font-size:52px; font-weight:900; color:#191919; background:transparent; }
  blockquote::after, .quote-box::after { content: "」"; position:absolute; right:-6px; bottom:-40px;
    font-size:52px; font-weight:900; color:#191919; }
  .card.yellow { border:none; background:#f2f2ee; padding: 40px 40px; position:relative; margin-top: 48px; }
  .card.yellow::before { content:"「"; position:absolute; left:-6px; top:-36px; font-size:52px; font-weight:900; }
  .card.yellow::after { content:"」"; position:absolute; right:-6px; bottom:-42px; font-size:52px; font-weight:900; }
  .card.yellow .ct { font-size: 32px; margin-bottom: 14px; }
  .card.yellow p.body { font-size: 32px; }
'''

THEMES = {
  'note': None,  # 从 note-style.html 读取
  'paper': PAPER_CSS,
}

import re as _re
def get_css(theme):
    if theme == 'paper':
        return PAPER_CSS
    CSS = open('note-style.html', encoding='utf-8').read()
    return _re.search(r'<style>(.*?)</style>', CSS, re.S).group(1)

MD = open(sys.argv[1], encoding='utf-8').read()
THEME = sys.argv[3] if len(sys.argv) > 3 else 'note'
OUT_CSS = get_css(THEME)

def inline(s):
    s = html.escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<mark>\1</mark>', s)          # **xx** → 高亮
    s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)
    s = re.sub(r'((?:https?://|www\.)[^\s）)】]*)', r'<span class="hl-blue">\1</span>', s)
    return s

def parse_table(lines):
    rows = [l for l in lines if l.strip().startswith('|')]
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    cells = [r for r in cells if not all(re.match(r'^:?-+:?$', c) for c in r if c)]  # 去分隔行
    if not cells: return ''
    head = cells[0]; body = cells[1:]
    t = '<table><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr>'
    for r in body:
        k = f'<td class="k">{inline(r[0])}</td>'
        t += '<tr>' + k + ''.join(f'<td>{inline(c)}</td>' for c in r[1:]) + '</tr>'
    return t + '</table>'

def parse_page(lines, idx, total):
    out, i = [], 0
    is_cover = (idx == 1)
    while i < len(lines):
        l = lines[i].rstrip()
        if not l.strip(): i += 1; continue
        if l.startswith('|'):
            j = i
            while j < len(lines) and lines[j].strip().startswith('|'): j += 1
            out.append(parse_table(lines[i:j])); i = j; continue
        if l.startswith('> '):
            out.append(f'<div class="card yellow"><p class="body">{inline(l[2:])}</p></div>'); i += 1; continue
        if l.strip() == ':::':
            i += 1; continue
        if l.startswith(':::'):
            cls = 'card blue' if 'blue' in l else 'card'
            j = i + 1; buf = []
            while j < len(lines) and not lines[j].startswith(':::'):
                buf.append(lines[j].strip()); j += 1
            if len(buf) == 1:
                out.append(f'<div class="{cls}"><p class="body">{inline(buf[0])}</p></div>')
            else:
                out.append(f'<div class="{cls}"><div class="ct">{inline(buf[0].lstrip("# ") if buf else "")}</div>' +
                           ''.join(f'<p class="body">{inline(b)}</p>' for b in buf[1:]) + '</div>')
            i = j + 1; continue
        if l.startswith('# '):
            out.append(f'<h1>{inline(l[2:])}</h1>')
        elif l.startswith('## '):
            out.append(f'<h2>{inline(l[3:])}</h2>')
        elif l.startswith('### '):
            out.append(f'<p class="body" style="font-weight:700;color:#2f5cff;margin-top:24px">{inline(l[4:])}</p>')
        elif l.startswith('- '):
            out.append('<ul>' + ''.join(f'<li>{inline(x[2:])}</li>' for x in lines[i:] if x.startswith('- ')))
            while i < len(lines) and lines[i].startswith('- '): i += 1
            out.append('</ul>'); continue
        elif re.match(r'^\d+\.\s', l):
            out.append(f'<div class="step"><div class="n">{l.split(".")[0]}</div><div class="t">{inline(l.split(". ",1)[1])}</div></div>')
        else:
            out.append(f'<p class="body">{inline(l)}</p>')
        i += 1
    tag = '封面' if is_cover else '干货'
    return f'''<section class="poster" id="p{idx}">
  <div class="tag-row"><span class="tag">{TAG}</span><span class="pageno">{idx:02d} / {total:02d}</span></div>
  {chr(10).join(out)}
  <div class="footer"><span>{FOOTER_L}</span><span>{FOOTER_R}</span></div>
</section>'''

# ---- 配置区：可在 md 首行用 <!-- TAG: x | L: y | R: z --> 覆盖 ----
TAG, FOOTER_L, FOOTER_R = '产品方法论', '策略产品经理 · 入门', '关注看全系列'
_m = re.match(r'\s*<!--\s*TAG:\s*(.+?)\s*(?:\|\s*L:\s*(.+?)\s*)?(?:\|\s*R:\s*(.+?)\s*)?-->', MD)
if _m:
    TAG = _m.group(1).strip()
    FOOTER_L = (_m.group(2) or FOOTER_L).strip()
    FOOTER_R = (_m.group(3) or FOOTER_R).strip()
    MD = MD[_m.end():]

pages_raw = [p.split('\n') for p in MD.split('\n---\n') if p.strip()]
total = len(pages_raw)
sections = ''.join(parse_page(p, i+1, total) for i, p in enumerate(pages_raw))

HTML = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>md2card</title><style>{OUT_CSS}
h1 .u, h2 .u {{ background: linear-gradient(transparent 62%, #ffe45c 62%); }}
code {{ background:#eef2ff; color:#2f5cff; padding:2px 10px; border-radius:6px; font-size:0.9em; }}
</style></head><body>
{sections}
<script>
const m = location.hash.match(/^#p(\\d+)$/);
if (m) {{
  document.querySelectorAll('.poster').forEach(p => {{ if (p.id !== 'p' + m[1]) p.style.display = 'none'; }});
  document.body.style.background = '#fffdf8'; window.scrollTo(0, 0);
}}
</script></body></html>'''

open(sys.argv[2], 'w', encoding='utf-8').write(HTML)
print(f'ok: {total} pages -> {sys.argv[2]}')
