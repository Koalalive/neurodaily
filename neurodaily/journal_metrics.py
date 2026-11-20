"""Journal metrics: auto (OpenAlex) + official (user-imported JCR/CAS).

Why not bundle JCR IF / CAS partition?
- JCR (Clarivate) and 中科院分区 are **proprietary**; there is no free, legal API.
- OpenAlex is free and provides `2yr_mean_citedness` (an IF-like citation rate),
  h-index, i10-index and citation counts. We fetch these automatically.

Layers
1. AUTO  — `output/journal_metrics_auto.json`, refreshed from OpenAlex (TTL 1 day).
2. OFFICIAL — `config/journal_metrics.json`, imported from a JCR/CAS export:
      {"ttl_days": 1,
       "journals": {"Nature Medicine": {"if": 58.7, "jcr": "Q1",
                                        "cas": "1区", "year": 2023}}}
   Official values override auto values.

Rendering rules
- IF / JCR / 中科院 only when official data exists (labelled as official).
- Otherwise show `OA 2yr` from OpenAlex, explicitly **not** JCR IF.
"""
from __future__ import annotations

import csv
import json
import os
import re
from datetime import date, datetime

import httpx

ROOT = os.environ.get("NEURODAILY_HOME") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTO_PATH = os.path.join(ROOT, "output", "journal_metrics_auto.json")
OFFICIAL_PATH = os.path.join(ROOT, "config", "journal_metrics.json")

OPENALEX = "https://api.openalex.org/sources"
TTL_DAYS = 1

_ALIASES = {
    "nat med": "Nature Medicine",
    "nat neurosci": "Nature Neuroscience",
    "nat rev neurosci": "Nature Reviews Neuroscience",
    "nat rev neurol": "Nature Reviews Neurology",
    "nat commun": "Nature Communications",
    "j neurosci": "Journal of Neuroscience",
    "biol psychiatry": "Biological Psychiatry",
    "mol psychiatry": "Molecular Psychiatry",
    "am j psychiatry": "American Journal of Psychiatry",
    "lancet neurol": "The Lancet Neurology",
    "sci transl med": "Science Translational Medicine",
    "trends cogn sci": "Trends in Cognitive Sciences",
    "trends neurosci": "Trends in Neurosciences",
    "j neurosurg": "Journal of Neurosurgery",
    "epilepsy behav": "Epilepsy & Behavior",
    "ann neurol": "Annals of Neurology",
    "brain res": "Brain Research",
}


