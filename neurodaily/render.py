"""Render a DigestResult to a self-contained HTML report using Jinja2."""
from __future__ import annotations

import os
from datetime import datetime

from .config import Config, DEFAULT_CONFIG
from .digest import DigestResult

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _stdlib_loader():
    try:
        from jinja2 import Environment, FileSystemLoader
        return Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    except ImportError:
        return None


_LINK_RE = r"\[([^\]]+)\]\(([^)\s]+)\)"


def render_ai_inline(text: str, allowed_urls=None, refs=None) -> str:
    """Escape text but turn Markdown links into anchors (validated against allowed URLs)."""
    import html as _html
    import re
    allowed = None if allowed_urls is None else {u.rstrip("/") for u in allowed_urls if u}
    refs = refs or {}
    parts, pos = [], 0
    for m in re.finditer(_LINK_RE, text or ""):
        parts.append(_html.escape(text[pos:m.start()]))
        label, target = m.group(1), m.group(2)
        if not label.strip():
            pos = m.end()
            continue
        url = (refs.get(target) or {}).get("url") if target in refs else target
        ok = bool(url) and (url.startswith(("http://", "https://"))
              and (allowed is None or url.rstrip("/") in allowed))
        if ok:
            parts.append(
                f'<a href="{_html.escape(url, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer">{_html.escape(label)}</a>'
            )
        else:
            parts.append(_html.escape(label))
        pos = m.end()
    parts.append(_html.escape(text[pos:]))
    return "".join(parts)


def render_ai_text(text: str, allowed_urls=None, refs=None) -> str:
    out = []
    for line in (text or "").splitlines():
        s = line.strip().replace("**", "")
        if not s:
            continue
        bullet = s.startswith(("- ", "• ", "* "))
        if bullet:
            s = s[2:].strip()
        out.append(f'<p class="summary">{"• " if bullet else ""}{render_ai_inline(s, allowed_urls, refs)}</p>')
    return "".join(out)


def ai_links_to_text(text: str) -> str:
    import re
    return re.sub(_LINK_RE, r"\1 (\2)", text or "")


