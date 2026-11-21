# 配置参考

> **中文** — 全部配置字段、示例与常用改法。
> **English** — Full configuration reference with examples and recipes.
> **Русский** — Полный справочник конфигурации с примерами.

> [中文](CONFIGURATION.md) · [English](en/CONFIGURATION.md) · [Русский](ru/CONFIGURATION.md)

> 所有配置都有默认值；**新增字段均可选**，旧配置文件无需迁移即可运行。

## 1. 文件位置

| 文件 | 作用 | 是否提交 |
|---|---|---|
| `config/config.json` | 主配置（学科、源、期刊、输出、定时） | 否（gitignore） |
| `config/profiles/<name>.json` | 独立学科配置 | 否 |
| `config/email.json` | 邮件（SMTP、收件人、主题、附件） | 否 |
| `config/ai_summary.json` | AI 摘要（provider、模型、上限） | 否 |
| `config/webhooks.json` | 飞书/企微 webhook | 否 |
| `~/.neurodaily_smtp` | SMTP 授权码（600） | 否 |
| `~/.neurodaily_deepseek` | LLM API key（600） | 否 |

模板：`config.example.json`、`config/email.example.json`、`config/ai_summary.example.json`、`config/webhooks.example.json`。

---

## 2. `config.json` 顶层

| 字段 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `version` | int | `2` | 配置版本 |
| `profile` | str | `"neuro"` | 配置档名称（仅标签） |
| `disciplines` | list | 7 个学科 | 关注方向，**至少 1 个** |
| `global_keywords` | list[str] | 见默认 | 跨源通用关键词 |
| `sources` | dict | 8 个内置源 | 数据源与参数 |
| `journals` | list | 28 本 | 顶级期刊观察列表 |
| `policy_feeds` | list[str] | 机构/新闻 RSS | 政策与新闻源 |
| `output` | dict | — | 输出目录、格式、保留策略 |
| `scheduled` | dict | — | 定时任务与「历史上的今天」开关 |
| `windows` | dict | — | 手动、定时及各类内容的回看时长 |
| `search` | dict | — | 可选的高级检索表达式、检索集合、期刊过滤及排序 |

### 分享检索配置

在桌面端设置里点击 **导出已保存的配置**，在系统保存窗口中选择目录和文件名。文件以
`{"format":"neurodaily.profile","version":1,"config":{…}}` 包装学科、关键词、检索表达式、来源、期刊和回看窗口。输出目录、定时设置、通知收件人、Webhook 和 AI 授权等留在本机。来源网址中的用户名、密码和常见授权参数会去掉。分享前可检查网址和检索词。

在 **导入配置文件** 里选择共享文件或旧版 `config.json`，核对预览后应用。导入会替换当前检索设置并保留本机的定时和输出设置。

### 2.1 `disciplines[]`

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | str | 学科名（必填） |
| `arxiv_cats` | list[str] | arXiv 分类，如 `q-bio.NC` |
| `mesh_terms` | list[str] | PubMed MeSH，如 `Epilepsy` |
| `bio_cats` | list[str] | bioRxiv 分类 |
| `keywords` | list[str] | 自由关键词 |
| `enabled` | bool | 是否启用 |

> 校验规则：`enabled=true` 时，`keywords/mesh_terms/arxiv_cats/bio_cats` 至少有一个非空。

示例：

```json
{
  "name": "Epilepsy",
  "arxiv_cats": ["q-bio.NC"],
  "mesh_terms": ["Epilepsy", "Seizures"],
  "bio_cats": ["neuroscience"],
  "keywords": ["epilepsy", "seizure", "antiepileptic"],
  "enabled": true
}
```

### 2.2 `sources`

#### 内置源

