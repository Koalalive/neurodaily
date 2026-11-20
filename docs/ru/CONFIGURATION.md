# Конфигурация

> [中文](../CONFIGURATION.md) · [English](../en/CONFIGURATION.md) · **Русский**

У каждого поля есть значение по умолчанию; **новые поля необязательны**, старые конфиги работают без миграции.

## 1. Файлы

| Файл | Назначение | В git |
|---|---|---|
| `config/config.json` | Основной конфиг (профиль, источники, журналы, вывод, расписание, окна) | Нет |
| `config/profiles/<name>.json` | Изолированный профиль дисциплины | Нет |
| `config/email.json` | SMTP, получатели, тема, вложение | Нет |
| `config/ai_summary.json` | Провайдер/модель/лимиты LLM | Нет |
| `config/webhooks.json` | Feishu / WeCom | Нет |
| `~/.neurodaily_smtp` | Пароль приложения SMTP (600) | Нет |
| `~/.neurodaily_deepseek` | Ключ LLM (600) | Нет |

## 2. Основной конфиг (фрагмент)

```json
{
  "profile": "neuro",
  "windows": {"daily_paper_hours": 36, "manual_paper_hours": 168, "other_lookback_days": 7},
  "scheduled": {"enabled": true, "hour": 8, "minute": 0,
                "on_this_day": {"enabled": true, "notify": true, "lang": "zh"}}
}
```

- `windows.daily_paper_hours` — окно статей для планового запуска (по умолчанию **36 ч**).
- `windows.manual_paper_hours` — окно для `run --mode manual` (168 ч).
- `windows.other_lookback_days` — не-статьи (испытания/политика/индустрия).
- `on_this_day.lang` — `zh` | `en` | `ru`; переопределение: `run --lang en`.

## 3. Пуш-настройки

Почта (`config/email.json`): `enabled`, `to`, `smtp_host`, `smtp_port`, `use_ssl`,
`username`, `from`, `from_name`, `subject_template`, `attach_report`, `attach_max_mb`,
`summary_papers`, `summary_chars`.

Webhook (`config/webhooks.json`): `feishu`, `wecom`, `max_items`.

GUI (`/settings`) редактирует всё это и сохраняет пароль SMTP через
`POST /api/push/password` (пишет `~/.neurodaily_smtp`, режим 600).

## 4. Метрики журналов

- Авто: `output/journal_metrics_auto.json` из OpenAlex по ISSN (TTL 1 день).
- Официально: `config/journal_metrics.json` через `neurodaily metrics import file.csv`.
- Официальные значения приоритетны; иначе показывается `OA 2yr x.x` с пометкой, что это **не** JCR IF.

## 5. Ручной запуск без CLI

Открыть отчёт → **⚙ 设置 / Settings** → изменить получателей/окна/язык →
**保存并立即检索推送** (сохранить +检索 + почта/webhook). В macOS можно дважды
щёлкнуть `scripts/启动 NeuroDaily.command`, чтобы запустить сервер и открыть настройки.
