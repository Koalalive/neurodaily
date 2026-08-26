"""ClinicalTrials.gov v2 API: recently registered/enrolled studies + conference signal."""
from __future__ import annotations

from datetime import datetime, timedelta

from .http import get, parse_date_any
from ..models import Item

BASE = "https://clinicaltrials.gov/api/v2/studies"


def fetch(config, logger=None) -> list[Item]:
    opts = config.source_opts("trials")
    max_results = int(opts.get("max_results", 10))
    lookback = int(opts.get("lookback_days", 60))

    monday_cutoff = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")
    items: list[Item] = []
    seen: set[str] = set()

    # Query each discipline separately with short term lists (long comma-joined
    # query.term lists cause HTTP 400 on the v2 API).
    for d in config.active_disciplines():
        conds = list(dict.fromkeys([x for x in (d.mesh_terms + d.keywords) if x]))
        if not conds:
            continue
        params = {
            "query.term": ",".join(conds[:8]),
            "pageSize": max_results,
            "format": "json",
            "sort": "LastUpdatePostDate:desc",
            "filter.advanced": f"AREA[LastUpdatePostDate]RANGE[{monday_cutoff},MAX]",
        }
        resp = get(BASE, params=params, connect_close=True, user_agent="python-httpx")
        if resp is None:
            continue
        try:
            data = resp.json()
        except ValueError:
            continue
        studies = data.get("studies", [])
        for s in studies:
            p = s.get("protocolSection", {})
            idm = p.get("identificationModule", {})
            statusm = p.get("statusModule", {})
            descm = p.get("descriptionModule", {})
            scm = p.get("sponsorCollaboratorsModule", {})
            clm = p.get("contactsLocationsModule", {})
            conds2 = p.get("conditionsModule", {}).get("conditions", [])
            title = idm.get("briefTitle", "")
            if not title:
                continue
            nct = idm.get("nctId", "")
            if nct in seen:
                continue
            seen.add(nct)
            last_update = statusm.get("lastUpdatePostDateStruct", {}).get("date", "")

            sponsor = scm.get("leadSponsor", {}).get("name", "")
            authors = []
            affiliations = []
            corresponding = []
            for off in clm.get("overallOfficials", []):
                nm = off.get("name", "")
                aff = off.get("affiliation", "")
                role = off.get("role", "")
                if nm:
                    authors.append(nm)
                if aff:
                    affiliations.append(aff)
                if nm and role == "PRINCIPAL_INVESTIGATOR":
                    corresponding.append(nm)
            # add sponsor as an affiliation (institution) if not already present
            if sponsor and sponsor not in affiliations:
                affiliations.append(sponsor)
            # add site organizations (locations)
            for loc in clm.get("locations", []):
                fac = loc.get("facility", "")
                city = loc.get("city", "")
                country = loc.get("country", "")
                site = ", ".join(x for x in [fac, city, country] if x)
                if site and site not in affiliations:
                    affiliations.append(site)

            items.append(Item(
                title=title,
                url=f"https://clinicaltrials.gov/study/{nct}" if nct else "",
                summary=descm.get("briefSummary", "")[:1200],
                authors=authors,
                affiliations=affiliations,
                corresponding=corresponding,
                source="trials",
                kind="trial",
                date=parse_date_any(last_update),
                doi="",
                tags=conds2,
                extra={"nct": nct, "status": statusm.get("overallStatus", ""),
                       "conditions": conds2,
                       "phase": p.get("designModule", {}).get("phases", []),
                       "sponsor": sponsor,
                       "enrollment": p.get("designModule", {}).get("enrollmentInfo", {}).get("count")},
            ))
            if len(items) >= max_results:
                break
        if len(items) >= max_results:
            break
    return items