| key | 说明 |
|---|---|
| `journal` | 顶级期刊 RSS（按关注点过滤） |
| `arxiv` | arXiv API |
| `pubmed` | NCBI E-utilities |
| `biorxiv` | bioRxiv / medRxiv |
| `fda_drugs` | openFDA 新药批准 |
| `fda_devices` | openFDA 510(k) |
| `trials` | ClinicalTrials.gov v2 |
| `policy` | 政策/新闻 RSS（`policy_feeds`） |

通用字段：

```json
{ "enabled": true, "max_results": 500, "lookback_days": 2 }
```

#### 配置化源（无需写代码）

| 字段 | 适用 | 说明 |
|---|---|---|
| `type` | 必填 | `rss` 或 `json_api` |
| `url` | 必填 | 源地址 |
| `kind` | 可选 | `paper/drug/device/trial/news/policy/conference/funding` |
| `max_results` | 可选 | 本地上限 |
| `lookback_days` | 可选 | 按发布日期过滤 |
| `filter_keywords` | 可选 | 标题+摘要任一命中才保留 |
| `items_path` | JSON 源 | 列表在响应中的路径，如 `data.items` |
| `map` | JSON 源 | 字段映射：`title/url/summary/date/doi/authors` |

RSS 示例：

```json
"neuro_vc_bci": {
  "type": "rss",
  "url": "https://news.google.com/rss/search?q=%22brain-computer+interface%22+funding+when:7d&hl=en-US&gl=US&ceid=US:en",
  "kind": "funding",
  "max_results": 25,
  "lookback_days": 7,
  "enabled": true
}
```

JSON API 示例：

```json
"my_api": {
  "type": "json_api",
  "url": "https://api.example.org/items",
  "items_path": "data.items",
  "map": {"title": "title", "url": "link", "summary": "abstract",
          "date": "published", "doi": "doi", "authors": "authors"},
  "kind": "paper",
  "max_results": 50,
  "enabled": true
}
```

> 提示：Google News 按相关度排序，务必在查询里加 `when:7d`（或更大窗口），否则会被 `lookback_days` 全部过滤。

### 2.3 `journals[]`

```json
{ "name": "Neuron", "url": "https://www.cell.com/neuron",
  "rss": "https://www.cell.com/action/showFeed?type=etoc&feed=rss&jc=neuron",
  "category": "neuroscience",
  "impact_factor": 14.7, "jcr": "Q1", "cas": "1区", "year": 2024 }
```

- 有 `rss` 的期刊会被抓取并置顶到论文区（★ 标记）
- 没有可靠 RSS 的期刊保留为站点链接
- `impact_factor`（别名 `if`）/ `jcr` / `cas` / `year` 可选，用于**硬编码期刊指标**
- 指标优先级：**用户配置 `journals[]` > `config/journal_metrics.json` 官方导入 > OpenAlex 自动 `OA 2yr`**
- 设置页的期刊行同样提供 `IF / JCR / 中科院` 输入框

### 2.4 `output`

| 字段 | 默认 | 说明 |
|---|---|---|
| `dir` | `~/neurodaily/output` | 报告目录 |
| `filename_format` | `neurodaily_%Y-%m-%d_%H%M%S.html` | 文件名格式 |
| `open_on_finish` | `true` | 跑完自动打开 |
| `extra_formats` | `[]` | 额外导出：`["json","bibtex"]` |
| `keep_reports` | `60` | 保留最近 N 份报告（引用中的不删） |

### 2.5 `scheduled`

| 字段 | 默认 | 说明 |
|---|---|---|
| `enabled` | CLI `true`，桌面首次安装 `false` | 是否启用定时 |
| `hour` / `minute` | `8` / `0` | 每日运行时间 |
| `on_this_day` | `{"enabled":true,"notify":true}` | 「历史上的今天」与桌面通知 |
| `launchd` | `{label,stdout,stderr}` | macOS LaunchAgent 参数 |

```json
"scheduled": {
  "enabled": true, "hour": 8, "minute": 0,
  "on_this_day": {"enabled": true, "notify": true},
  "launchd": {"label": "com.neurodaily.daily"}
}
```

