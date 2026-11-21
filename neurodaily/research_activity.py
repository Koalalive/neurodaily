"""Build the daily geography and keyword views from a single set of records."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from .config import DEFAULT_DIRS
from .digest import DigestResult
from .models import Item
from .records import record_ids

_MAP_KINDS = {"paper", "trial", "news", "policy"}


def _index(items: list[Item]) -> dict[str, Item]:
    result = {}
    for item in items:
        identifiers = item.extra.get("record_ids") or record_ids(item)
        result.setdefault(identifiers[0], item)
    return result


def _mapped(items: dict[str, Item]) -> dict[str, Item]:
    return {record_id: item for record_id, item in items.items() if item.kind in _MAP_KINDS}


@lru_cache(maxsize=1)
def _land() -> list:
    return json.loads(files("neurodaily").joinpath("data", "natural_earth_land.json").read_text(encoding="utf-8"))


def enrich_geography(result: DigestResult) -> bool:
    """Optionally resolve ambiguous locations during a real run, before delivery."""
    from . import ai_summary, api_billing
    from .geography import locate_items

    if result.skipped or not result.items or not api_billing.load_settings()["geo_enabled"]:
        return False
    cfg = ai_summary.load_cfg()
    if not cfg.get("enabled"):
        return False
    key = ai_summary.api_key(cfg)
    if not key:
        return False
    base = ai_summary._api_base(cfg["base_url"])
    model = cfg["model"]
    cache_key = hashlib.sha256(json.dumps([base, model]).encode()).hexdigest()
    cache_dir = Path(DEFAULT_DIRS["output"], "geography_cache", cache_key)

    def chat(messages, max_tokens):
        return ai_summary._chat_request(base, model, key, messages, max_tokens, 35,
                                       purpose="geolocation", run_id=result.history_id or None,
                                       profile=result.config_profile, temperature=0)

    result.geography = locate_items(_mapped(_index(result.items)), chat=chat, cache_dir=cache_dir)
    return True


def report_activity(result: DigestResult, config, external_url) -> dict:
    from .geography import locate_items
    from .keywords import keyword_cloud

    items = _index(result.items)
    mapped = _mapped(items)
    geo = result.geography if result.geography is not None else locate_items(mapped)
    places = [place for place in geo["places"] if place["id"] in mapped]
    covered = {place["id"] for place in places}
    return {
        "land": _land() if mapped else [],
        "places": places,
        "unknown": [record_id for record_id in mapped if record_id not in covered],
        "deferred": [record_id for record_id in geo.get("deferred", []) if record_id in mapped],
        "keywords": keyword_cloud(items, config),
        "records": {
            record_id: {
                "title": item.title, "source": item.source, "kind": item.kind,
                "date": item.date_display, "url": external_url(item.url),
                "summary": " ".join((item.summary or "").split())[:240].strip(),
            } for record_id, item in items.items()
        },
    }
