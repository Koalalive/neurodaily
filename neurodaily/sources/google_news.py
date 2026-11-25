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
# Public, stable RSS fallbacks used only when Google News is unreachable.
FALLBACK_FEEDS = (
    "https://www.chinanews.com.cn/rss/scroll-news.xml",
    "https://www.sciencedaily.com/rss/mind_brain.xml",
    "https://www.sciencenews.org/topic/neuroscience/feed",
)
_FALLBACK_CN_KEYWORDS = (
    "脑科学", "神经科学", "脑机接口", "脑电", "脑磁图",
    "功能磁共振", "神经影像", "大脑", "神经", "精神",
)


def _query(opts: dict) -> str:
    queries = opts.get("queries") or opts.get("queries_zh") or opts.get("query") or DEFAULT_QUERIES
    if isinstance(queries, str):
        queries = [queries]
    return " OR ".join(f"({str(q).strip()})" for q in queries if str(q).strip())


def _fallback_news(config, opts, cutoff: str, end: str, limit: int) -> list[Item]:
    """Use public science RSS when Google News is blocked or empty.

    This is deliberately a public-feed fallback, not a browser scrape. The
    query's Chinese keywords are not meaningful on English science feeds, so
    the profile's global keywords are used for local relevance filtering.
    """
    feeds = opts.get("fallback_feeds") or FALLBACK_FEEDS
    if not isinstance(feeds, (list, tuple)):
        feeds = FALLBACK_FEEDS
    from ..security import validate_http_url

    # The fallback feeds are already neuroscience-specific. Do not require
    # the profile's narrow keyword set, or a valid feed can still yield zero.
    keywords = [str(k).casefold() for k in (opts.get("fallback_keywords") or []) if str(k).strip()]
    out: list[Item] = []
    seen: set[str] = set()
    for feed_url in feeds:
        if not isinstance(feed_url, str) or not feed_url.strip():
            continue
        feed_keywords = keywords
        if "chinanews.com.cn" in feed_url:
            feed_keywords = [term.casefold() for term in _FALLBACK_CN_KEYWORDS]
        try:
            validate_http_url(feed_url, resolve=False)
        except ValueError:
            continue
        # Built-in fallbacks are hardcoded trusted public feeds; user-supplied
        # feeds must pass through the SSRF transport.
        trusted = feed_url in FALLBACK_FEEDS
        response = get(feed_url, timeout=15.0, retries=1, user_agent="Mozilla/5.0 NeuroDaily",
                       untrusted_url=not trusted)
        if response is None:
            continue
        try:
            parsed = feedparser.parse(response.content)
        except Exception:
            continue
        if not parsed.get("version"):
            continue
        record_candidates(len(parsed.entries))
        for entry in parsed.entries:
            title = strip_html(entry.get("title", ""))
            link = entry.get("link", "")
            if not title or not link or link in seen:
                continue
            published = parse_date_any(entry.get("published") or entry.get("updated"))
            if published and not cutoff <= published <= end:
                continue
            summary = strip_html(entry.get("summary") or entry.get("description") or "")[:1000]
            hay = f"{title} {summary}".casefold()
            if feed_keywords and not any(keyword in hay for keyword in feed_keywords):
                continue
            seen.add(link)
            source = strip_html(entry.get("source", {}).get("title", "") if isinstance(entry.get("source"), dict) else "")
            if source and title.endswith(" - " + source):
                title = title[: -len(source) - 3].strip()
            out.append(Item(title=title, url=link, summary=summary, source="google_news_zh",
                            kind="news", date=published,
                            extra={"publisher": source, "feed": "公开新闻 RSS fallback",
                                   "query": "fallback", "fallback": True, "fallback_url": feed_url}))
            if len(out) >= limit:
                return out
    return out


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
        fallback = _fallback_news(config, opts, cutoff, end, limit)
        if fallback:
            record_failure("Google News 不可达，已使用公开 RSS fallback")
            return fallback
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
    if not items:
        fallback = _fallback_news(config, opts, cutoff, end, limit)
        if fallback:
            record_failure("Google News 无可解析结果，已使用公开 RSS fallback")
            return fallback
    return items
