# NeuroDaily

A daily **neuroscience & psychiatry** research digest that runs **both as a web app and as a standalone script**. Every morning at 08:00 it aggregates the latest literature, industry/regulatory progress, clinical & conference signals, and policy news — then renders a styled, **interactive HTML report** you can open in your browser.

Your **focus areas (disciplines), keywords, and journal watch-list are stored as a structured prompt**, so the whole system queries and labels content against exactly what you care about.

---

## What it aggregates

| Source | Type | Endpoint |
|---|---|---|
| **Top journals** | Papers | Journal RSS (Neuron, Nature, Nature Medicine, Mol Psychiatry, Nat Rev Neuro…) filtered by your interests |
| arXiv | Papers | `q-bio.NC`, `cs.NE` by category + keyword |
| PubMed | Papers | NCBI E-utilities (MeSH + Title/Abstract) |
| bioRxiv / medRxiv | Preprints | `api.biorxiv.org` detail API |
| openFDA | Drugs / Devices | New NDA/BLA approvals + 510(k) clearances |
| ClinicalTrials.gov | Trials / Conference | v2 API, recently updated studies |
| Policy & News RSS | Policy / institutional | NIMH, NIDA, NINDS, Nature feeds |

**Default focus areas**: Neuroscience, Psychiatry, Cognitive Neuroscience, Neurosurgery, Traumatic Brain Injury, Addiction, Epilepsy.

