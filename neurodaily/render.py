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


def render_html(result: DigestResult, config: Config | None = None) -> str:
    env = _stdlib_loader()
    if env is None:
        return _fallback_plain(result)
    try:
        template = env.get_template("report.html.j2")
        ctx = {
            "result": result,
            "today": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        html = template.render(**ctx)
        return _inject_graph_links(_inject_on_this_day(html, result))
    except Exception:
        return _fallback_plain(result)


def _inject_on_this_day(html: str, result: DigestResult) -> str:
    events = getattr(result, "on_this_day", None) or []
    if not events:
        return html
    from .onthisday import render_section_html
    section = render_section_html(events)
    if not section:
        return html
    if "</main>" in html:
        return html.replace("</main>", section + "\n</main>", 1)
    if "</body>" in html:
        return html.replace("</body>", section + "\n</body>", 1)
    return html + section


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