# Stable ISSNs for the default watch-list (identifiers only, NOT metrics).
_ISSN_MAP = {
    "Nature": "0028-0836",
    "Science": "0036-8075",
    "Cell": "0092-8674",
    "Nature Medicine": "1078-8956",
    "Nature Communications": "2041-1723",
    "Neuron": "0896-6273",
    "Nature Neuroscience": "1097-6256",
    "Nature Reviews Neuroscience": "1471-0048",
    "Trends in Neurosciences": "0166-2236",
    "Journal of Neuroscience": "0270-6474",
    "eLife": "2050-084X",
    "Brain": "0006-8950",
    "Brain Research": "0006-8993",
    "Annals of Neurology": "0364-5134",
    "Nature Reviews Neurology": "1759-4758",
    "Neurology": "0028-3878",
    "The Lancet Neurology": "1474-4422",
    "Biological Psychiatry": "0006-3223",
    "Molecular Psychiatry": "1359-4184",
    "American Journal of Psychiatry": "0002-953X",
    "JAMA Psychiatry": "2168-622X",
    "World Psychiatry": "1723-8617",
    "Journal of Neurosurgery": "0022-3085",
    "Neurosurgery": "0148-396X",
    "Epilepsia": "0013-9580",
    "Epilepsy & Behavior": "1525-5050",
    "Science Translational Medicine": "1946-6234",
    "Trends in Cognitive Sciences": "1364-6613",
    "NeuroImage": "1053-8119",
}


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[\(\)\[\]\{\}:;,.!?'\"/\\&]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _read_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_official() -> dict:
    data = _read_json(OFFICIAL_PATH)
    if isinstance(data.get("journals"), dict):
        return data["journals"]
    # tolerate a flat {name: {...}} file
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def load_auto() -> dict:
    data = _read_json(AUTO_PATH)
    return data.get("journals", {}) if isinstance(data.get("journals"), dict) else data


def ttl_days() -> int:
    data = _read_json(OFFICIAL_PATH)
    try:
        return int(data.get("ttl_days", TTL_DAYS))
    except Exception:
        return TTL_DAYS


def _age_days(fetched_at: str | None) -> float:
    if not fetched_at:
        return 1e9
    try:
        d = datetime.strptime(fetched_at[:10], "%Y-%m-%d").date()
        return (date.today() - d).days
    except Exception:
        return 1e9


def _find_key(name: str, mapping: dict) -> str | None:
    n = _norm(name)
    for key in mapping:
        if _norm(key) == n:
            return key
    alias = _ALIASES.get(n)
    if alias and alias in mapping:
        return alias
    for key in mapping:
        kn = _norm(key)
        if kn and len(kn) >= 5 and (kn in n or n in kn):
            return key
    return None


def _config_metrics(name: str, config) -> dict | None:
    """User-hardcoded metrics in config.journals take precedence over everything."""
    if config is None:
        return None
    n = _norm(name)
    alias = _ALIASES.get(n)
    for j in getattr(config, "journals", []) or []:
        jn = _norm(getattr(j, "name", ""))
        if not jn:
            continue
        # Exact / known alias only: "Nature" must not match "Nature Medicine".
        if not (jn == n
                or (alias is not None and _norm(alias) == jn)
                or (_ALIASES.get(jn) is not None and _norm(_ALIASES[jn]) == n)):
            continue
        if j.impact_factor or j.jcr or j.cas:
            return {
                "name": j.name,
                "if": j.impact_factor,
                "jcr": j.jcr or None,
                "cas": j.cas or None,
                "year": j.metric_year,
                "official": True,
                "source": "config",
            }
    return None


def lookup(name: str | None, config=None) -> dict | None:
    if not name:
        return None
    official = load_official()
    auto = load_auto()

    hard = _config_metrics(name, config)
    if hard:
        off_key = _find_key(hard["name"], official) or _find_key(name, official)
        off = official.get(off_key, {}) if off_key else {}
        auto_key = _find_key(hard["name"], auto) or _find_key(name, auto)
        aut = auto.get(auto_key, {}) if auto_key else {}
        out = {
            "name": hard["name"],
            # per-field merge: hardcoded wins, official fills missing fields
            "if": hard.get("if") if hard.get("if") is not None else off.get("if"),
            "jcr": hard.get("jcr") or off.get("jcr"),
            "cas": hard.get("cas") or off.get("cas"),
            "year": hard.get("year") or off.get("year"),
            "official": True,
            "source": "config",
            "oa_2yr": aut.get("oa_2yr"),
            "h_index": aut.get("h_index"),
            "works": aut.get("works"),
            "openalex_id": aut.get("openalex_id"),
            "fetched_at": aut.get("fetched_at"),
        }
        return out

    canon = _find_key(name, {**official, **auto})
    if canon is None:
        return None

    off = official.get(canon, {}) or {}
    aut = auto.get(canon, {}) or {}
    out = {
        "name": canon,
        "if": off.get("if"),
        "jcr": off.get("jcr"),
        "cas": off.get("cas"),
        "year": off.get("year"),
        "official": bool(off),
        "oa_2yr": aut.get("oa_2yr"),
        "h_index": aut.get("h_index"),
        "works": aut.get("works"),
        "openalex_id": aut.get("openalex_id"),
        "fetched_at": aut.get("fetched_at"),
    }
    return out if any(out[k] is not None for k in ("if", "jcr", "cas", "oa_2yr")) else None


def for_item(item, config=None) -> dict | None:
    extra = getattr(item, "extra", None) or {}
    for key in ("journal", "journal_abbrev", "container", "venue"):
        m = lookup(extra.get(key), config=config)
        if m:
            return m
    return None


def _pick(name: str, results: list[dict]) -> dict | None:
    if not results:
        return None
    n = _norm(name)
    for r in results:
        if _norm(r.get("display_name", "")) == n:
            return r
    return results[0]


def _resolve_issn(client: httpx.Client, name: str) -> str | None:
    if name in _ISSN_MAP:
        return _ISSN_MAP[name]
    cached = (load_auto().get(name) or {}).get("issn_l")
    if cached:
        return cached
    try:
        r = client.get("https://api.crossref.org/journals",
                       params={"query": name, "rows": 20,
                               "mailto": os.environ.get("OPENALEX_MAILTO", "neurodaily@example.com")},
                       timeout=30)
        r.raise_for_status()
        target = _norm(name)
        best = None
        for it in r.json().get("message", {}).get("items", []):
            title = _norm(it.get("title") or "")
            if not title:
                continue
            if title == target or title == "the " + target or target == "the " + title:
                best = it
                break
        if best and best.get("ISSN"):
            return best["ISSN"][0]
    except Exception:
        return None
    return None


def _fetch_one(client: httpx.Client, name: str) -> dict | None:
    issn = (load_official().get(name) or {}).get("issn") or _resolve_issn(client, name)
    if issn:
        r = client.get(f"{OPENALEX}/issn:{issn}", timeout=30)
        if r.status_code == 200:
            s = r.json()
        else:
            r = client.get(OPENALEX, params={"filter": f"issn:{issn}", "per_page": 1}, timeout=30)
            r.raise_for_status()
            results = r.json().get("results", [])
            s = results[0] if results else None
    else:
        r = client.get(OPENALEX, params={"search": name, "per_page": 5}, timeout=30)
        r.raise_for_status()
        s = _pick(name, r.json().get("results", []))
    if not s:
        return None
    st = s.get("summary_stats") or {}
    return {
        "issn_l": s.get("issn_l") or issn,
        "display_name": s.get("display_name"),
        "issn_l": s.get("issn_l"),
        "openalex_id": s.get("id"),
        "oa_2yr": st.get("2yr_mean_citedness"),
        "h_index": st.get("h_index"),
        "i10_index": st.get("i10_index"),
        "works": s.get("works_count"),
        "cited_by_count": s.get("cited_by_count"),
        "fetched_at": date.today().isoformat(),
    }


def refresh(names: list[str] | None = None, force: bool = False) -> dict:
    """Fetch OpenAlex metrics for `names`; skip fresh entries unless force."""
    if names is None:
        try:
            from .config import Config
            names = [j.name for j in Config.load().journals]
        except Exception:
            names = sorted(set(load_official()) | set(load_auto()))
    auto = load_auto()
    ttl = ttl_days()
    updated, skipped = 0, 0
    with httpx.Client(headers={"User-Agent": "NeuroDaily/0.1 (metrics)"}) as client:
        for name in names:
            if not force and _age_days((auto.get(name) or {}).get("fetched_at")) < ttl:
                skipped += 1
                continue
            try:
                got = _fetch_one(client, name)
            except Exception:
                got = None
            if got:
                auto[name] = got
                updated += 1
    os.makedirs(os.path.dirname(AUTO_PATH), exist_ok=True)
    tmp = AUTO_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"journals": auto, "updated_at": datetime.now().isoformat()},
                  f, ensure_ascii=False, indent=1)
    os.replace(tmp, AUTO_PATH)
    return {"updated": updated, "skipped": skipped, "total": len(auto)}