**Journal watch-list**: 28 leading journals (Nature, Neuron, Science, Cell, Nature Neuroscience, Molecular Psychiatry, JAMA Psychiatry, Journal of Neurosurgery, Epilepsia, etc.) — see [Top Journals](#top-journals-watch-list).

---

## Features

- **Two run modes**: FastAPI web app (dashboard + REST API) *and* a standalone CLI script.
- **Journal-paper sourcing**: top-journal RSS feeds are filtered by your research interests and surface as ★-badged papers at the *top of Latest Papers* — not just broad keyword hits.
- **Structured focus prompt**: config is editable (JSON) and serializes into a reusable `to_prompt()` string shown in the report (`config show`).
- **Collapsible cards**: each item is a click-to-expand card (native `<details>`/`<summary>`) with per-section **Expand / Collapse** toggles — collapsed by default for a scannable digest.
- **Top Journals section**: the report embeds a clickable grid of your watch-list journals (grouped by field), each linking to its official site.
- **Automatic tagging & dedupe**: every item is labeled by which discipline/keyword it matches; duplicates removed.
- **Per-source health panel**: shows whether each API succeeded, item count, and latency.
- **launchd scheduling**: register a macOS LaunchAgent to run at 08:00 daily.
- **Graceful degradation**: a failing source never breaks the report.

---

## Project layout

```
neurodaily/
├── pyproject.toml
├── config.example.json         # sample config (disciplines + keywords + journals); copy to config/config.json
├── neurodaily/
│   ├── config.py               # Config, Discipline, Journal, DEFAULT_CONFIG, JOURNALS(), to_prompt()
│   ├── models.py               # Item dataclass, tagging
│   ├── digest.py               # orchestrator: run() + save_report()
│   ├── render.py               # Jinja2 -> HTML
│   ├── cli.py                  # standalone script + launchd + config editor
│   ├── webapp.py               # FastAPI app
│   └── sources/                # arxiv, pubmed, biorxiv, fda, trials, rss
│       └── http.py             # shared HTTP helper with retries/timeouts
├── templates/report.html.j2    # styled HTML template (collapsible cards, journal grid)
└── output/                     # generated reports
```

---

## Quick start

```bash
cd ~/neurodaily

# 1. create venv + install (editable so `neurodaily` command works anywhere)
python3 -m venv .venv
.venv/bin/pip install -e .

# 2. write the default config (disciplines, keywords, journals)
.venv/bin/python -m neurodaily config init
#    (or copy config.example.json -> config/config.json and edit)

# 3a. generate a report (standalone script mode)
.venv/bin/python -m neurodaily run

# 3b. OR start the web app
.venv/bin/python -m neurodaily serve --port 8031
#    open http://127.0.0.1:8031
```

> A `neurodaily` console script is also installed, so `neurodaily run` / `neurodaily serve` work if the venv is on PATH.

---

## Config & the structured prompt

`config.json` holds your disciplines, keywords, and journal watch-list. Each discipline maps to source-specific query terms:

```json
{
  "profile": "neuro",
  "disciplines": [
    {
      "name": "Epilepsy",
      "arxiv_cats": ["q-bio.NC"],
      "mesh_terms": ["Epilepsy", "Seizures"],
      "bio_cats": ["neuroscience"],
      "keywords": ["epilepsy", "seizure", "antiepileptic"],
      "enabled": true
    }
  ],
  "global_keywords": ["brain", "neuro", "synapse", "EEG", "fMRI"],
  "journals": [
    { "name": "Neuron", "url": "https://www.cell.com/neuron",
      "rss": "https://www.cell.com/neuron/rss", "category": "neuroscience" }
  ],
  "sources": { "...": { "enabled": true, "max_results": 20, "lookback_days": 14 } },
  "scheduled": { "enabled": true, "hour": 8, "minute": 0 },
  "policy_feeds": ["https://..."],
  "output": { "dir": "~/neurodaily/output", "filename_format": "neurodaily_%Y-%m-%d.html" }
}
```

View the current focus prompt anytime:

```bash
.venv/bin/python -m neurodaily config show
```

It produces a single structured prompt you can paste into an LLM, share, or keep as documentation — it now also includes the **Top Journals** watch-list grouped by field.

---

## Top Journals (watch-list)

These are embedded in the report as a clickable grid and appear in the prompt. **Journals marked with an RSS feed are actively pulled** — their newest relevant papers are filtered by your research interests and surface first in **Latest Papers** (with a ★ badge). Edit `journals` in `config.json` to add/remove.

| Category | Journals (★ = active RSS → feeds Latest Papers) |
|---|---|
| **general** | Nature ★, Science, Cell, Nature Communications ★, Nature Medicine ★ |
| **neuroscience** | Neuron ★, Nature Neuroscience, Nature Reviews Neuroscience ★, Trends in Neurosciences, Journal of Neuroscience, eLife |
| **clinical_neuro** | Brain, Brain Research, Annals of Neurology, Neurology, The Lancet Neurology |
| **psychiatry** | Biological Psychiatry, Molecular Psychiatry ★, American Journal of Psychiatry, JAMA Psychiatry, World Psychiatry |
| **neurosurgery** | Journal of Neurosurgery, Neurosurgery |
| **epilepsy** | Epilepsia, Epilepsy & Behavior |
| **cognition** | Trends in Cognitive Sciences, NeuroImage |
| **translational** | Science Translational Medicine |

> Only feeds that return valid RSS are wired in (some publishers route through auth/redirects — those are kept as site links only). To ingest a journal's new articles, set its `rss` field to a working feed URL; the `journal` source will filter by your interests and surface matches as ★ top-journal papers in **Latest Papers**.

### Journal-sourced papers

The `journal` source reads each journal's `rss`, keeps entries matching your disciplines/keywords, and emits them as `paper` items sorted to the **top of Latest Papers** and labeled with a ★ `b-journal` badge plus the journal name. This makes the paper section reflect what's genuinely new in *leading journals for your fields* rather than only broad keyword search results (arXiv/PubMed/bioRxiv still run beneath, for completeness).

---

## Interactivity in the report

- **Collapsible cards**: every item is collapsed by default showing the title + metadata badges. Click the card header to expand the abstract, authors, and Read link.
- **Expand / Collapse all**: each section has two small buttons to open or fold every card in that section at once.
- **Journal grid**: hover to highlight; click a journal to open its site.

---

## Daily 08:00 scheduling (launchd)

```bash
# install the LaunchAgent (runs `python -m neurodaily run` at 08:00)
.venv/bin/python -m neurodaily launchd install

# preview the plist
.venv/bin/python -m neurodaily launchd show

# remove it
.venv/bin/python -m neurodaily launchd uninstall
```

The plist writes stdout/stderr to `~/neurodaily/output/launchd_*.log`. Verify with `launchctl list | grep neurodaily`.

> The generated plist uses **the venv python that invoked `install`** (`sys.executable`, e.g. `~/neurodaily/.venv/bin/python`), not a hardcoded `/usr/bin/python3` — this is what makes the scheduled job reliably find the package and its dependencies. Re-run `launchd install` from the venv after moving the project or changing the venv path.

---

## Web app API

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Dashboard (renders latest report) |
| `/api/run` | POST | Run a fresh digest (background) |
| `/api/status` | GET | Last run + per-source health |
| `/api/prompt` | GET | Structured focus prompt (JSON) |
| `/reports` | GET | List generated HTML reports |
| `/reports/{file}` | GET | Serve a saved report |

---

## Notes & caveats

- **External network**: sources require outbound HTTP. In restricted/proxied environments, a slow source degrades to "failed" — the rest still build.
- **Recent-item windows**: `lookback_days` per source controls how far back each query goes (defaults: 7–14 days for papers, 60 for FDA/trials).
- **openFDA search syntax**: date ranges use space-separated `TO` (a literal `+` is rejected by openFDA).
- **ClinicalTrials.gov**: 403s on custom User-Agents; the source sends `python-httpx` and uses short per-discipline queries to avoid HTTP 400.
- **RSS timeouts**: feeds are fetched with a timed HTTP client (not `feedparser.parse(url)`), which avoids a slow feed stalling the whole pool.

---

## Customizing

- **Add a discipline/keyword**: edit `config.json` (or `config init` then edit), re-run.
- **Add/edit journals**: edit the `journals` array in `config.json`.
- **Change output location/filename**: edit `output` in `config.json`.
- **Ingest journal RSS**: copy a journal's `rss` URL into `policy_feeds`.

---

## Troubleshooting

- **`launchd install` loads but job doesn't fire**: ensure `~/Library/LaunchAgents` exists and the plist `WorkingDirectory` points at this repo; check `output/launchd_stderr.log`.
- **Source returns 0 items**: raise `max_results` / `lookback_days`, or the focus filter was too narrow — loosen `keywords`/`mesh_terms`.
- **Journals section missing from report**: re-run `config init` (or `config show` — the loader auto-fills `journals` on load), then regenerate.
- **Cards not toggling**: the report is a static file — open it in a modern browser; `details`/`summary` are supported everywhere.
