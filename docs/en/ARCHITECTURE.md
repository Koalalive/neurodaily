# Architecture

> [中文](../ARCHITECTURE.md) · **English** · [Русский](../ru/ARCHITECTURE.md)

Goal: **one machine, one deploy, a readable daily digest every day**. Every stage degrades gracefully; no single source failure may erase the report.

## 1. Data flow

```
launchd / cron / CLI / Web
        └─> digest.run(mode="daily"|"manual")
              ├─ sources: journal RSS, PubMed, arXiv, bioRxiv,
              │            ClinicalTrials.gov, openFDA, policy RSS, funding RSS
              ├─ tag → dedupe → rank → section split
              ├─ paper window filter (36 h daily / 168 h manual)
              ├─ journal metrics (OpenAlex auto + official CSV import)
              ├─ On-This-Day (zh/en/ru, LLM translation cached)
              └─ render HTML → output/ → mail + webhooks
```

## 2. Modules

| Module | Responsibility |
|---|---|
| `digest.py` | Orchestration, windows, dedupe, ranking, sections, `save_report` |
| `sources.py` | Source registry and fetchers; config-defined sources |
| `journal_metrics.py` | OpenAlex `2yr_mean_citedness` + official import; TTL refresh |
| `onthisday.py` | Landmark events, fallback rotation, LLM translation (zh/en/ru) |
| `render.py` / `templates/` | Jinja HTML report, metrics badges, i18n labels |
| `mailer.py` | SMTP STARTTLS/SSL, summary + attachment, subject template |
| `webhooks.py` | Feishu / WeCom push |
| `webapp.py` | Dashboard, settings API, manual run, `/api/push` |
| `settings_page.py` | Single-page settings GUI (config + push + schedule) |
| `cli.py` | `run`, `demo`, `serve`, `metrics`, `export`, `deepen`, … |

## 3. Degradation

- A source failure is recorded in `health` and does not abort the run.
- Missing LLM key → explainable Chinese-only fallback; no crash.
- Missing JCR/CAS data → OpenAlex 2-year mean citedness is shown and labelled as **not** the JCR IF.
- Email/Webhook failures are non-fatal; the report file is always written first.

## 4. Extension points

- Add a source: register a fetcher in `sources.py` or add a `sources[]` entry in `config.json`.
- Add a journal: add it to `journals[]`; metrics are fetched by ISSN.
- Add a language: extend `OTD_LABELS` / prompts in `onthisday.py`.
