# Configuration

> [中文](../CONFIGURATION.md) · **English** · [Русский](../ru/CONFIGURATION.md)

Every field has a default; **all new fields are optional**, old configs keep working.

## 1. Files

| File | Purpose | Committed |
|---|---|---|
| `config/config.json` | Main config (profile, sources, journals, output, schedule, windows) | No |
| `config/profiles/<name>.json` | Isolated discipline profile | No |
| `config/email.json` | SMTP, recipients, subject, attachment | No |
| `config/ai_summary.json` | LLM provider/model/limits | No |
| `config/webhooks.json` | Feishu / WeCom webhooks | No |
| `~/.neurodaily_smtp` | SMTP app password (mode 600) | No |
| `~/.neurodaily_deepseek` | LLM API key (mode 600) | No |

## 2. Main config (excerpt)

```json
{
  "profile": "neuro",
  "windows": {
    "daily_paper_hours": 36,
    "manual_paper_hours": 168,
    "other_lookback_days": 7
  },
  "scheduled": {
    "enabled": true,
    "hour": 8,
    "minute": 0,
    "on_this_day": {"enabled": true, "notify": true, "lang": "zh"}
  },
  "journals": [{"name": "Nature", "url": "https://www.nature.com/"}]
}
```

- `windows.daily_paper_hours` — papers kept for scheduled runs (default **36 h**).
- `windows.manual_paper_hours` — papers kept for `run --mode manual` (default 168 h).
- `windows.other_lookback_days` — non-paper items (trials/policy/industry).
- `on_this_day.lang` — `zh` | `en` | `ru`; CLI override: `run --lang en`.

## 3. Push settings

Email (`config/email.json`): `enabled`, `to` (list), `smtp_host`, `smtp_port`, `use_ssl`,
`username`, `from`, `from_name`, `subject_template`, `attach_report`, `attach_max_mb`,
`summary_papers`, `summary_chars`.

Webhooks (`config/webhooks.json`): `feishu`, `wecom`, `max_items`.

The GUI (`/settings`) edits all of the above and can store the SMTP password via
`POST /api/push/password` (writes `~/.neurodaily_smtp`, mode 600).

## 4. Journal metrics

- Automatic: `output/journal_metrics_auto.json` from OpenAlex by ISSN (TTL 1 day).
- Official: `config/journal_metrics.json` via `neurodaily metrics import file.csv`
  (columns: `name,if,jcr,cas`).
- Official values win; otherwise `OA 2yr x.x` is shown and explicitly **not** labelled as the JCR IF.

## 5. Manual run without CLI

Open the report → **⚙ 设置 / Settings** → edit recipients/windows/language →
**保存并立即检索推送** (save + fetch + email/webhook). On macOS you can also
double-click `scripts/启动 NeuroDaily.command` to start the server and open settings.