Windows、macOS 和 Linux 桌面版在设置里启用定时并保存，按系统本地时间运行。最小化时仍会检索。重新启动或唤醒后可补跑当天未完成的时段。每个学科与设定时段当天成功一次后，重启不会重复执行同一时段。设置页显示下一次运行时间和最近结果。若所有启用的来源均失败，当天约五分钟后重试。完全退出应用会停止服务。

定时检索期间，日报页的 **Run now** 和手动检索页的开始按钮会显示 **Running…**，任务结束后恢复可点。

### 2.6 `policy_feeds` 与自定义 RSS

`policy_feeds` 是 URL 列表，全部以 `kind=news` 进入「政策/新闻」板块：

```json
"policy_feeds": ["https://www.nature.com/subjects/neuroscience.rss"]
```

如需指定板块（论文/试验/Funding），在 `sources` 里加一个自定义 RSS：

```json
"sources": {
  "my_rss": {
    "type": "rss",
    "url": "https://example.org/feed.xml",
    "kind": "funding",
    "max_results": 20,
    "lookback_days": 7,
    "filter_keywords": ["neuro", "brain"]
  }
}
```

- `kind` 映射：`paper`→最新论文；`trial`/`conference`→临床试验；`funding`/`drug`/`device`/`industry`→产业/Funding；`news`/`policy`→政策/新闻。
- 不能与内置源重名（`journal`/`arxiv`/`pubmed`/`biorxiv`/`fda_drugs`/`fda_devices`/`trials`/`policy`）。
- 设置页 **Policy / news RSS → + Add RSS** 等价于往 `policy_feeds` 追加。
- 配置每次运行重新读取，保存后下一次运行生效，无需重启。

---

## 3. Profile 与补丁

```bash
neurodaily profile new oncology
neurodaily config apply patch.json --profile oncology --dry-run
neurodaily config apply patch.json --profile oncology
neurodaily --profile oncology run --no-open
```

**补丁语义**

| 类型 | 行为 |
|---|---|
| 对象 | 递归合并 |
| 数组 | **整体替换** |
| 标量 | 覆盖 |
| `null` | 删除该键 |

示例补丁见 `config/examples/oncology.patch.json`。

---

## 4. `email.json`

| 字段 | 默认 | 说明 |
|---|---|---|
| `enabled` | `true` | 是否发送 |
| `smtp_host` | `smtp.sjtu.edu.cn` | SMTP 服务器 |
| `smtp_port` | `587` | 端口 |
| `use_ssl` | `false` | `true`=SSL(465)，`false`=STARTTLS(587) |
| `smtp_timeout` | `120` | 秒 |
| `username` / `from` | — | 发件账号（二者通常一致） |
| `from_name` | `NeuroDaily` | 显示名 |
| `to` | `[]` | 收件人列表 |
| `password_env` | `NEURODAILY_SMTP_PASSWORD` | 环境变量名 |
| `password_file` | `~/.neurodaily_smtp` | 密码文件（600） |
| `subject_template` | `神经病专家的厕所读物-{date} {weekday}` | 主题模板 |
| `body_mode` | `summary` | `summary` 摘要 / `full` 全量 |
| `attach_report` | `true` | 附完整 HTML |
| `attach_max_mb` | `8` | 附件上限 |
| `summary_papers` | `12` | 摘要正文论文数 |
| `summary_chars` | `420` | 史论摘录字数 |

---

## 5. `ai_summary.json`

| 字段 | 默认 | 说明 |
|---|---|---|
| `enabled` | `true` | 是否生成 |
| `base_url` | `https://api.deepseek.com/v1` | DeepSeek 官方 OpenAI 兼容地址 |
| `model` | `deepseek-flash` | DeepSeek 官方模型名 |
| `api_key_env` | `DEEPSEEK_API_KEY` | 环境变量名 |
| `api_key_file` | `~/.neurodaily_deepseek` | key 文件（600） |
| `max_papers` | `30` | 输入里包含的论文数 |
| `max_other` | `8` | 每个其他板块的条数 |
| `max_input_chars` | `8000` | 输入截断 |

