"""Chinese Google News RSS search (the domestic source used by Jieli's digest).

This is deliberately one news pool, not a China/global split. Google News'
Chinese edition is used as a discovery layer; every item keeps its publisher and
original URL. The source can be disabled from settings if Google News is blocked.
"""
from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import quote

import feedparser

from .http import get, mark_sampled, parse_date_any, record_candidates, record_failure, record_query, strip_html
from ._discovery import fixed_bounds
from ..models import Item

BASE = "https://news.google.com/rss/search"
DEFAULT_QUERIES = (
    "脑科学 OR 神经科学",
    "脑机接口",
    "脑电 研究",
    "脑磁图",
    "功能磁共振",
    "神经影像",
)


def _query(opts: dict) -> str:
    queries = opts.get("queries") or opts.get("queries_zh") or opts.get("query") or DEFAULT_QUERIES
    if isinstance(queries, str):
        queries = [queries]
    return " OR ".join(f"({str(q).strip()})" for q in queries if str(q).strip())


def fetch(config, logger=None) -> list[Item]:
    opts = config.source_opts("google_news_zh")
    if opts.get("enabled", True) is False:
        return []
    query = _query(opts)
    if not query:
        return []
    lookback = max(1, int(opts.get("lookback_days", 2)))
    today = date.today()
    fixed = fixed_bounds(opts)
    cutoff, end = fixed or ((today - timedelta(days=lookback)).isoformat(), "9999-12-31")
    # This endpoint only has a relative lookback. Fetch far enough back to
    # reach the fixed start, then apply the original upper bound locally.
    request_days = max(lookback, (today - date.fromisoformat(cutoff)).days + 1) if fixed else lookback
    limit = max(1, int(opts.get("max_results", 100)))
    url = (BASE + "?" + "q=" + quote(f"{query} when:{request_days}d") +
           "&hl=zh-CN&gl=CN&ceid=CN:zh-Hans")
    record_query(f"Google News 中文 · {cutoff}–{end}" if fixed else f"Google News 中文 · {lookback} 天")
    response = get(url, timeout=20.0, retries=1, user_agent="Mozilla/5.0 NeuroDaily")
    if response is None:
        return []
    try:
        parsed = feedparser.parse(response.content)
    except Exception:
        record_failure("Google News 中文 RSS 解析失败")
        return []
    if not parsed.get("version"):
        record_failure("Google News 中文未返回有效 RSS")
        return []
    record_candidates(len(parsed.entries))
    items: list[Item] = []
    seen: set[str] = set()
    for entry in parsed.entries:
        title = strip_html(entry.get("title", ""))
        link = entry.get("link", "")
        if not title or not link or link in seen:
            continue
        seen.add(link)
        published = parse_date_any(entry.get("published") or entry.get("updated"))
        if published and not cutoff <= published <= end:
            continue
        source = strip_html(entry.get("source", {}).get("title", "") if isinstance(entry.get("source"), dict) else "")
        # Google News appends " - Publisher" to titles.
        if source and title.endswith(" - " + source):
            title = title[: -len(source) - 3].strip()
        summary = strip_html(entry.get("summary", ""))[:1000]
        items.append(Item(title=title, url=link, summary=summary, source="google_news_zh",
                          kind="news", date=published,
                          extra={"publisher": source, "feed": "Google News 中文",
                                 "query": query}))
        if len(items) >= limit:
            mark_sampled(truncated=True)
            break
    items.sort(key=lambda item: item.date, reverse=True)
    return items
