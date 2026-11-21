"""Summarize the papers in a saved digest without contacting any service."""

from collections import Counter, defaultdict
from datetime import date
from html import escape
import re

from .models import Item


_LABELS = {
    "zh": {
        "title": "文献计量", "description": "统计本次日报收录的论文。作者按显示名称统计，来源按主记录统计。",
        "papers": "论文", "dated": "有发表年份", "year": "发表年份", "all": "全部", "unknown": "未知年份",
        "trend": "发表趋势", "journals": "期刊（前 10）", "authors": "作者（前 10）", "sources": "论文来源",
        "empty": "本次日报暂无论文。", "missing": "暂无可用元数据。",
    },
    "en": {
        "title": "Bibliometrics", "description": "Counts cover papers in this report. Authors are grouped by display name and sources use the primary record.",
        "papers": "Papers", "dated": "With publication year", "year": "Publication year", "all": "All", "unknown": "Unknown year",
        "trend": "Publication trend", "journals": "Top 10 journals", "authors": "Top 10 authors", "sources": "Paper sources",
        "empty": "This report contains no papers.", "missing": "No metadata available.",
    },
    "ru": {
        "title": "Библиометрия", "description": "Подсчёт включает статьи из этого отчёта. Авторы сгруппированы по отображаемым именам, источники определены по основным записям.",
        "papers": "Статьи", "dated": "С годом публикации", "year": "Год публикации", "all": "Все", "unknown": "Год неизвестен",
        "trend": "Динамика публикаций", "journals": "10 ведущих журналов", "authors": "10 ведущих авторов", "sources": "Источники статей",
        "empty": "В этом отчёте нет статей.", "missing": "Метаданные отсутствуют.",
    },
}

_DATE = re.compile(r"(\d{4})(?:-(\d{2})(?:-(\d{2})(?:[T ].*)?)?)?")
_JOURNAL_KEYS = ("journal", "journal_abbreviation", "journal_abbrev", "container", "venue")


def _name(value) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _canonical_name(value: str) -> str:
    return re.sub(r"[^\w]+", " ", value.casefold()).strip()


def _publication_period(value: str) -> str:
    match = _DATE.fullmatch(_name(value))
    if match:
        year, month, day = match.groups()
        try:
            date(int(year), int(month or "1"), int(day or "1"))
        except ValueError:
            return ""
        return f"{year}-{month}" if month else year
    return ""


def _alias_lookup(journals) -> dict[str, str]:
    return {_canonical_name(alias): journal.name
            for journal in journals for alias in (journal.name, *journal.aliases)}


def _counts(papers: list[tuple[Item, str]], aliases) -> dict[str, Counter]:
    counts = {key: Counter() for key in ("trend", "authors", "journals", "sources")}
    names = {key: {} for key in ("authors", "journals", "sources")}

    def add(key, values):
        normalized = {}
        for value in values:
            label = _name(value)
            if label:
                normalized.setdefault(label.casefold(), label)
        for identifier, label in normalized.items():
            canonical = names[key].setdefault(identifier, label)
            counts[key][canonical] += 1

    for item, period in papers:
        if period:
            counts["trend"][period] += 1
        journal = next((_name(item.extra.get(key)) for key in _JOURNAL_KEYS
                        if _name(item.extra.get(key))), "")
        add("journals", [aliases.get(_canonical_name(journal), journal)])
        add("authors", item.authors)
        add("sources", [item.source] if item.source != "unknown" else [])
    return counts


def _ranked_rows(rows: Counter, *, chronological=False, limit=None) -> list[tuple[str, int]]:
    if chronological:
        return sorted(rows.items())
    return sorted(rows.items(), key=lambda pair: (-pair[1], pair[0].casefold()))[:limit]


def _panel(title: str, rows, missing: str, *, expand=False) -> str:
    detail = f'<details{" open" if expand else ""}><summary>{title}</summary>'
    if not rows:
        return f"{detail}<p>{missing}</p></details>"
    maximum = max(count for _, count in rows)
    table = "".join(f'<tr><th scope="row" data-no-i18n>{escape(name)}</th><td><meter aria-hidden="true" min="0" '
                    f'max="{maximum}" value="{count}"></meter></td><td>{count}</td></tr>'
                    for name, count in rows)
    return f'{detail}<table aria-label="{title}"><tbody>{table}</tbody></table></details>'


