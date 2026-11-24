"""Offline demo dataset so the product can be shown without any network."""
from __future__ import annotations

from datetime import datetime

from .config import DEFAULT_CONFIG
from .digest import DigestResult, _SECTION_BY_KIND
from .models import Item, tag_items
from .onthisday import is_enabled, today_events


def _items() -> list[Item]:
    return [
        Item(title="Oligodendrocyte dysfunction in human age-related cognitive decline",
             url="https://www.nature.com/articles/s41591-026-04608-y",
             summary="A human brain bank with >70 years of cognitive follow-up identifies "
                     "oligodendrocytes as active contributors to age-related cognitive decline.",
             authors=["Demo Author", "Second Author"], source="journal", kind="paper",
             affiliations=["Example brain bank, United Kingdom"],
             date="2026-08-25", doi="10.1038/s41591-026-04608-y",
             extra={"journal": "Nature Medicine"}),
        Item(title="Psychedelics align brain activity with context",
             url="https://www.nature.com/articles/s41586-026-10910-z",
             summary="Psilocybin reorganizes brain activity into context-aligned patterns that "
                     "integrate internal and external processing.",
             authors=["Demo Author"], source="journal", kind="paper", date="2026-08-19",
             doi="10.1038/s41586-026-10910-z", extra={"journal": "Nature"}),
        Item(title="Thalamo-accumbal circuit adaptations following extended oxycodone abstinence",
             url="https://elifesciences.org/articles/demo-oxycodone",
             summary="Optogenetic and electrophysiological study of PVT→NAc shell adaptations "
                     "after prolonged abstinence in male and female rats.",
             authors=["Demo Author"], source="journal", kind="paper", date="2026-08-21",
             extra={"journal": "eLife"}),
        Item(title="Cerebellar rhythms: mechanisms, functions and translational opportunities",
             url="https://www.nature.com/articles/s41583-026-01072-y",
             summary="Review of cerebellar oscillatory microcircuits and their potential for "
                     "precision neuromodulation.",
             authors=["Demo Author"], source="journal", kind="paper", date="2026-08-06",
             doi="10.1038/s41583-026-01072-y", extra={"journal": "Nature Reviews Neuroscience"}),
        Item(title="Lecanemab (Leqembi) receives full FDA approval for early Alzheimer's disease",
             url="https://www.fda.gov/drugs/demo-lecanemab",
             summary="FDA converts accelerated approval to traditional approval after confirmatory "
                     "data in early Alzheimer's disease.",
             source="fda_drugs", kind="drug", date="2026-07-06"),
        Item(title="Responsive neurostimulation (RNS) approved for drug-resistant focal epilepsy",
             url="https://www.fda.gov/medical-devices/demo-rns",
             summary="Closed-loop intracranial stimulation reduces seizure frequency in adults with "
                     "drug-resistant focal epilepsy.",
             source="fda_devices", kind="device", date="2026-05-12"),
        Item(title="MR CLEAN: endovascular thrombectomy for acute large-vessel occlusion",
             url="https://clinicaltrials.gov/study/demo-mrclean",
             summary="Randomized trial demonstrating improved functional outcomes with "
                     "intra-arterial treatment in acute ischemic stroke.",
             source="trials", kind="trial", date="2026-06-01",
             extra={"trial_sites": [{"facility": "Demo trial site", "city": "Rotterdam",
                                    "country": "Netherlands", "geoPoint": {"lat": 51.923, "lon": 4.479}}]}),
        Item(title="SANTE: anterior nucleus DBS for drug-resistant epilepsy",
             url="https://clinicaltrials.gov/study/demo-sante",
             summary="Long-term follow-up of thalamic stimulation showing sustained reduction in "
                     "seizure frequency.",
             source="trials", kind="trial", date="2026-04-18"),
        Item(title="NIMH launches initiative on circuit-based psychiatry",
             url="https://www.nimh.nih.gov/news/demo-circuit-psychiatry",
             summary="New funding program emphasizes circuit-level biomarkers and interventional "
                     "psychiatry.",
             source="policy", kind="news", date="2026-08-20"),
        Item(title="Longest-lived human brain organoids grown for years in culture",
             url="https://www.nature.com/articles/d41586-026-02617-y",
             summary="Organoids cultured for over five years continue to mature and record the "
                     "passage of time.",
             source="policy", kind="news", date="2026-08-19"),
    ]


def build_result(config=None) -> DigestResult:
    cfg = config or DEFAULT_CONFIG()
    items = tag_items(_items(), cfg)
    try:
        from .journal_metrics import for_item
        for it in items:
            m = for_item(it, cfg)
            if m:
                it.extra["metrics"] = m
    except Exception:
        pass
    sections = {"papers": [], "industry": [], "trials_conferences": [], "policy": []}
    for it in items:
        sections[_SECTION_BY_KIND.get(it.kind, "papers")].append(it)
    return DigestResult(
        items=items,
        sections=sections,
        health=[{"source": "demo", "ok": True, "count": len(items), "ms": 1}],
        generated_at=datetime.now().isoformat(),
        config_profile=f"{cfg.profile} (demo)",
        config=cfg,
        on_this_day=today_events() if is_enabled(cfg) else [],
    )
