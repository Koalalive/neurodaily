"""BRAIN Initiative releases selected from the official NIH News Releases feed."""

from datetime import date, timedelta
import re
from urllib.parse import urljoin, urlsplit

import feedparser

from ._discovery import date_value, fixed_bounds, http_url, int_option, text
from .http import get, mark_sampled, parse_date_any, record_candidates, record_failure, record_query, strip_html
from ..models import Item


BASE = "https://www.nih.gov/news-releases/feed.xml"
_BRAIN = re.compile(r"\b(?:BRAIN[\s-]+Initiative|Brain Research Through Advancing Innovative Neurotechnologies)\b", re.I)
_MAX_RESULTS = 100


def _published(entry) -> str:
    stamp = entry.get("published_parsed")
    if stamp:
        try:
            return date(stamp.tm_year, stamp.tm_mon, stamp.tm_mday).isoformat()
        except (AttributeError, ValueError):
            pass
    return date_value(parse_date_any(text(entry.get("published"))))


def fetch(config, logger=None) -> list[Item]:
    opts = config.source_opts("nih_brain")
    requested = int_option(opts.get("max_results"), 40)
    limit = requested
    cutoff = (date.today() - timedelta(days=min(int_option(opts.get("lookback_days"), 14), 365))).isoformat()
    start, end = fixed_bounds(opts) or (cutoff, "9999-12-31")
    query = text(opts.get("query")).casefold()
    record_query("NIH News Releases · BRAIN Initiative" + (f" · {query}" if query else ""))
    # no adapter-level item cap
    response = get(BASE, timeout=15, retries=1)
    if response is None:
        return []
    parsed = feedparser.parse(response.content)
    if not parsed.get("version"):
        record_failure("The NIH News Releases endpoint did not return a valid feed.")
        return []
    record_candidates(len(parsed.entries))

    seen = set()
    items = []
    for entry in parsed.entries:
        title = strip_html(text(entry.get("title")))
        ephemeral = strip_html(text(entry.get("summary")))
        searchable = title + " " + ephemeral
        if not title or not _BRAIN.search(searchable) or (query and query not in searchable.casefold()):
            continue
        raw_url = text(entry.get("link"))
        url = http_url(urljoin(BASE, raw_url)) if raw_url else ""
        domain = urlsplit(url).hostname or ""
        if not (domain == "nih.gov" or domain.endswith(".nih.gov")) or url in seen:
            continue
        published = _published(entry)
        if published and not start <= published <= end:
            continue
        if len(items) >= limit:
            mark_sampled(truncated=True)
            break
        seen.add(url)
        items.append(Item(title=title, url=url, date=published, source="nih_brain", kind="news",
                          extra={"feed": "NIH News Releases", "source_url": BASE, "publisher_domain": domain}))
    return items