def render_bibliometrics(items: list[Item], journals=(), *, locale: str = "zh") -> str:
    language = locale.lower().replace("_", "-").split("-", 1)[0]
    labels = _LABELS.get(language, _LABELS["zh"])
    papers = [(item, _publication_period(item.date)) for item in items if item.kind == "paper"]
    heading = f'<summary class="bib-title">{labels["title"]} <b>{len(papers)}</b></summary>'
    if not papers:
        return f'<details id="bibliometrics" class="bib-metrics">{heading}<p>{labels["empty"]}</p></details>{_STYLE}'

    aliases = _alias_lookup(journals)
    groups = defaultdict(list)
    for item, period in papers:
        groups[period[:4] or "unknown"].append((item, period))
    years = sorted((year for year in groups if year != "unknown"), reverse=True)
    if "unknown" in groups:
        years.append("unknown")

    def view(key, group):
        counts = _counts(group, aliases)
        panels = "".join(
            _panel(labels[metric], _ranked_rows(rows, chronological=metric == "trend",
                                               limit=10 if metric in {"authors", "journals"} else None),
                   labels["missing"], expand=metric == "trend")
            for metric, rows in counts.items()
        )
        hidden = "" if key == "all" else " hidden"
        return (
            f'<div data-bib-period="{key}"{hidden}>'
            f'<p>{labels["papers"]} <b>{len(group)}</b> · {labels["dated"]} '
            f'<b>{sum(counts["trend"].values())}</b></p>'
            f'<div class="bib-grid">{panels}</div></div>'
        )

    controls = script = ""
    views = view("all", papers)
    if len(years) > 1:
        options = "".join(f'<option value="{year}">{labels.get(year, year)}</option>' for year in years)
        controls = (
            f'<label class="bib-year" hidden>{labels["year"]} '
            f'<select><option value="all">{labels["all"]}</option>{options}</select></label>'
        )
        views += "".join(view(year, groups[year]) for year in years)
        script = _FILTER

    return (
        f'<details id="bibliometrics" class="bib-metrics">{heading}'
        f'<p>{labels["description"]}</p>{controls}{views}</details>{_STYLE}{script}'
    )


_STYLE = """
<style>
.bib-metrics{margin:1.2rem 0;padding:.85rem 1rem;border:1px solid var(--line,#333);border-radius:12px}
.bib-metrics summary{cursor:pointer}
.bib-metrics .bib-title{font-weight:700}
.bib-metrics .bib-title b{margin-inline-start:.5rem;color:var(--muted,#9ca3af);font-size:.85em}
.bib-metrics p{margin:.55rem 0;color:var(--muted,#9ca3af)}
.bib-metrics select{font:inherit;margin-inline-start:.35rem}
.bib-metrics .bib-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(16rem,100%),1fr));gap:.55rem}
.bib-grid details{border:1px solid var(--line,#333);border-radius:8px;padding:.55rem .7rem;min-width:0}
.bib-grid table{width:100%;margin-top:.35rem;border-collapse:collapse;font-size:.85em}
.bib-grid th{text-align:start;font-weight:400;overflow-wrap:anywhere}
.bib-grid td{text-align:end;font-variant-numeric:tabular-nums;padding-inline-start:.35rem}
.bib-grid meter{width:3.6rem;max-width:100%;height:.65rem}
.bib-metrics [hidden]{display:none}
</style>
"""

_FILTER = """
<script>
(function(){
  const metrics = document.getElementById('bibliometrics');
  const filter = metrics.querySelector('.bib-year');
  const select = filter.querySelector('select');
  const periods = metrics.querySelectorAll('[data-bib-period]');
  select.addEventListener('change', () => {
    for (const period of periods) period.hidden = period.dataset.bibPeriod !== select.value;
  });
  filter.hidden = false;
})();
</script>
"""
