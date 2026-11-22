"""Source registry: maps config key -> fetch function."""
from __future__ import annotations

from . import arxiv, biorxiv, europe_pmc, fda, gdelt, generic, journalpapers, nih_brain, openalex, pubmed, rss, trials

BUILTIN = {
    "journal": journalpapers.fetch,
    "arxiv": arxiv.fetch,
    "pubmed": pubmed.fetch,
    "biorxiv": biorxiv.fetch,
    "fda_drugs": fda.fetch_drugs,
    "fda_devices": fda.fetch_devices,
    "trials": trials.fetch,
    "policy": rss.fetch,
    "europe_pmc": europe_pmc.fetch,
    "openalex": openalex.fetch,
    "gdelt": gdelt.fetch,
    "nih_brain": nih_brain.fetch,
}

REGISTRY = BUILTIN


def _bound(fn, name):
    return lambda config, logger=None: fn(name, config, logger)


def registry_for(config) -> dict:
    """BUILTIN sources + any config-defined rss/json_api sources."""
    reg = dict(BUILTIN)
    for name, opts in (getattr(config, "sources", {}) or {}).items():
        if name in reg:
            continue
        t = (opts or {}).get("type")
        if t == "rss":
            reg[name] = _bound(generic.fetch_rss, name)
        elif t in ("json_api", "json"):
            reg[name] = _bound(generic.fetch_json, name)
    return reg


def fetch_source(name: str, config, logger=None):
    fn = REGISTRY.get(name)
    if fn is None or config.source_opts(name).get("enabled", True) is False:
        return []
    try:
        return fn(config, logger=logger)
    except Exception as e:  # noqa: BLE001 — sources must never crash the report
        if logger:
            logger.warning("source %s failed: %s", name, e)
        return []
