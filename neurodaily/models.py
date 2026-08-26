"""Shared data model: every source emits Items, digest consumes them."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Item:
    title: str
    url: str = ""
    summary: str = ""
    authors: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)   # institutions/units
    corresponding: list[str] = field(default_factory=list)  # corresponding/corresponding-author names
    source: str = "unknown"              # "arxiv" | "pubmed" | "biorxiv" | "fda_drugs" | ...
    kind: str = "paper"                  # "paper" | "drug" | "device" | "trial" | "news" | "policy"
    date: str = ""                       # ISO string, best-effort
    doi: str = ""
    tags: list[str] = field(default_factory=list)   # matched discipline/keyword tags
    extra: dict = field(default_factory=dict)        # source-specific fields

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def date_display(self) -> str:
        if not self.date:
            return ""
        try:
            d = datetime.fromisoformat(self.date.replace("Z", ""))
            return d.strftime("%Y-%m-%d")
        except ValueError:
            return self.date

    @property
    def author_display(self) -> str:
        """All authors, joined; truncate only very long lists."""
        if not self.authors:
            return ""
        return ", ".join(self.authors)

    @property
    def affiliation_display(self) -> str:
        if not self.affiliations:
            return ""
        if len(self.affiliations) == 1:
            return self.affiliations[0]
        # de-dup preserving order
        seen, out = set(), []
        for a in self.affiliations:
            if a and a not in seen:
                seen.add(a)
                out.append(a)
        if len(out) <= 2:
            return "; ".join(out)
        return "; ".join(out[:2]) + f" (+{len(out)-2})"

    @property
    def corresponding_display(self) -> str:
        if not self.corresponding:
            return ""
        return ", ".join(self.corresponding)

    @property
    def kind_label(self) -> str:
        return {
            "paper": "Paper",
            "drug": "Drug Approval",
            "device": "Device Clearance",
            "trial": "Clinical Trial",
            "news": "News",
            "policy": "Policy",
            "conference": "Conference",
        }.get(self.kind, "Item")


def tag_items(items: list[Item], config) -> list[Item]:
    """Attach discipline/keyword tags to each item based on the config focus."""
    import re as _re
    for it in items:
        hay = (it.title + " " + it.summary + " " + " ".join(it.tags)).lower()
        matched: list[str] = []
        for d in config.active_disciplines():
            if _dish_matches(d.name, hay):
                matched.append(d.name)
        for kw in config.all_keywords():
            if _whole_word(kw.lower(), hay) and kw not in matched:
                matched.append(kw)
        # Keep a source-flag tag (e.g. "top-journal") that tag_items must not wipe.
        flags = [t for t in it.tags if t in ("top-journal",)]
        it.tags = flags + (matched[:6] if matched else [])
    return items


def _dish_matches(name: str, hay: str) -> bool:
    n = name.lower()
    # direct substring, plus a couple of aliases
    if n in hay:
        return True
    alias = {
        "traumatic brain injury": ["tbi", "head injury", "concussion"],
        "addiction": ["substance use", "substance-use", "opioid", "drug use"],
        "epilepsy": ["seizure", "antiepileptic", "epileptic"],
        "psychiatry": ["psychiatric", "mental disorder", "depression", "anxiety"],
        "cognitive neuroscience": ["cognition", "working memory", "cognitive"],
    }.get(n, [])
    return any(a in hay for a in alias)


def _whole_word(word: str, hay: str) -> bool:
    if len(word) <= 2:
        return word in hay
    return bool(re.search(rf"\b{word}\b", hay))
