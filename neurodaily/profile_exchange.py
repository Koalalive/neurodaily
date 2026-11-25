"""Portable research profiles with a versioned format and no delivery settings."""
from __future__ import annotations

import re
from copy import deepcopy
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import Config, DEFAULT_CONFIG, RESEARCH_FIELDS
from .schema import validate

FORMAT = "neurodaily.profile"
VERSION = 1
MAX_BYTES = 256 * 1024
_FIELDS = RESEARCH_FIELDS
_SOURCE_FIELDS = {"enabled", "max_results", "lookback_days", "type", "url", "kind",
                  "items_path", "map", "filter_keywords", "query", "feed_kinds"}
_SECRET_QUERY_NAMES = {"key", "apikey", "accesstoken", "authtoken", "token", "auth",
                       "secret", "signature", "sig", "password", "credential", "jwt"}
_PORTABLE_WINDOWS = set(DEFAULT_CONFIG().windows)


def _url(value):
    if not isinstance(value, str) or not value:
        return value
    try:
        url = urlsplit(value)
    except ValueError:
        return ""
    if url.scheme.lower() not in ("https", "http") or not url.hostname:
        return ""
    safe_query = [
        (key, val) for key, val in parse_qsl(url.query, keep_blank_values=True)
        if re.sub(r"[^a-z]", "", key.lower()) not in _SECRET_QUERY_NAMES
        and not key.lower().startswith(("x-amz-", "x-goog-"))
    ]
    return urlunsplit((url.scheme, url.netloc.rsplit("@", 1)[-1], url.path,
                       urlencode(safe_query), ""))


def _portable(data: dict) -> dict:
    fields = {key: deepcopy(data[key]) for key in _FIELDS if key in data}
    if isinstance(fields.get("sources"), dict):
        for name, source in fields["sources"].items():
            if not isinstance(source, dict):
                continue
            fields["sources"][name] = {key: val for key, val in source.items() if key in _SOURCE_FIELDS}
            if "url" in source:
                fields["sources"][name]["url"] = _url(source["url"])
            if isinstance(source.get("feed_kinds"), dict):
                fields["sources"][name]["feed_kinds"] = {
                    _url(url): kind for url, kind in source["feed_kinds"].items()
                }
    if isinstance(fields.get("journals"), list):
        for item in fields["journals"]:
            if not isinstance(item, dict):
                continue
            for key in list(item):
                if key not in {"name", "url", "rss", "category", "impact_factor", "if", "jcr", "cas",
                               "metric_year", "year", "aliases", "issns", "impact_factor_year", "if_year",
                               "jcr_year", "cas_year", "cas_top", "sci", "ssci", "tags"}:
                    del item[key]
                elif key in ("url", "rss"):
                    item[key] = _url(item[key])
    if isinstance(fields.get("policy_feeds"), list):
        fields["policy_feeds"] = [_url(value) for value in fields["policy_feeds"]]
    if isinstance(fields.get("windows"), dict):
        fields["windows"] = {key: value for key, value in fields["windows"].items()
                             if key in _PORTABLE_WINDOWS}
    if isinstance(fields.get("disciplines"), list):
        fields["disciplines"] = [
            {key: value for key, value in row.items()
             if key in {"name", "enabled", "keywords", "mesh_terms", "arxiv_cats", "bio_cats"}}
            if isinstance(row, dict) else row for row in fields["disciplines"]
        ]
    return fields


def export_profile(config: Config) -> dict:
    return {"format": FORMAT, "version": VERSION, "config": _portable(config.to_dict())}


def restore_research_config(current: Config, document: dict) -> dict:
    """Restore portable rules and keep local options only at their current endpoint."""
    stored = _portable(document)
    current_feeds = {_url(url): url for url in current.policy_feeds}
    stored["policy_feeds"] = [current_feeds.get(url, url) for url in stored.get("policy_feeds", [])]
    for name, opts in stored.get("sources", {}).items():
        active = current.sources.get(name, {})
        if opts.get("type") == active.get("type") and opts.get("url") == _url(active.get("url")):
            opts.update({key: value for key, value in active.items() if key not in _SOURCE_FIELDS})
            if "url" in active:
                opts["url"] = active["url"]
        if isinstance(opts.get("feed_kinds"), dict):
            opts["feed_kinds"] = {current_feeds.get(url, url): kind for url, kind in opts["feed_kinds"].items()}
    active_journals = {journal.name: journal for journal in current.journals}
    for journal in stored.get("journals", []):
        active = active_journals.get(journal.get("name"))
        if active:
            for field in ("url", "rss"):
                value = getattr(active, field)
                if value and _url(value) == journal.get(field):
                    journal[field] = value
    return {**current.to_dict(), **stored}


def import_profile(document, current: Config) -> tuple[Config, dict]:
    if not isinstance(document, dict):
        raise ValueError("配置文件必须是 JSON 对象")
    if "format" in document:
        if document.get("format") != FORMAT or type(document.get("version")) is not int or document["version"] != VERSION:
            raise ValueError("不支持此配置文件格式或版本")
        data = document.get("config")
    else:
        version = document.get("version", 2)
        if type(version) is not int or version not in (1, 2):
            raise ValueError("不支持此旧版配置文件版本")
        data = document
    if not isinstance(data, dict) or not data.get("disciplines"):
        raise ValueError("配置文件需要至少一个学科")
    shared = _portable(data)
    defaults = DEFAULT_CONFIG().to_dict()
    merged = {**current.to_dict(), **{key: defaults[key] for key in _FIELDS}, **shared}
    errors = validate(merged)
    if errors:
        raise ValueError("；".join(errors[:5]))
    cfg = Config.from_dict(merged)
    return cfg, {"profile": cfg.profile, "disciplines": len(cfg.disciplines),
                 "sources": len(cfg.sources), "journals": len(cfg.journals),
                 "has_query": bool(cfg.search.get("query") or cfg.search.get("rules")),
                 "removed_private_fields": any(key not in _FIELDS and key != "version" for key in data)}
