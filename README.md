# NeuroDaily

> **中文** — 神经科学与精神病学方向的**每日情报 + AI 精读**系统。一台笔记本/小主机即可部署：抓取论文、预印本、临床试验、监管与创投动态，生成中文日报，每天早晨自动邮件送达全组。检索不消耗 token，AI 按需生成并缓存。
>
> **English** — A self-hosted daily digest for neuroscience & psychiatry. It aggregates journal RSS, PubMed, arXiv, bioRxiv, ClinicalTrials.gov, openFDA, policy feeds and VC/funding news, renders an interactive HTML report with an AI overview and a long-form "on this day" essay, and emails it to your team every morning. Retrieval is token-free; AI runs on demand and is cached.
>
> **Русский** — Автономная система ежедневной научной сводки по нейронаукам и психиатрии. Собирает RSS журналов, PubMed, arXiv, bioRxiv, ClinicalTrials.gov, openFDA, новости политики и венчурного финансирования, формирует интерактивный HTML-отчёт с ИИ-обзором и длинным эссе «в этот день», и каждое утро отправляет его по электронной почте. Поиск не расходует токены; ИИ работает по запросу и кэшируется.

[![ci](https://github.com/Koalalive/neurodaily/actions/workflows/ci.yml/badge.svg)](https://github.com/Koalalive/neurodaily/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)
![license](https://img.shields.io/badge/license-MIT-green)

---

## 中文

**Languages:** [中文](#中文) · [English](#english) · [Русский](#русский)

## 目录

- [核心特性](#核心特性)
- [快速开始](#快速开始)
- [Docker](#docker)
- [配置](#配置)
- [AI 每日摘要（可选）](#ai-每日摘要可选)
- [学科 profile 与 Agent 配置](#学科-profile-与-agent-配置)
- [邮件与 Webhook](#邮件与-webhook)
- [数据源](#数据源)
- [命令行](#命令行)
- [HTTP API](#http-api)
- [项目结构](#项目结构)
- [测试](#测试)
- [文档](#文档)
- [免责声明](#免责声明)

---

## 核心特性

| 能力 | 说明 |
|---|---|
| **七源聚合** | 期刊 RSS · PubMed · arXiv · bioRxiv · ClinicalTrials.gov · openFDA · 政策/新闻 |
| **创投/产业情报** | BCI 融资、neurotech 融资、MedTech Dive、Crunchbase（`kind=funding`） |
| **AI 每日摘要** | 800+ 条 → 约 900 字：研究进展 / 临床监管 / 产业创投 / 大事件（可选、带缓存） |
| **历史上的今天** | 936 篇约千字学科史长文，按日轮换，精确日/近邻/经典标注 |
| **交互式日报** | 折叠卡片、板块导航、来源健康面板、一键引用图谱 |
| **邮件日报** | 摘要正文 + 完整 HTML 附件；每天 08:00 自动；单机多收件人 |
| **桌面通知** | macOS / Linux 原生通知 |
| **Web 设置页 + TUI** | 收件人、SMTP 凭据、关注点、定时任务；无需手改 JSON |
| **Agent 可配置** | JSON 补丁 + schema 校验 + dry-run + profile；换学科零代码 |
| **配置化数据源** | 填一个 RSS/JSON 地址即可新增源，不写 Python |
| **导出** | JSON / BibTeX |
| **Webhook** | 飞书 / 企业微信 |
| **离线演示** | `neurodaily demo`，断网可完整演示 |
| **稳健性** | 并行抓取、0 条自动回退、单源失败降级、报告保留策略 |
| **可部署** | `scripts/start.sh` 一键启动；Docker / docker compose（镜像约 199MB） |

---

## 快速开始

### 本地（Python 3.12+）

```bash
git clone https://github.com/Koalalive/neurodaily.git
cd neurodaily

python3 -m venv .venv
.venv/bin/pip install -e .

.venv/bin/python -m neurodaily config init     # 写入默认 config/config.json
.venv/bin/python -m neurodaily run             # 跑一次，生成 output/*.html
```

一键启动 Web 应用（含设置页）：

```bash
scripts/start.sh
# http://127.0.0.1:8031
```

### 一键（macOS，无需命令行）

双击 `scripts/启动 NeuroDaily.command` → 自动启动服务并打开设置页。

日报页右上角：

- **⚙ 设置 / Settings** — 改推送（收件人、SMTP 授权码、飞书/企微）、检索时间窗口、史论语言
- **▶ Run now** — 跳到设置页；改完点 **保存并立即检索推送**，直接完成「检索 + 邮件/Webhook 推送」

离线演示（不联网）：

```bash
.venv/bin/python -m neurodaily demo --no-open
```

### Docker

```bash
docker build -t neurodaily:local .
docker run -d --name neurodaily -p 8031:8031 neurodaily:local
# http://127.0.0.1:8031
```

或：

```bash
docker compose up --build
```

详见 [`docs/DOCKER.md`](docs/DOCKER.md)。

---

## 配置

配置文件：`config/config.json`（gitignored）。查看/校验：

```bash
.venv/bin/python -m neurodaily config show
.venv/bin/python -m neurodaily config validate
.venv/bin/python -m neurodaily config describe     # Agent 可读的能力清单
.venv/bin/python -m neurodaily config schema --out schema.json
```

完整字段说明见 [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md)。

**最常改的三件事**

```jsonc
{
  "disciplines": [ { "name": "Epilepsy", "mesh_terms": ["Epilepsy"], "keywords": ["seizure"] } ],
  "sources": { "pubmed": { "enabled": true, "max_results": 500, "lookback_days": 2 } },
  "journals": [ { "name": "Neuron", "rss": "https://www.cell.com/...", "category": "neuroscience" } ]
}
```

---

## AI 每日摘要（可选）

需要用户自己的 OpenAI 兼容 API key（默认 DeepSeek）：

```bash
printf '%s' 'sk-...' > ~/.neurodaily_deepseek && chmod 600 ~/.neurodaily_deepseek
cp config/ai_summary.example.json config/ai_summary.json
.venv/bin/python -m neurodaily ai-summary --demo --force --save   # 预览
```

- 位置：报告**最顶部**（在「历史上的今天」之上），并写入邮件正文
- 缓存：同日同内容不重复调用（`output/ai_summary/`）
- 失败只降级，不影响报告生成与投递
- 提示词强制「不得编造日期/数字/人名/结论」

---

## 学科 profile 与 Agent 配置

为非默认学科单独建配置，不动主配置：

```bash
.venv/bin/python -m neurodaily profile new oncology
.venv/bin/python -m neurodaily config apply config/examples/oncology.patch.json --profile oncology --dry-run
.venv/bin/python -m neurodaily config apply config/examples/oncology.patch.json --profile oncology
.venv/bin/python -m neurodaily --profile oncology demo --no-open
```

补丁语义：**对象递归合并、数组整体替换、`null` 删除**。
非技术用户可以让 Agent 按 [`docs/AGENT_GUIDE.md`](docs/AGENT_GUIDE.md) 的协议完成换学科。

---

## 邮件与 Webhook

邮件（`config/email.json`）：

```bash
cp config/email.example.json config/email.json
printf '%s' '你的SMTP授权码' > ~/.neurodaily_smtp && chmod 600 ~/.neurodaily_smtp
.venv/bin/python -m neurodaily mail --test
.venv/bin/python -m neurodaily mail --send            # 立即跑一次并发送
.venv/bin/python -m neurodaily mail --send-latest     # 复用上次渲染重发
.venv/bin/python -m neurodaily mail --tui             # 收件人/凭据 TUI
```

- 主题模板：`神经病专家的厕所读物-{date} {weekday}`
- 正文：AI 摘要 + 历史上的今天 + 前 12 篇论文 + 其他板块计数
- 附件：完整 HTML 报告（`attach_max_mb` 超限自动跳过）

Webhook（`config/webhooks.json`）：

```bash
cp config/webhooks.example.json config/webhooks.json
.venv/bin/python -m neurodaily webhook --test
```

---

## 数据源

内置（`sources/*.py`）：`journal`、`arxiv`、`pubmed`、`biorxiv`、`fda_drugs`、`fda_devices`、`trials`、`policy`。

**配置化数据源**（不写代码）：

```json
{
  "sources": {
    "nci_news": { "type": "rss", "url": "https://...", "kind": "news",
                  "max_results": 30, "lookback_days": 7, "enabled": true },
    "my_api":   { "type": "json_api", "url": "https://...", "items_path": "data.items",
                  "map": { "title": "title", "url": "link", "summary": "abstract", "date": "published" },
                  "kind": "paper", "enabled": true }
  }
}
```

`kind` 决定归属板块：`paper / drug / device / trial / news / policy / conference / funding`。
可选 `filter_keywords` 做关键词过滤。

**创投源示例**（已内置在 `config.example.json`）：BCI 融资、neurotech 融资、MedTech Dive、Crunchbase。

---

## 命令行

| 命令 | 用途 |
|---|---|
| `neurodaily run [--demo] [--no-open] [--dedupe]` | 生成日报（`--demo` 离线） |
| `neurodaily demo` | 离线演示报告 |
| `neurodaily serve [--host] [--port] [--demo]` | Web 应用 / 设置页 |
| `neurodaily export --format json\|bibtex\|both [--demo]` | 数据导出 |
| `neurodaily ai-summary [--demo] [--force] [--save]` | 生成 AI 摘要 |
| `neurodaily mail --test\|--send\|--send-latest\|--tui\|--list\|--add\|--remove` | 邮件 |
| `neurodaily webhook --test [--demo]` | 飞书/企微 |
| `neurodaily config show\|init\|validate\|schema\|describe\|apply` | 配置 |
| `neurodaily profile new\|list\|path\|show` | 学科 profile |
| `neurodaily deepen --status\|--backend llm\|template` | 长文批量扩写 |
| `neurodaily launchd install\|uninstall\|show` | 定时任务 |
| `neurodaily history [--limit N]` | 运行历史 |

---

## HTTP API

| 路由 | 方法 | 用途 |
|---|---|---|
| `/` | GET | 仪表盘 |
| `/settings` | GET | 设置 GUI |
| `/api/config` | GET/POST | 读取/保存配置（带 schema 校验） |
| `/api/config/reset` | POST | 重置默认 |
| `/api/run` | POST | 后台跑一次 |
| `/api/status` | GET | 状态 + 源健康 |
| `/api/prompt` | GET | 结构化 Focus Prompt |
| `/reports` `/reports/{file}` | GET | 报告列表/读取 |
| `/history` `/history/{id}` `/api/history` | GET/DELETE | 历史 |
| `/api/launchd/status\|install\|uninstall` | GET/POST | 定时任务 |

---

## 项目结构

```
neurodaily/
├── neurodaily/
│   ├── cli.py            # 命令入口
│   ├── config.py         # Config dataclass / load / save
│   ├── config_ops.py     # 补丁、profile、schema（Agent 配置）
│   ├── schema.py         # pydantic 校验
│   ├── digest.py         # 编排：抓取→标签→去重→排序→板块
│   ├── models.py         # Item + 标签
│   ├── sources/          # 各数据源 + 通用 RSS/JSON
│   ├── onthisday.py      # 历史上的今天（975 条，936 篇长文）
│   ├── deepen.py         # 长文批量扩写（LLM/模板 + 缓存）
│   ├── ai_summary.py     # AI 每日摘要（带缓存）
│   ├── render.py         # HTML 渲染 + 注入
│   ├── templates/        # Jinja2 模板
│   ├── mailer.py         # 邮件渲染/发送
│   ├── mail_tui.py       # 收件人/凭据 TUI
│   ├── webhooks.py       # 飞书/企微
│   ├── exporters.py      # JSON / BibTeX
│   ├── demo.py           # 离线演示数据
│   ├── webapp.py         # FastAPI
│   ├── settings_page.py  # 设置页 HTML
│   └── history.py        # SQLite 运行历史
├── config/examples/      # 学科补丁示例（oncology）
├── docs/                 # 架构 / 配置 / Docker / 测试 / Agent 指南
├── scripts/              # start.sh / test_all.sh / deepen / hooks
├── tests/                # 32 项 unittest
├── Dockerfile
└── docker-compose.yml
```

---

## 测试

```bash
bash scripts/test_all.sh      # 编译 + 32 项单元测试 + 配置 + demo + 导出 + profile
make test                     # 同上
```

覆盖：配置校验、补丁语义、profile 隔离、渲染置顶、邮件（空收件人/附件上限）、TUI 增删、报告裁剪、366 天长文覆盖、通用 RSS/JSON 源、AI 摘要缓存、路由与安全边界、Docker 容器。

详见 [`docs/TESTING.md`](docs/TESTING.md)。CI：GitHub Actions（Python 3.12/3.13）。

---

## 文档

| 文档 | 内容 |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 架构、数据流、模块职责、扩展点 |
| [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) | 全部配置字段与示例 |
| [`docs/DOCKER.md`](docs/DOCKER.md) | 构建/运行/compose/推送 Docker Hub |
| [`docs/TESTING.md`](docs/TESTING.md) | 测试矩阵、CI、已知未覆盖项 |
| [`docs/AGENT_GUIDE.md`](docs/AGENT_GUIDE.md) | Agent 引导换学科的协议 |
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | 运维手册（启停/调度/排障/维护记录） |

---

## 免责声明

- 仅聚合**公开**文献与新闻元数据；不存储全文、不绕过付费墙。
- AI 摘要与长文可能出错，**仅供科研参考，不构成医疗建议**。
- 请遵守各数据源的使用条款；邮件/Webhook 凭据仅保存在本机（600 权限）。


---

## English

### What it is

NeuroDaily is a **self-hosted daily digest for neuroscience and psychiatry**. It aggregates journal RSS, PubMed, arXiv, bioRxiv, ClinicalTrials.gov, openFDA, policy feeds and VC/funding news, filters by your focus, renders an interactive HTML report with an **AI overview** and a long-form **"on this day"** essay, and emails it to your team every morning.

- **Retrieval is token-free**; AI runs on demand and is cached.
- **Journal metrics**: OpenAlex auto-fetch (2yr mean citedness, h-index); official JCR IF / quartile and CAS partition can be imported.
- **Local-first**: one laptop/mini-PC, data never leaves the machine.
- **Agent-configurable**: switch disciplines with JSON patches (`profile` + `config apply`).

### Quick start

```bash
git clone https://github.com/Koalalive/neurodaily.git
cd neurodaily
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m neurodaily config init
.venv/bin/python -m neurodaily run --no-open
# web UI + settings:
scripts/start.sh          # http://127.0.0.1:8031
```

No-CLI flow: double-click `scripts/启动 NeuroDaily.command` (macOS), or open the report →
**⚙ Settings** → edit push/windows/language → **Save & run now** (fetch + email/webhook).

Offline demo:

```bash
.venv/bin/python -m neurodaily demo --no-open
```

### Docker

```bash
docker build -t neurodaily:local .
docker run -d --name neurodaily -p 8031:8031 \
  -v "$PWD/config:/app/neurodaily/config" \
  -v "$PWD/output:/app/neurodaily/output" \
  neurodaily:local
```

Prebuilt image: `docker pull koalalive/neurodaily:latest`.

No-CLI flow: open the report → **⚙ Настройки** → изменить получателей/окна/язык →
**Сохранить и запустить** (сбор + почта/webhook).

### Configuration

- Main: `config/config.json` (gitignored)
- Email: `config/email.json`; AI: `config/ai_summary.json`; webhooks: `config/webhooks.json`
- Validate: `neurodaily config validate`
- Patch: `neurodaily config apply patch.json --dry-run` (objects merge, lists replace, null deletes)
- Disciplines: `neurodaily profile new oncology` → `--profile oncology`

### AI overview (optional)

```bash
printf '%s' 'sk-...' > ~/.neurodaily_deepseek && chmod 600 ~/.neurodaily_deepseek
cp config/ai_summary.example.json config/ai_summary.json
.venv/bin/python -m neurodaily ai-summary --force --save
```

Top of the report + email body; cached; failures never break the report.

### Email

```bash
printf '%s' 'SMTP-CODE' > ~/.neurodaily_smtp && chmod 600 ~/.neurodaily_smtp
.venv/bin/python -m neurodaily mail --test
.venv/bin/python -m neurodaily mail --send
.venv/bin/python -m neurodaily mail --tui     # manage recipients/credentials
```

### Docs

ARCHITECTURE · CONFIGURATION · DOCKER · DOCKER_AGENT · TESTING · AGENT_GUIDE · GITHUB_ACTIONS_AGENT — see [`docs/`](docs/).

### Tests

```bash
bash scripts/test_all.sh      # 35 unit tests + compile + config + demo + export + profile
```

---

## Русский

### Что это

NeuroDaily — это **автономная система ежедневной научной сводки по нейронаукам и психиатрии**. Она собирает RSS журналов, PubMed, arXiv, bioRxiv, ClinicalTrials.gov, openFDA, новости политики и венчурного финансирования, фильтрует по вашим интересам, формирует интерактивный HTML-отчёт с **ИИ-обзором** и длинным эссе **«в этот день»**, и каждое утро отправляет его по электронной почте.

- **Поиск не расходует токены**; ИИ работает по запросу и кэшируется.
- **Метрики журналов**: автоматически из OpenAlex (2yr mean citedness, h-index); официальные JCR IF / квартиль и раздел CAS можно импортировать.
- **Локальный запуск**: один ноутбук/мини-ПК, данные не покидают машину.
- **Настраивается агентом**: смена дисциплины через JSON-патчи (`profile` + `config apply`).

### Быстрый старт

```bash
git clone https://github.com/Koalalive/neurodaily.git
cd neurodaily
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m neurodaily config init
.venv/bin/python -m neurodaily run --no-open
scripts/start.sh          # http://127.0.0.1:8031
```

Демо без сети:

```bash
.venv/bin/python -m neurodaily demo --no-open
```

### Docker

```bash
docker build -t neurodaily:local .
docker run -d --name neurodaily -p 8031:8031 \
  -v "$PWD/config:/app/neurodaily/config" \
  -v "$PWD/output:/app/neurodaily/output" \
  neurodaily:local
```

Готовый образ: `docker pull koalalive/neurodaily:latest`.

### Конфигурация

- Основная: `config/config.json` (gitignored)
- Почта: `config/email.json`; ИИ: `config/ai_summary.json`; webhooks: `config/webhooks.json`
- Проверка: `neurodaily config validate`
- Патч: `neurodaily config apply patch.json --dry-run` (объекты сливаются, массивы заменяются, null удаляет)
- Дисциплины: `neurodaily profile new oncology` → `--profile oncology`

### ИИ-обзор (опционально)

```bash
printf '%s' 'sk-...' > ~/.neurodaily_deepseek && chmod 600 ~/.neurodaily_deepseek
cp config/ai_summary.example.json config/ai_summary.json
.venv/bin/python -m neurodaily ai-summary --force --save
```

Вверху отчёта и в письме; кэшируется; ошибки не ломают отчёт.

### Почта

```bash
printf '%s' 'SMTP-CODE' > ~/.neurodaily_smtp && chmod 600 ~/.neurodaily_smtp
.venv/bin/python -m neurodaily mail --test
.venv/bin/python -m neurodaily mail --send
.venv/bin/python -m neurodaily mail --tui
```

### Документация

ARCHITECTURE · CONFIGURATION · DOCKER · DOCKER_AGENT · TESTING · AGENT_GUIDE · GITHUB_ACTIONS_AGENT — см. [`docs/`](docs/).

### Тесты

```bash
bash scripts/test_all.sh      # 35 модульных тестов + компиляция + конфиг + демо + экспорт
```
