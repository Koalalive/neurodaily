# NeuroDaily

> **Short description（≤100 字符）**
> `NeuroDaily｜神经科学每日情报+AI精读｜Нейродайджест`

---

## 中文

### 简介

NeuroDaily 是一个**自托管的神经科学与精神病学每日情报系统**。它聚合期刊 RSS、PubMed、arXiv、bioRxiv、ClinicalTrials.gov、openFDA、政策新闻与创投动态，按你的关注点过滤，生成带 **AI 摘要**与**学科史长文**的交互式 HTML 日报，并在每天早晨通过邮件送达全组。**检索不消耗 token**，AI 按需生成并缓存。

### 快速开始

```bash
docker run -d --name neurodaily \
  -p 127.0.0.1:8031:8031 \
  -v "$PWD/config:/app/neurodaily/config" \
  -v "$PWD/output:/app/neurodaily/output" \
  --restart unless-stopped \
  koalalive/neurodaily:latest
```

打开 <http://127.0.0.1:8031>。

离线演示（不联网）：

```bash
docker run --rm -p 127.0.0.1:8031:8031 -e NEURODAILY_DEMO=1 koalalive/neurodaily:latest
```

### 卷与环境变量

| 项 | 说明 |
|---|---|
| `/app/neurodaily/config` | 配置、profile、邮件/AI/Webhook 配置 |
| `/app/neurodaily/output` | HTML 日报、历史库、缓存 |
| `NEURODAILY_DEMO=1` | 仪表盘使用离线演示数据 |
| `NEURODAILY_LLM_API_KEY` | 可选：AI 摘要 key |
| `NEURODAILY_SMTP_PASSWORD` | 可选：SMTP 授权码 |

### 标签

`latest` · `YYYYMMDD`

### 链接

- 源码与文档：<https://github.com/Koalalive/neurodaily>
- 架构：<https://github.com/Koalalive/neurodaily/blob/main/docs/ARCHITECTURE.md>
- 配置：<https://github.com/Koalalive/neurodaily/blob/main/docs/CONFIGURATION.md>

---

## English

### Overview

NeuroDaily is a **self-hosted daily digest for neuroscience and psychiatry**. It aggregates journal RSS, PubMed, arXiv, bioRxiv, ClinicalTrials.gov, openFDA, policy feeds and VC/funding news, filters by your focus, renders an interactive HTML report with an **AI overview** and a long-form **"on this day"** essay, and emails it to your team every morning. **Retrieval is token-free**; AI runs on demand and is cached.

### Quick start

```bash
docker run -d --name neurodaily \
  -p 127.0.0.1:8031:8031 \
  -v "$PWD/config:/app/neurodaily/config" \
  -v "$PWD/output:/app/neurodaily/output" \
  --restart unless-stopped \
  koalalive/neurodaily:latest
```

Open <http://127.0.0.1:8031>.

Offline demo:

```bash
docker run --rm -p 127.0.0.1:8031:8031 -e NEURODAILY_DEMO=1 koalalive/neurodaily:latest
```

### Volumes & environment

| Item | Purpose |
|---|---|
| `/app/neurodaily/config` | config, profiles, email/AI/webhook settings |
| `/app/neurodaily/output` | HTML reports, history DB, caches |
| `NEURODAILY_DEMO=1` | serve offline demo data |
| `NEURODAILY_LLM_API_KEY` | optional: AI summary key |
| `NEURODAILY_SMTP_PASSWORD` | optional: SMTP password |

### Tags

`latest` · `YYYYMMDD`

### Links

- Source & docs: <https://github.com/Koalalive/neurodaily>
- Architecture: <https://github.com/Koalalive/neurodaily/blob/main/docs/ARCHITECTURE.md>
- Configuration: <https://github.com/Koalalive/neurodaily/blob/main/docs/CONFIGURATION.md>

---

## Русский

### Обзор

NeuroDaily — это **автономная система ежедневной научной сводки по нейронаукам и психиатрии**. Она собирает RSS журналов, PubMed, arXiv, bioRxiv, ClinicalTrials.gov, openFDA, новости политики и венчурного финансирования, фильтрует по вашим интересам, формирует интерактивный HTML-отчёт с **ИИ-обзором** и длинным эссе **«в этот день»**, и каждое утро отправляет его команде по электронной почте. **Поиск не расходует токены**; ИИ работает по запросу и кэшируется.

### Быстрый старт

```bash
docker run -d --name neurodaily \
  -p 127.0.0.1:8031:8031 \
  -v "$PWD/config:/app/neurodaily/config" \
  -v "$PWD/output:/app/neurodaily/output" \
  --restart unless-stopped \
  koalalive/neurodaily:latest
```

Откройте <http://127.0.0.1:8031>.

Демо без сети:

```bash
docker run --rm -p 127.0.0.1:8031:8031 -e NEURODAILY_DEMO=1 koalalive/neurodaily:latest
```

### Тома и переменные

| Путь / переменная | Назначение |
|---|---|
| `/app/neurodaily/config` | конфигурация, профили, настройки почты/ИИ/webhook |
| `/app/neurodaily/output` | HTML-отчёты, история, кэш |
| `NEURODAILY_DEMO=1` | демонстрационные данные без сети |
| `NEURODAILY_LLM_API_KEY` | ключ для ИИ-обзора (опционально) |
| `NEURODAILY_SMTP_PASSWORD` | пароль SMTP (опционально) |

### Теги

`latest` · `YYYYMMDD`

### Ссылки

- Исходный код и документация: <https://github.com/Koalalive/neurodaily>
- Архитектура: <https://github.com/Koalalive/neurodaily/blob/main/docs/ARCHITECTURE.md>
- Конфигурация: <https://github.com/Koalalive/neurodaily/blob/main/docs/CONFIGURATION.md>
