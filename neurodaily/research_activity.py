"""Build the daily research map from the report's records."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
import hashlib
import json
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from .config import DEFAULT_DIRS
from .digest import DigestResult
from .geography import locate_items
from .models import Item
from .records import normalize_doi, record_ids

def _index(result: DigestResult) -> dict[str, tuple[str, Item]]:
    indexed = {}
    for category, items in result.report_categories().items():
        for item in items:
            identifiers = item.extra.get("record_ids") or record_ids(item)
            record_id = identifiers[0]
            if record_id in indexed:
                record_id = f"{item.kind}:{record_id}"
                if record_id in indexed:
                    record_id = f"{record_id}:{len(indexed)}"
            indexed[record_id] = (category, item)
    return indexed


@lru_cache(maxsize=1)
def _land() -> list:
    return json.loads(files("neurodaily").joinpath("data", "natural_earth_land.json").read_text(encoding="utf-8"))


def enrich_geography(result: DigestResult) -> bool:
    """Optionally resolve ambiguous locations during a real run, before delivery."""
    from . import ai_summary, api_billing

    settings = api_billing.load_settings()
    if result.skipped or not result.items or not settings["geo_enabled"]:
        return False
    cfg = ai_summary.load_cfg()
    # Summary and map have independent switches; the map only needs a key.
    key = ai_summary.api_key(cfg)
    if not key:
        return False
    base = ai_summary._api_base(cfg["base_url"])
    model = cfg["model"]
    cache_key = hashlib.sha256(json.dumps([base, model]).encode()).hexdigest()
    cache_dir = Path(DEFAULT_DIRS["output"], "geography_cache", cache_key)
    concurrency = max(1, min(16, int(settings.get("geo_concurrency") or 4)))
    mapped = _index(result)
    # News/policy feeds often carry only a headline. Fetch the article text so the
    # geolocation model can trace the event location instead of leaving it unknown.
    try:
        from .sources.http import get as _get, strip_html as _strip_html
        candidates = [item for _, item in mapped.values()
                      if item.kind in {"news", "policy", "funding", "drug", "device"} and item.url
                      and not item.extra.get("article_text")][:24]

        def fetch_article_text(item):
            try:
                response = _get(item.url, timeout=8.0, retries=0,
                                user_agent="Mozilla/5.0 NeuroDaily", untrusted_url=True)
                if response is not None:
                    text = _strip_html(response.text)
                    if text:
                        item.extra["article_text"] = text[:4000]
            except Exception:
                return

        if candidates:
            with ThreadPoolExecutor(max_workers=min(4, len(candidates)),
                                    thread_name_prefix="geo-article") as pool:
                list(pool.map(copy_context().run, [lambda item=item: fetch_article_text(item)
                                                   for item in candidates]))
    except Exception:
        pass

    if result.config:
        # Affiliation lookup is metadata enrichment, not a literature source.
        # Do it even when Europe PMC is not enabled as a feed, otherwise papers
        # with a DOI but no affiliation remain permanently unlocated.
        from .sources.europe_pmc import last_author_metadata

        missing = [item for item in result.items if item.kind == "paper"
                   and not item.extra.get("last_author_affiliations") and item.doi][:120]
        dois = list(dict.fromkeys(normalize_doi(item.doi) for item in missing if normalize_doi(item.doi)))
        found = last_author_metadata(dois)
        for item in missing:
            if addresses := found.get(normalize_doi(item.doi)):
                item.extra["last_author_affiliations"] = [{**address, "source": "Europe PMC"} for address in addresses]

    def chat(messages, max_tokens):
        return ai_summary._chat_request(base, model, key, messages, max_tokens, 35,
                                       purpose="geolocation", run_id=result.history_id or None,
                                       profile=result.config_profile, temperature=0)

    # Process the full candidate set for a real report. The low-level helper keeps
    # its small default for callers that want a bounded preview.
    result.geography = locate_items({key: item for key, (_, item) in mapped.items()}, chat=chat,
                                    cache_dir=cache_dir, max_model_items=400,
                                    batch_size=6, concurrency=concurrency)
    return True


def report_activity(result: DigestResult, external_url) -> dict:
    mapped = _index(result)
    geo = result.geography
    if geo is None:
        geo = locate_items({key: item for key, (_, item) in mapped.items()})
    places = [place for place in geo["places"] if place["id"] in mapped]
    covered = {place["id"] for place in places}
    return {
        "enabled": True,
        "land": _land() if mapped else [],
        "places": places,
        "unknown": [record_id for record_id in mapped if record_id not in covered],
        "deferred": [record_id for record_id in geo.get("deferred", []) if record_id in mapped],
        "order": list(mapped),
        "records": {
            record_id: {
                "title": item.title, "source": item.source, "kind": item.kind, "category": category,
                "journal": (item.extra.get("journal") if item.kind == "paper" else "") or "",
                "venue": (item.extra.get("journal") if item.kind == "paper" else
                          (item.extra.get("feed") or item.source)),
                "date": item.date_display, "url": external_url(item.url),
                "summary": " ".join((item.summary or "").split())[:240].strip(),
            } for record_id, (category, item) in mapped.items()
        },
    }
