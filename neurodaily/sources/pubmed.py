"""PubMed source via NCBI E-utilities (esearch + efetch XML).

We fetch XML so we can capture author affiliations and the abstract, which the
JSON summary endpoint does not provide.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from .http import get, parse_date_any
from ..models import Item

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NS = {"m": "http://www.w3.org/2005/Atom"}


def _esearch(term: str, retmax: int) -> list[str]:
    resp = get(f"{BASE}/esearch.fcgi", params={
        "db": "pubmed",
        "term": term,
        "retmode": "json",
        "retmax": retmax,
        "sort": "date",
    })
    if resp is None:
        return []
    try:
        data = resp.json()
        return data.get("esearchresult", {}).get("idlist", [])
    except (ValueError, AttributeError):
        return []


def _efetch_xml(pmids: list[str]) -> str:
    """Fetch full PubMed records as XML for the given PMIDs."""
    if not pmids:
        return ""
    resp = get(f"{BASE}/efetch.fcgi", params={
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    })
    return resp.text if resp is not None else ""


def _text(parent, path) -> str:
    el = parent.find(path)
    return (el.text or "").strip() if el is not None else ""


def _parse_article(pubmed_article) -> Item | None:
    """Parse one <PubmedArticle> into an Item with authors + affiliations."""
    medline = pubmed_article.find("MedlineCitation/Article")
    if medline is None:
        return None
    title = _text(medline, "ArticleTitle")
    if not title:
        return None

    journal_el = medline.find("Journal")
    journal = _text(journal_el, "Title") if journal_el is not None else ""
    doi = ""
    for eid in medline.findall("ELocationID"):
        if eid.get("EIdType") == "doi":
            doi = (eid.text or "").strip()
            break

    abstract_blocks = []
    ab = medline.find("Abstract")
    if ab is not None:
        for at in ab.findall("AbstractText"):
            label = at.get("Label")
            t = "".join(at.itertext()).strip()
            if not t:
                continue
            if label:
                t = f"{label}: {t}"
            abstract_blocks.append(t)
    abstract = " ".join(abstract_blocks)

    authors: list[str] = []
    affiliations: list[str] = []
    alist = medline.find("AuthorList")
    if alist is not None:
        for a in alist.findall("Author"):
            last = _text(a, "LastName")
            fore = _text(a, "ForeName")
            coll = _text(a, "CollectiveName")
            if coll:
                authors.append(coll)
            elif last and fore:
                authors.append(f"{fore} {last}")
            elif last:
                authors.append(last)
            for aff in a.findall("AffiliationInfo/Affiliation"):
                v = (aff.text or "").strip()
                if v:
                    affiliations.append(v)

    pmid = _text(pubmed_article.find("MedlineCitation/PMID"), ".")
    pubdate = _text(medline, "Journal/JournalIssue/PubDate/Year") or _text(
        medline, "Journal/JournalIssue/PubDate/MedlineDate")
    pubdate = parse_date_any(pubdate)

    return Item(
        title=title,
        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        summary=abstract[:1200],
        authors=authors,
        affiliations=affiliations,
        source="pubmed",
        kind="paper",
        date=pubdate,
        doi=doi,
        tags=["pubmed"],
        extra={"pmid": pmid, "journal": journal},
    )


def build_terms(config) -> list[str]:
    terms = []
    for d in config.active_disciplines():
        sub = []
        for m in d.mesh_terms:
            sub.append(f"{m}[MeSH]")
        for k in d.keywords:
            sub.append(f"{k}[Title/Abstract]")
        if sub:
            terms.append("(" + " OR ".join(sub) + ")")
    return terms


def fetch(config, logger=None) -> list[Item]:
    opts = config.source_opts("pubmed")
    max_results = int(opts.get("max_results", 25))
    lookback = int(opts.get("lookback_days", 7))

    daterange = f'("last {lookback} days"[dp])'
    terms = build_terms(config)

    items: list[Item] = []
    seen: set[str] = set()

    for term in terms:
        query = f'{term} AND {daterange}'
        pmid_list = _esearch(query, max_results)
        if not pmid_list:
            continue
        xml = _efetch_xml(pmid_list)
        if not xml:
            continue
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            continue
        for pa in root.findall("PubmedArticle"):
            pmid = _text(pa.find("MedlineCitation/PMID"), ".")
            if not pmid or pmid in seen:
                continue
            seen.add(pmid)
            item = _parse_article(pa)
            if item:
                items.append(item)
    return items
