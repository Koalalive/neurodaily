"""Source registry: maps config key -> fetch function."""
from __future__ import annotations

from . import arxiv, pubmed, biorxiv, fda, trials, rss, journalpapers

REGISTRY = {
    "journal": journalpapers.fetch,
    "arxiv": arxiv.fetch,
    "pubmed": pubmed.fetch,
    "biorxiv": biorxiv.fetch,
    "fda_drugs": fda.fetch_drugs,
    "fda_devices": fda.fetch_devices,
    "trials": trials.fetch,
    "policy": rss.fetch,
}


def fetch_source(name: str, config, logger=None):
    fn = REGISTRY.get(name)
    if fn is None:
        return []
    try:
        return fn(config, logger=logger)
    except Exception as e:  # noqa: BLE001 — sources must never crash the report
        if logger:
            logger.warning("source %s failed: %s", name, e)
        return []
