"""Config: disciplines + keywords, serialized as a structured prompt.

The whole point of this module: the user configures their FOCUS (disciplines)
and KEYWORDS once, and the app turns it into:
  1. concrete per-source queries (arXiv categories, PubMed MeSH terms, ...)
  2. a STRUCTURED PROMPT string (``to_prompt()``) that captures the focus.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any

DEFAULT_DIRS = {
    "config": os.path.join(os.path.expanduser("~"), "neurodaily", "config"),
    "output": os.path.join(os.path.expanduser("~"), "neurodaily", "output"),
}


# ---------------------------------------------------------------------------
# Discipline model
# ---------------------------------------------------------------------------
@dataclass
class Discipline:
    name: str                      # human name, e.g. "Neuroscience"
    arxiv_cats: list[str] = field(default_factory=list)
    mesh_terms: list[str] = field(default_factory=list)     # PubMed [MeSH] terms
    bio_cats: list[str] = field(default_factory=list)       # bioRxiv category slugs
    keywords: list[str] = field(default_factory=list)       # extra free-text keywords
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Discipline":
        return Discipline(
            name=d["name"],
            arxiv_cats=list(d.get("arxiv_cats", [])),
            mesh_terms=list(d.get("mesh_terms", [])),
            bio_cats=list(d.get("bio_cats", [])),
            keywords=list(d.get("keywords", [])),
            enabled=bool(d.get("enabled", True)),
        )


# ---------------------------------------------------------------------------
# Journal model (top journals for quick reference / RSS)
# ---------------------------------------------------------------------------
@dataclass
class Journal:
    name: str                       # e.g. "Neuron"
    url: str = ""                   # official site
    rss: str = ""                   # optional RSS feed
    category: str = "neuroscience"  # grouping label in the UI

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Journal":
        return Journal(
            name=d["name"],
            url=d.get("url", ""),
            rss=d.get("rss", ""),
            category=d.get("category", "neuroscience"),
        )


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
@dataclass
class Config:
    profile: str
    disciplines: list[Discipline]
    global_keywords: list[str]                     # apply across all sources
    sources: dict[str, dict]                       # per-source options
    output: dict[str, Any]
    scheduled: dict[str, Any]
    policy_feeds: list[str] = field(default_factory=list)   # RSS/news/policy URLs
    journals: list[Journal] = field(default_factory=list)   # top journals

    # --------------------------------------------------------------- load
    @staticmethod
    def load(path: str | None = None) -> "Config":
        """Load from a JSON file; if absent, return DEFAULT_CONFIG."""
        p = path or os.path.join(DEFAULT_DIRS["config"], "config.json")
        if not os.path.exists(p):
            return DEFAULT_CONFIG()
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Migrate: newer fields (journals) missing from an existing config are
        # filled from defaults so upgrades keep working without manual edits.
        if "journals" not in data:
            data["journals"] = [j.to_dict() for j in DEFAULT_CONFIG().journals]
        return Config(
            profile=data.get("profile", "neuro"),
            disciplines=[Discipline.from_dict(d) for d in data.get("disciplines", [])],
            global_keywords=list(data.get("global_keywords", [])),
            sources=dict(data.get("sources", {})),
            output=dict(data.get("output", {})),
            scheduled=dict(data.get("scheduled", {})),
            policy_feeds=list(data.get("policy_feeds", [])),
            journals=[Journal.from_dict(j) for j in data.get("journals", [])],
        )

    def save(self, path: str | None = None) -> str:
        p = path or self.default_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return p

    # ------------------------------------------------------------- accessors
    @staticmethod
    def default_path() -> str:
        return os.path.join(DEFAULT_DIRS["config"], "config.json")

    def to_dict(self) -> dict:
        return {
            "profile": self.profile,
            "disciplines": [d.to_dict() for d in self.disciplines],
            "global_keywords": self.global_keywords,
            "sources": self.sources,
            "output": self.output,
            "scheduled": self.scheduled,
            "policy_feeds": self.policy_feeds,
            "journals": [j.to_dict() for j in self.journals],
        }

    def output_dir(self) -> str:
        return self.output.get("dir", DEFAULT_DIRS["output"])

    # ----------------------------------------------------- derived queries
    def active_disciplines(self) -> list[Discipline]:
        return [d for d in self.disciplines if d.enabled]

    def all_keywords(self) -> list[str]:
        """global keywords + per-discipline keywords, de-duplicated."""
        kws: list[str] = []
        for d in self.disciplines:
            kws.extend(d.keywords)
        kws.extend(self.global_keywords)
        seen, out = set(), []
        for k in kws:
            k = k.strip()
            if k and k.lower() not in seen:
                seen.add(k.lower())
                out.append(k)
        return out

    def all_arxiv_cats(self) -> list[str]:
        cats: list[str] = []
        for d in self.disciplines:
            cats.extend(d.arxiv_cats)
        # de-dup preserving order
        seen, out = set(), []
        for c in cats:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    def all_mesh_terms(self) -> list[str]:
        terms: list[str] = []
        for d in self.disciplines:
            terms.extend(d.mesh_terms)
        seen, out = set(), []
        for t in terms:
            if t and t.lower() not in seen:
                seen.add(t.lower())
                out.append(t)
        return out

    def source_opts(self, name: str) -> dict:
        return dict(self.sources.get(name, {}))

    # ------------------------------------------------------ structured prompt
    def to_prompt(self) -> str:
        """Render the config into a STANDARDIZED STRUCTURED PROMPT.

        This is the deliverable the user asked for: 一段结构化提示词 that captures
        their disciplines, keywords, and per-source query intent, so it can be
        reused by an LLM, a digest engine, or humans.
        """
        lines = [
            f"# NeuroDaily Focus Prompt (profile: {self.profile})",
            "",
            "## Mission",
            "Aggregate the latest scientific literature, commercial/regulatory progress, "
            "conference signals, and policy/news for a neuroscience-adjacent daily digest.",
            "",
            "## Disciplines (focus areas)",
        ]
        for i, d in enumerate(self.active_disciplines(), 1):
            lines.append(f"{i}. **{d.name}**")
            if d.arxiv_cats:
                lines.append(f"   - arXiv categories: {', '.join(d.arxiv_cats)}")
            if d.mesh_terms:
                lines.append(f"   - PubMed MeSH: {', '.join(d.mesh_terms)}")
            if d.bio_cats:
                lines.append(f"   - bioRxiv categories: {', '.join(d.bio_cats)}")
            if d.keywords:
                lines.append(f"   - keywords: {', '.join(d.keywords)}")
        lines.append("")
        lines.append("## Global keywords")
        lines.append(", ".join(self.global_keywords) if self.global_keywords else "(none)")
        lines.append("")
        lines.append("## Sources & limits")
        for name, opts in self.sources.items():
            enabled = opts.get("enabled", True)
            lines.append(f"- {name}: {'enabled' if enabled else 'disabled'} "
                         f"(max_results={opts.get('max_results', 20)}, "
                         f"lookback_days={opts.get('lookback_days', 14)})")
        lines.append("")
        lines.append("## Scheduled run")
        lines.append(f"- {self.scheduled}")
        lines.append("")
        lines.append("## Policy / news feeds")
        for u in self.policy_feeds:
            lines.append(f"- {u}")
        if self.journals:
            lines.append("")
            lines.append("## Top journals (watch list)")
            grouped: dict[str, list[Journal]] = {}
            for j in self.journals:
                grouped.setdefault(j.category, []).append(j)
            for cat, js in grouped.items():
                lines.append(f"### {cat}")
                for j in js:
                    line = f"- {j.name}"
                    if j.url:
                        line += f" ({j.url})"
                    lines.append(line)
        return "\n".join(lines)

    def show(self) -> str:
        return self.to_prompt()


# ---------------------------------------------------------------------------
# Default config tailored to the user's focus: neuroscience/psychiatry/
# cognitive neuroscience/neurosurgery/TBI/addiction/epilepsy.
# ---------------------------------------------------------------------------
def JOURNALS() -> list[Journal]:
    """Curated watch-list of top neuroscience/psychiatry journals (official sites + RSS).

    Only journals with a VERIFIED, working RSS feed get an ``rss`` value; others are
    kept as site links so the journal watch-list stays complete but never tries to
    pull from a dead/redirecting feed.
    """
    return [
        Journal("Nature", "https://www.nature.com/",
                "https://www.nature.com/nature.rss", "general"),
        Journal("Science", "https://www.science.org/", "", "general"),
        Journal("Cell", "https://www.cell.com/",
                "https://www.cell.com/action/showFeed?type=etoc&feed=rss&jc=cell", "general"),
        Journal("Nature Communications", "https://www.nature.com/ncomms",
                "https://www.nature.com/ncomms.rss", "general"),
        Journal("Nature Medicine", "https://www.nature.com/nm",
                "https://www.nature.com/nm.rss", "general"),
        Journal("Neuron", "https://www.cell.com/neuron",
                "https://www.cell.com/action/showFeed?type=etoc&feed=rss&jc=neuron", "neuroscience"),
        Journal("Nature Neuroscience", "https://www.nature.com/nn", "", "neuroscience"),
        Journal("Nature Reviews Neuroscience", "https://www.nature.com/nrn",
                "https://www.nature.com/nrn.rss", "neuroscience"),
        Journal("Trends in Neurosciences", "https://www.cell.com/trends/neurosciences",
                "https://www.cell.com/action/showFeed?type=etoc&feed=rss&jc=tins", "neuroscience"),
        Journal("Journal of Neuroscience", "https://www.jneurosci.org/", "", "neuroscience"),
        Journal("eLife", "https://elifesciences.org/",
                "https://observer.elifesciences.org/report/latest-articles.rss", "neuroscience"),
        Journal("Brain", "https://academic.oup.com/brain", "", "clinical_neuro"),
        Journal("Brain Research", "https://www.sciencedirect.com/journal/brain-research",
                "", "clinical_neuro"),
        Journal("Annals of Neurology", "https://onlinelibrary.wiley.com/journal/15318249",
                "", "clinical_neuro"),
        Journal("Nature Reviews Neurology", "https://www.nature.com/nrneurol",
                "https://www.nature.com/nrneurol.rss", "clinical_neuro"),
        Journal("Neurology", "https://www.neurology.org/",
                "https://www.neurology.org/action/showFeed?type=etoc&feed=rss&jc=wnl", "clinical_neuro"),
        Journal("The Lancet Neurology", "https://www.thelancet.com/journals/laneur",
                "", "clinical_neuro"),
        Journal("Biological Psychiatry", "https://www.biologicalpsychiatryjournal.com/",
                "https://rss.sciencedirect.com/publication/science/00063223", "psychiatry"),
        Journal("Molecular Psychiatry", "https://www.nature.com/mp",
                "https://www.nature.com/mp.rss", "psychiatry"),
        Journal("American Journal of Psychiatry", "https://ajp.psychiatryonline.org/",
                "", "psychiatry"),
        Journal("JAMA Psychiatry", "https://jamanetwork.com/journals/jamapsychiatry",
                "https://jamanetwork.com/rss/site_14/70.xml", "psychiatry"),
        Journal("World Psychiatry", "https://onlinelibrary.wiley.com/journal/20515545",
                "", "psychiatry"),
        Journal("Journal of Neurosurgery", "https://thejns.org/view/journals/j-neurosurg/j-neurosurg-overview.xml",
                "", "neurosurgery"),
        Journal("Neurosurgery", "https://journals.lww.com/neurosurgery", "", "neurosurgery"),
        Journal("Epilepsia", "https://onlinelibrary.wiley.com/journal/15281167",
                "", "epilepsy"),
        Journal("Epilepsy & Behavior", "https://www.sciencedirect.com/journal/epilepsy-behavior",
                "https://rss.sciencedirect.com/publication/science/15255050", "epilepsy"),
        Journal("Science Translational Medicine", "https://www.science.org/journal/stm",
                "", "translational"),
        Journal("Trends in Cognitive Sciences", "https://www.cell.com/trends/cognitive-sciences",
                "https://www.cell.com/action/showFeed?type=etoc&feed=rss&jc=tics", "cognition"),
        Journal("NeuroImage", "https://www.sciencedirect.com/journal/neuroimage",
                "https://rss.sciencedirect.com/publication/science/10538119", "cognition"),
    ]


def DEFAULT_CONFIG() -> Config:
    disciplines = [
        Discipline(
            name="Neuroscience",
            arxiv_cats=["q-bio.NC", "cs.NE"],
            mesh_terms=["Neurosciences"],
            bio_cats=["neuroscience"],
            keywords=["neuroscience", "brain", "neural"],
        ),
        Discipline(
            name="Psychiatry",
            arxiv_cats=["q-bio.NC"],
            mesh_terms=["Psychiatry", "Mental Disorders"],
            bio_cats=["psychiatry"],
            keywords=["psychiatry", "mental health", "mood disorder", "schizophrenia"],
        ),
        Discipline(
            name="Cognitive Neuroscience",
            arxiv_cats=["cs.NE", "q-bio.NC"],
            mesh_terms=["Cognitive Neuroscience", "Cognition"],
            bio_cats=["neuroscience"],
            keywords=["cognitive", "memory", "attention", "decision making"],
        ),
        Discipline(
            name="Neurosurgery",
            arxiv_cats=["q-bio.NC"],
            mesh_terms=["Neurosurgery", "Neurosurgical Procedures"],
            bio_cats=["neuroscience"],
            keywords=["neurosurgery"],
        ),
        Discipline(
            name="Traumatic Brain Injury",
            arxiv_cats=["q-bio.NC"],
            mesh_terms=["Brain Injuries, Traumatic", "Brain Concussion"],
            bio_cats=["neuroscience"],
            keywords=["traumatic brain injury", "TBI", "concussion"],
        ),
        Discipline(
            name="Addiction",
            arxiv_cats=["q-bio.NC"],
            mesh_terms=["Substance-Related Disorders", "Opioid-Related Disorders"],
            bio_cats=["neuroscience"],
            keywords=["addiction", "substance use disorder", "opioid", "dopamine"],
        ),
        Discipline(
            name="Epilepsy",
            arxiv_cats=["q-bio.NC"],
            mesh_terms=["Epilepsy", "Seizures"],
            bio_cats=["neuroscience"],
            keywords=["epilepsy", "seizure", "antiepileptic"],
        ),
    ]
    sources = {
        "journal":    {"enabled": True, "max_results": 500, "lookback_days": 1},
        "arxiv":      {"enabled": True, "max_results": 500, "lookback_days": 1},
        "pubmed":     {"enabled": True, "max_results": 500, "lookback_days": 1},
        "biorxiv":    {"enabled": True, "max_results": 500, "lookback_days": 1},
        "fda_drugs":  {"enabled": True, "max_results": 500, "lookback_days": 1},
        "fda_devices":{"enabled": True, "max_results": 500, "lookback_days": 1},
        "trials":     {"enabled": True, "max_results": 500, "lookback_days": 1},
        "policy":     {"enabled": True, "max_results": 500, "lookback_days": 1},
    }
    output = {
        "dir": DEFAULT_DIRS["output"],
        # Timestamped so every run (including the daily 08:00 job) writes a NEW
        # html instead of overwriting the same day's file.
        "filename_format": "neurodaily_%Y-%m-%d_%H%M%S.html",
        "open_on_finish": True,
    }
    scheduled = {
        "enabled": True,
        "hour": 8,
        "minute": 0,
        "launchd": {
            "label": "com.neurodaily.daily",
            "stdout": os.path.join(DEFAULT_DIRS["output"], "launchd_stdout.log"),
            "stderr": os.path.join(DEFAULT_DIRS["output"], "launchd_stderr.log"),
        },
    }
    policy_feeds = [
        "https://www.nimh.nih.gov/news/index.rss",
        "https://nida.nih.gov/rss.xml",
        "https://www.ninds.nih.gov/news-events/news-releases/rss.xml",
        "https://www.feinsteininstitutes.org/feed/",
        "https://www.sfn.org/news",
        "https://www.nature.com/subjects/neuroscience.rss",
        "https://www.nature.com/subjects/psychiatric-disorders.rss",
        "https://www.nature.com/subjects/addiction.rss",
        "https://www.nature.com/subjects/epilepsy.rss",
        # Journal RSS feeds verified to work (Nature redirects through auth, so
        # use the working subject feeds + these verified journals)
        "https://www.nature.com/mp.rss",
        "https://www.nature.com/nm.rss",
        "https://www.nature.com/ncomms.rss",
        "https://www.cell.com/action/showFeed?type=etoc&feed=rss&jc=neuron",
    ]
    journals = JOURNALS()
    return Config(
        profile="neuro",
        disciplines=disciplines,
        global_keywords=[
            "brain", "neuro", "neuron", "synapse", "neuroinflammation",
            "blood-brain barrier", "neuroimaging", "EEG", "fMRI", "cortex",
            "hippocampus", "neuroplasticity", "psychiatric", "neurological",
        ],
        sources=sources,
        output=output,
        scheduled=scheduled,
        policy_feeds=policy_feeds,
        journals=journals,
    )


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------
def normalize_keywords_into_query(keywords: list[str]) -> str:
    """Turn keywords into a quoted OR query fragment suitable for search APIs."""
    quoted = [f'"{k}"' for k in keywords if k.strip()]
    return " OR ".join(quoted) if quoted else "*"


def _validate(data: dict) -> None:
    if not data.get("disciplines"):
        raise ValueError("config must define at least one discipline")


if __name__ == "__main__":
    c = DEFAULT_CONFIG()
    print(c.to_prompt())
