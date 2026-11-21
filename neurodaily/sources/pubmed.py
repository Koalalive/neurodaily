"""PubMed source via NCBI E-utilities (esearch + efetch XML).

We fetch XML so we can capture author affiliations and the abstract, which the
JSON summary endpoint does not provide.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

from .http import get, mark_sampled, parse_date_any, record_candidates, record_failure, record_query
from ..models import Item

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
MONTHS = ("", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _esearch(term: str, retmax: int, *, preview: bool = False) -> list[str]:
    record_query(term)
    resp = get(f"{BASE}/esearch.fcgi", params={
        "db": "pubmed",
        "term": term,
        "retmode": "json",
        "retmax": retmax,
        "sort": "date",
    }, timeout=8.0 if preview else 20.0, retries=0 if preview else 2)
    if resp is None:
        return []
    try:
        result = resp.json()["esearchresult"]
        if result.get("error") or result.get("ERROR"):
            raise ValueError("ESearch reported an error")
        ids = result["idlist"]
        if not isinstance(ids, list):
            raise ValueError("invalid idlist")
        count = int(result.get("count", len(ids)))
    except (ValueError, TypeError, KeyError, AttributeError):
        record_failure("Invalid PubMed ESearch response")
        return []
    record_candidates(count)
    if count > len(ids):
        mark_sampled(truncated=True)
    return ids


def _efetch_xml(pmids: list[str], *, preview: bool = False) -> str:
    """Fetch full PubMed records as XML for the given PMIDs."""
    if not pmids:
        return ""
    resp = get(f"{BASE}/efetch.fcgi", params={
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }, timeout=8.0 if preview else 20.0, retries=0 if preview else 2)
    return resp.text if resp is not None else ""


def _text(parent, path) -> str:
    el = parent.find(path) if parent is not None else None
    return "".join(el.itertext()).strip() if el is not None else ""


def _date(element) -> str:
    year = _text(element, "Year")
    month = _text(element, "Month")
    day = _text(element, "Day")
    if not year.isdigit():
        return parse_date_any(_text(element, "MedlineDate"))
    if not month:
        return year
    try:
        month_number = int(month) if month.isdigit() else MONTHS.index(month[:3].title())
        if not 1 <= month_number <= 12:
            return year
        if not day:
            return f"{int(year):04d}-{month_number:02d}"
        return datetime(int(year), month_number, int(day)).date().isoformat()
    except (ValueError, OverflowError):
        return year


def _parse_article(pubmed_article) -> Item | None:
    """Parse one <PubmedArticle> into an Item with authors + affiliations."""
    citation = pubmed_article.find("MedlineCitation")
    medline = citation.find("Article") if citation is not None else None
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
    if not doi:
        doi = _text(pubmed_article, "PubmedData/ArticleIdList/ArticleId[@IdType='doi']")

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

    pmid = _text(citation, "PMID")
    history = pubmed_article.find("PubmedData/History")
    online = _date(medline.find("ArticleDate[@DateType='Electronic']"))
    if not online and history is not None:
        online = _date(history.find("PubMedPubDate[@PubStatus='epublish']"))
    print_date = _date(medline.find("Journal/JournalIssue/PubDate"))
    entry_date = _date(history.find("PubMedPubDate[@PubStatus='entrez']")) if history is not None else ""
    extra = {"pmid": pmid, "journal": journal}
    if abstract:
        extra["abstract"] = abstract
    for name, values in (
        ("keywords", citation.findall("KeywordList/Keyword")),
        ("mesh_terms", citation.findall("MeshHeadingList/MeshHeading/DescriptorName")),
        ("publication_types", medline.findall("PublicationTypeList/PublicationType")),
    ):
        fields = [_text(el, ".") for el in values]
        if fields:
            extra[name] = fields
    for name, value in (
        ("issn", _text(journal_el, "ISSN")),
        ("issn_linking", _text(citation, "MedlineJournalInfo/ISSNLinking")),
        ("journal_abbreviation", _text(journal_el, "ISOAbbreviation")),
        ("published_online", online),
        ("published_print", print_date),
        ("entry_date", entry_date),
    ):
        if value:
            extra[name] = value
    if extra.get("issn") or extra.get("issn_linking"):
        extra["issns"] = list(dict.fromkeys(value for value in
                               (extra.get("issn"), extra.get("issn_linking")) if value))
    if extra.get("journal_abbreviation"):
        extra["journal_aliases"] = [extra["journal_abbreviation"]]

    return Item(
        title=title,
        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        summary=abstract[:1200],
        authors=authors,
        affiliations=affiliations,
        source="pubmed",
        kind="paper",
        date=online or print_date,
        doi=doi,
        tags=["pubmed"],
        extra=extra,
    )


def _field_term(value: str, field: str) -> str:
    literal = value.replace('"', " ").strip()
    return f'"{literal}"[{field}]'


def build_terms(config) -> list[str]:
    terms = []
    for d in config.active_disciplines():
        sub = [_field_term(term, "MeSH") for term in d.mesh_terms if term.strip()]
        sub.extend(_field_term(term, "Title/Abstract") for term in d.keywords if term.strip())
        if sub:
            terms.append("(" + " OR ".join(sub) + ")")
    configured = {term.strip().casefold() for discipline in config.active_disciplines() for term in discipline.keywords}
    globals_only = [_field_term(term, "Title/Abstract") for term in config.global_keywords
                    if term.strip() and term.strip().casefold() not in configured]
    if globals_only:
        terms.append("(" + " OR ".join(globals_only) + ")")
    return terms


def fetch(config, logger=None) -> list[Item]:
    opts = config.source_opts("pubmed")
    preview = opts.get("preview", False)
    max_results = int(opts.get("max_results", 25))
    lookback = int(opts.get("lookback_days", 7))

    plan = None
    if getattr(config, "search", None):
        from ..search import compile_search
        plan = compile_search(config.search)
    bounds = plan.date_range if plan and plan.active else None
    if bounds:
        start, end = (bound.replace("-", "/") for bound in bounds)
        daterange = f"({start}[dp]:{end}[dp])"
    else:
        daterange = f'("last {lookback} days"[dp])'
    terms = [plan.remote_query("pubmed")] if plan and plan.active else build_terms(config)
    if preview:
        max_results = min(max_results, 30)
        if len(terms) > 4:
            terms = [*terms[:3], terms[-1]]
            mark_sampled(truncated=True)

    items: list[Item] = []
    seen: set[str] = set()

    for term in terms:
        query = f"({term}) AND {daterange}" if term else daterange
        pmid_list = [pmid for pmid in _esearch(query, max_results, preview=preview) if pmid not in seen]
        for start in range(0, len(pmid_list), 100):
            batch = pmid_list[start:start + 100]
            xml = _efetch_xml(batch, preview=preview)
            if not xml:
                continue
            try:
                root = ET.fromstring(xml)
            except ET.ParseError:
                record_failure("Invalid PubMed EFetch XML")
                continue
            parsed = [item for pa in root.findall("PubmedArticle") if (item := _parse_article(pa))]
            fetched = {item.extra["pmid"] for item in parsed if item.extra["pmid"]}
            if set(batch) - fetched:
                record_failure("PubMed returned records without the requested paper metadata")
            for item in parsed:
                pmid = item.extra["pmid"]
                if pmid and pmid not in seen:
                    seen.add(pmid)
                    items.append(item)

    # Strict same-day filter ("last N days"[dp] can include yesterday's entries).
    if lookback <= 1 and not bounds:
        today = datetime.now().strftime("%Y-%m-%d")
        items = [it for it in items if it.date.startswith(today)]
    return items
