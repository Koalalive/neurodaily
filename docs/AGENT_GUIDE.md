# Agent 配置手册（让小白也能「换学科」）

> **中文** — 让 Agent 零代码完成换学科的协议。
> **English** — Protocol for an agent to switch disciplines without code.
> **Русский** — Протокол смены дисциплины агентом без кода.

> 目标：用户只说「我想每天看肿瘤学」，Agent 就能**不改代码**、按固定协议把配置改好并验证。
> 所有命令都是**非交互**的，返回明文 + 退出码，Agent 可以循环到通过为止。

---

## 0. 给 Agent 的一段话（可直接复制）

```
你在 NeuroDaily 仓库里。用户想换一个学科（例如肿瘤学）。
按以下协议操作，不要改 Python 代码：
1) 运行 `neurodaily config describe` 了解可配置项与补丁语义。
2) 运行 `neurodaily profile new <name>` 创建独立配置（不要动默认 profile）。
3) 参考 config/examples/oncology.patch.json 写一个 patch.json。
4) 先 `neurodaily config apply patch.json --profile <name> --dry-run`，
   看 diff 与校验错误；有错就修 patch，直到通过。
5) 去掉 --dry-run 写入；再 `neurodaily config validate --profile <name>`。
6) 用 `neurodaily --profile <name> demo --no-open` 做离线冒烟测试。
7) 报告：学科数、期刊数、冒烟测试条数、报告路径。
```

---

## 1. 补丁语义（非常重要）

`config apply` 使用 **JSON 合并补丁**：

| 类型 | 行为 |
|---|---|
| 对象 `{}` | 递归合并 |
| 数组 `[]` | **整体替换**（不是追加） |
| 标量 | 覆盖 |
| `null` | 删除该键 |

> 所以「换学科」时，`disciplines`、`journals`、`global_keywords`、`policy_feeds` 都要给**完整的新数组**。

---

## 2. 五步换学科（以肿瘤学为例）

### 第 1 步：看能力清单
```bash
neurodaily config describe
neurodaily config schema --out /tmp/config.schema.json   # 可选：给 Agent 做严格校验
```

### 第 2 步：建独立 profile（不动默认配置）
```bash
neurodaily profile new oncology
# → config/profiles/oncology.json（已被 gitignore）
```

### 第 3 步：写补丁（照抄模板改）
模板：`config/examples/oncology.patch.json`

最小改动版（只换学科与关键词）：
```json
{
  "profile": "oncology",
  "disciplines": [
    {
      "name": "Medical Oncology",
      "mesh_terms": ["Neoplasms"],
      "arxiv_cats": ["q-bio.QM"],
      "bio_cats": ["cancer biology"],
      "keywords": ["oncology", "cancer", "tumor", "chemotherapy"],
      "enabled": true
    }
  ],
  "global_keywords": ["cancer", "tumor", "metastasis", "immunotherapy"]
}
```
> 只写 `disciplines` 也可以：其余字段会保留（数组替换只影响你给的键）。

### 第 4 步：先试运行（看 diff + 校验）
```bash
neurodaily config apply my_oncology.patch.json --profile oncology --dry-run
```
- 通过 → 打印 `✔ dry-run OK (nothing written)`
- 失败 → 打印具体字段，例如 `sources.bad: url is required for type rss/json_api`

### 第 5 步：写入并验证
```bash
neurodaily config apply my_oncology.patch.json --profile oncology
neurodaily config validate --profile oncology
```

### 冒烟测试（离线，不耗网络）
```bash
neurodaily --profile oncology demo --no-open
# → output/neurodaily_<时间>.html，用演示数据验证渲染与板块
```

### 真正跑一次（耗时约 2–3 分钟）
```bash
neurodaily --profile oncology run --no-open
```

---

## 3. 加一个「配置化数据源」（不写代码）

`config apply` 同样可以加源：

```json
{
  "sources": {
    "nci_news": {
      "type": "rss",
      "url": "https://www.cancer.gov/news-events/cancer-currents-blog/rss",
      "kind": "news",
      "max_results": 30,
      "lookback_days": 7,
      "enabled": true
    },
    "my_api": {
      "type": "json_api",
      "url": "https://api.example.org/items",
      "items_path": "data.items",
      "map": {"title": "title", "url": "link", "summary": "abstract", "date": "published"},
      "kind": "paper",
      "max_results": 50,
      "enabled": true
    }
  }
}
```

- `kind` 决定它进哪个板块：`paper / drug / device / trial / news / policy / conference`
- 失败只降级，不会拖垮整份报告

---

## 4. Guardrails（Agent 必须遵守）

1. **先 dry-run，再写入**；校验不过绝不写。
2. **不要编造期刊 RSS 地址**：不确定就把 `rss` 留空（只作为站点链接）。
3. **不要动默认 profile**：一律 `profile new` + `--profile`。
4. **不要改 `scheduled` / 邮件 / SMTP**，除非用户明确要求。
5. **数组是替换**：想「追加一个学科」时，要把原有学科一起写进数组。
6. **enabled 的学科必须至少有一个** `keywords/mesh_terms/arxiv_cats/bio_cats`。
7. 生成的 profile 在 `config/profiles/`（gitignore），**不要提交**。

---

## 5. 验收清单（Agent 自检）

- [ ] `neurodaily config validate --profile <name>` 退出码 0
- [ ] `neurodaily --profile <name> demo --no-open` 成功生成 HTML
- [ ] 报告里出现新学科的期刊/关键词标签
- [ ] 没有修改 `neurodaily/` 下的任何代码
- [ ] 没有把 `config/profiles/*.json` 加入 git

---

## 6. 常见错误与修法

| 报错 | 原因 | 修法 |
|---|---|---|
| `disciplines: List should have at least 1 item` | 补丁把学科清空了 | 给完整 disciplines 数组 |
| `sources.x: url is required for type rss/json_api` | 通用源缺 url | 补 `url` 或删掉该源 |
| `sources.x: unknown kind 'xxx'` | kind 不在枚举 | 用 paper/drug/device/trial/news/policy/conference |
| `an enabled discipline needs at least one of ...` | 学科无任何检索条件 | 补 keywords 或 mesh_terms |
| `patch must be a JSON object` | 补丁不是对象 | 用 `{...}` 包起来 |