可用 `--base-url` / `--model` / `--api-key` 临时覆盖（测试用），但日常建议用文件。

---

## 6. `webhooks.json`

```json
{ "feishu": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
  "wecom": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
  "max_items": 8 }
```

---

## 7. 校验与 Schema

```bash
neurodaily config validate [--profile NAME]
neurodaily config schema --out config.schema.json
neurodaily config describe
```

- 校验失败会给出字段路径，例如 `sources.bad: url is required for type rss/json_api`
- 设置页保存前也会校验（失败返回 400 + 错误列表）

---

## 8. 常见改法（Cheat sheet）

| 想做什么 | 怎么做 |
|---|---|
| 加一个学科 | 在 `disciplines` 追加一项（或 `config apply`） |
| 只看最近 1 天 | 各源 `lookback_days: 1` |
| 加一个 RSS 源 | `sources.<name> = {type:"rss", url, kind}` |
| 加一个 JSON API | `sources.<name> = {type:"json_api", url, items_path, map}` |
| 只保留神经相关融资 | 给该源加 `filter_keywords: ["neuro","brain","bci"]` |
| 换成肿瘤学 | `profile new oncology` + `config apply oncology.patch.json --profile oncology` |
| 关闭 AI 摘要 | `config/ai_summary.json -> enabled: false` |
| 关闭邮件 | `config/email.json -> enabled: false`（或 TUI 按 `t`） |
| 增加收件人 | `neurodaily mail --add a@b.com` 或 `mail --tui` |
| 改定时时间 | 桌面版修改时间并保存。CLI 的 macOS LaunchAgent 使用 `launchd install` 重新安装 |
| 导出 BibTeX | `output.extra_formats: ["bibtex"]` 或 `neurodaily export --format bibtex` |


---

## 9. 时间窗口与多语言（新增）

| 字段 | 默认 | 说明 |
|---|---|---|
| `windows.daily_paper_hours` | `36` | 定时任务只保留最近 36 小时的论文 |
| `windows.manual_paper_hours` | `168` | 手动 `run --mode manual` 的论文窗口 |
| `windows.other_lookback_days` | `7` | 非论文（试验/政策/产业）回看天数 |
| `scheduled.on_this_day.lang` | `zh` | 史论语言：`zh`/`en`/`ru`；CLI 覆盖 `run --lang en` |

论文窗口在抓取后统一过滤；无日期的论文保留（宁可多推，不静默丢）。

## 10. Web 设置页（推送 + 一键检索）

`/settings` 除主配置外新增「推送设置」：

- 邮件：启用开关、收件人（逗号/换行）、SMTP 主机、端口、加密方式、账号、发件人、主题模板、是否附完整 HTML。**测试邮件连通性** 使用当前输入验证 TLS 和 SMTP 登录，结果不代表收件人可以收信。
- 凭据：SMTP 授权码输入框 → `POST /api/push/password` 写入 `~/.neurodaily_smtp`（600）
- AI 摘要：在设置页填写 Chat Completions 兼容的 API 基础地址、模型 ID 和 API 密钥。**测试模型 API** 只发送一条简短探测请求。密钥保存在本机 AI 设置中，输入框留空会保留已有密钥。更换服务地址时，如已有密钥，请填写新服务的密钥。
- Webhook：飞书、企业微信

选择「神经科学」或「肿瘤学」预设会填入检索配置。检查后点击 **Save & continue to search** 保存并进入 `/run`。临时时间范围留空时使用保存的配置。点击 **开始检索** 后，系统在报告生成成功时打开结果页，并按配置投递。

报告页的 **Settings** 打开 `/settings`，**Run now** 打开 `/run`。
macOS 可双击 `scripts/启动 NeuroDaily.command` 启动服务并直接打开设置页，无需命令行。