def render_html(result: DigestResult, config: Config | None = None) -> str:
    env = _stdlib_loader()
    if env is None:
        return _fallback_plain(result)
    try:
        from . import journal_metrics
        _cfg = config or getattr(result, "config", None)
        env.globals["jm"] = lambda name: journal_metrics.lookup(name, _cfg)
        template = env.get_template("report.html.j2")
        ctx = {
            "result": result,
            "today": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        html = template.render(**ctx)
        html = _inject_on_this_day(html, result)
        html = _inject_ai_summary(html, result)
        return _inject_graph_links(html)
    except Exception:
        return _fallback_plain(result)


def _inject_ai_summary(html: str, result: DigestResult) -> str:
    text = (getattr(result, "ai_summary", "") or "").strip()
    if not text:
        return html
    try:
        from .ai_summary import _clean_summary
        text = _clean_summary(text, getattr(result, 'ai_summary_refs', {}) or {})
    except Exception:
        pass
    import html as _html
    meta = getattr(result, "ai_summary_meta", {}) or {}
    model = _html.escape(str(meta.get("model", "AI")))
    allowed = {it.url for it in (getattr(result, "items", None) or []) if getattr(it, "url", None)}
    refs = getattr(result, "ai_summary_refs", {}) or {}
    allowed |= {(v or {}).get("url") for v in refs.values() if (v or {}).get("url")}
    paras = render_ai_text(text, allowed, refs)
    section = (
        '<section id="ai-summary"><div class="sec-head"><div>'
        f'<h2 class="sec-title"><span class="dot"></span>🧠 今日 AI 摘要'
        f'<span class="count">({model})</span></h2>'
        '<p class="sec-desc">由 AI 依据当日抓取内容生成，仅供参考；请以原文为准。</p>'
        '</div></div>'
        f'<div class="card" style="padding:14px 18px"><div class="card-body">{paras}</div></div>'
        '</section>'
    )
    for marker in ('<main class="wrap">', "<main>", "<main "):
        if marker in html:
            return html.replace(marker, marker + "\n" + section, 1)
    return section + html


def _inject_on_this_day(html: str, result: DigestResult) -> str:
    events = getattr(result, "on_this_day", None) or []
    if not events:
        return html
    from .onthisday import render_section_html
    section = render_section_html(events, lang=getattr(result, "on_this_day_lang", "zh"))
    if not section:
        return html
    for marker in ('<main class="wrap">', "<main>", "<main "):
        if marker in html:
            return html.replace(marker, marker + "\n" + section, 1)
    if "</body>" in html:
        return html.replace("</body>", section + "\n</body>", 1)
    return section + html


_GRAPH_JS = r"""
<style>
.card .graph-menu{margin-top:6px;font-size:.78rem}
.card .graph-menu summary{cursor:pointer;color:#38bdf8;list-style:none;display:inline-block}
.card .graph-menu summary::-webkit-details-marker{display:none}
.card .graph-menu a{display:inline-block;margin:6px 10px 0 0;color:#818cf8;text-decoration:none}
.card .graph-menu a:hover{text-decoration:underline}
</style>
<script>
(function(){
  function getDoi(card){
    var tags=card.querySelectorAll('.meta .tag');
    for(var i=0;i<tags.length;i++){
      var x=(tags[i].textContent||'').trim();
      if(x.indexOf('doi:')===0) return x.slice(4).trim();
    }
    var a=card.querySelector('.card-main h3 a');
    if(a){
      var h=a.getAttribute('href')||'';
      var m=h.match(/doi\.org\/(10\.[^\s?#]+)/i);
      if(m) return m[1];
      if(h) return h;
    }
    return '';
  }
  function addMenu(card){
    if(card.classList.contains('otd-card')) return;
    if(card.querySelector('.graph-menu')) return;
    var h3=card.querySelector('.card-main h3');
    if(!h3) return;
    var title=(h3.textContent||'').trim();
    var key=getDoi(card);
    var links=[['Connected Papers','https://www.connectedpapers.com/search?q='+encodeURIComponent(key||title)]];
    if(key && key.indexOf('10.')===0){
      links.push(['OpenAlex','https://openalex.org/works/doi:'+encodeURIComponent(key)]);
    }else{
      links.push(['OpenAlex','https://openalex.org/works?search='+encodeURIComponent(title)]);
    }
    links.push(['Semantic Scholar','https://www.semanticscholar.org/search?q='+encodeURIComponent(key||title)]);
    links.push(['本地引用网络','https://localcitationnetwork.github.io/']);
    var det=document.createElement('details');
    det.className='graph-menu';
    var sum=document.createElement('summary');
    sum.textContent='🕸 图谱';
    det.appendChild(sum);
    links.forEach(function(pair){
      var a=document.createElement('a');
      a.href=pair[1];a.target='_blank';a.rel='noopener';a.textContent=pair[0];
      det.appendChild(a);
    });
    var host=card.querySelector('.card-body .foot')||card.querySelector('.card-body')||card.querySelector('.card-main');
    if(host) host.appendChild(det);
  }
  function run(){
    var cards=document.querySelectorAll('details.card');
    for(var i=0;i<cards.length;i++) addMenu(cards[i]);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',run);
  else run();
})();
</script>
"""


def _inject_graph_links(html: str) -> str:
    if "</body>" in html:
        return html.replace("</body>", _GRAPH_JS + "\n</body>", 1)
    return html + _GRAPH_JS


def _fallback_plain(result: DigestResult) -> str:
    """Minimal but readable HTML if Jinja2 is unavailable."""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    for it in result.items:
        rows.append(
            f"<li>[{it.kind_label}][{it.source}] <b>{it.title}</b> "
            f"({it.date_display})<br>{it.summary[:300]}</li>"
        )
    health = "<br>".join(
        f"{h['source']}: {'ok' if h['ok'] else 'failed'} ({h['count']})"
        for h in result.health
    )
    return (
        f"<html><head><meta charset='utf-8'><title>NeuroDaily</title></head><body>"
        f"<h1>NeuroDaily — {today}</h1><p>{len(result.items)} items</p>"
        f"<ul>{''.join(rows)}</ul><hr><h2>Health</h2>{health}</body></html>"
    )