def ensure_fresh(journal_names: list[str], force: bool = False) -> dict | None:
    """Refresh only if some journal is missing/stale. Never raises."""
    try:
        auto = load_auto()
        ttl = ttl_days()
        stale = [n for n in journal_names
                 if _age_days((auto.get(n) or {}).get("fetched_at")) >= ttl]
        if force or stale:
            return refresh(journal_names if stale else None, force=force)
    except Exception:
        return None
    return None


def import_csv(path: str) -> dict:
    """Import official JCR/CAS values.

    CSV columns (case-insensitive): journal|name, if, jcr, cas, year
    """
    official = load_official()
    n = 0
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            low = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
            name = low.get("journal") or low.get("name")
            if not name:
                continue
            entry = {}
            if low.get("if"):
                try:
                    entry["if"] = float(low["if"])
                except ValueError:
                    pass
            if low.get("jcr"):
                entry["jcr"] = low["jcr"].upper()
            if low.get("cas"):
                entry["cas"] = low["cas"]
            if low.get("year"):
                try:
                    entry["year"] = int(low["year"])
                except ValueError:
                    pass
            if entry:
                official[name] = {**official.get(name, {}), **entry, "official": True}
                n += 1
    os.makedirs(os.path.dirname(OFFICIAL_PATH), exist_ok=True)
    with open(OFFICIAL_PATH, "w", encoding="utf-8") as f:
        json.dump({"ttl_days": ttl_days(), "journals": official}, f,
                  ensure_ascii=False, indent=2)
    return {"imported": n, "total": len(official), "path": OFFICIAL_PATH}


def status() -> dict:
    auto = load_auto()
    official = load_official()
    ages = [_age_days(v.get("fetched_at")) for v in auto.values()]
    return {
        "auto_count": len(auto),
        "official_count": len(official),
        "oldest_auto_days": max(ages) if ages else None,
        "ttl_days": ttl_days(),
        "auto_path": AUTO_PATH,
        "official_path": OFFICIAL_PATH,
    }
