# NeuroDaily Profile 生态落地计划与竞品分析

> 状态：审阅稿 v0.1  
> 日期：2026-11-20  
> 范围：检索 Profile 的文档层、组合/校验、人类与 Agent 双接口、迁移、注册生态  
> 不包含：1.0.0 桌面安装包 CI 修复（独立工作流）

## 实现进度（2026-11-22）

- 已完成：单 JSON `profile export/import/validate/doctor` CLI；复用设置页同一套 `profile_exchange`（URL 去敏、私密字段隔离）；设置页保存保留未知 source 字段；`search` 已接入检索。
- 已补回归：profile 导出/导入/校验/doctor、URL 密钥去除、doctor 发现缺失 `type` 的自定义源。
- 仍待：`plan/apply`、`extends/overrides`、`.ndprofile` bundle 迁移、registry/lock、feedback/change-only、MCP。
- 发布前门禁：`bash scripts/test_all.sh` 全绿；release 分支 CI 通过后再打 `v1.0.8` tag。

---

## 0. 审阅摘要

### 要解决的核心问题

当前 NeuroDaily 的“profile”还是分散配置：

- `config.json` 里混有 `disciplines / sources / journals / windows / search / policy_feeds`
- 设置页保存会重建对象，曾把 `sources.type/url/kind` 覆盖掉，导致创投源静默失效、industry=0
- 导出的 `neurodaily-neuro-2.json` 有 `format/version/config/search`，但加载器没有真正消费 `search`
- 没有 schema 校验、没有 plan/diff、没有迁移链、没有 profile registry、没有 Agent 专用接口

### 目标结果

1. **人可读**：YAML/JSON 可手改，有 schema、注释、示例、doctor
2. **Agent 可改**：MCP/CLI 提供 `resolve / validate / plan / apply / export / import`
3. **可组合**：`extends` + `overrides`，preset/theme 可叠加
4. **可迁移**：`.ndprofile` bundle + schema migration + 备份/回滚
5. **有生态**：内置 preset、版本化 registry、lockfile、可分享
6. **可审计**：revision、diff、变更日志、反馈层

### 建议节奏

| 阶段 | 周期（1 人） | 目标 |
|---|---|---|
| P0 | 2 周 | Profile v1 schema + validate/resolve/export/import + doctor |
| P1 | 3 周 | extends/overrides + preset/theme + 表单/YAML 双编辑 + plan/apply |
| P2 | 3 周 | bundle/migration + registry/lock + feedback/change-only |
| P3 | 3 周 | MCP/Agent 工具 + 团队作用域 + 审计 |
| 合计 | 约 11 周 | 2 人并行约 6–7 周 |

### 需要你拍板的 7 件事

1. Profile 主格式：**YAML + JSON Schema（推荐）**，还是 CUE/Pkl？
2. 第一版是否只做 **personal scope**，团队/共享延后？
3. registry 先做 **内置 preset**，还是一开始就做远程安装？
4. 旧 `version: 1` 是 **双读兼容 + 保存时迁移（推荐）**，还是强制迁移？
5. feedback 先 **建议式**（用户确认），还是自动写回？
6. UI 是扩展现有 `/settings`，还是新增 `/profiles` Studio？
7. 是否坚持“profile 不含密钥，只放 credential_ref”？

---

## 1. 现状与差距

### 1.1 已有能力

- Profile 隔离：`neurodaily profile new/list/path/show`
- JSON patch：`config apply`（对象合并、数组替换、null 删除）
- schema 基础：Pydantic `ConfigModel`
- 数据源：内置 + 配置化 RSS/JSON
- 设置页、Run now、Tauri 桌面壳
- 75 项单元测试

### 1.2 关键缺口

| 缺口 | 影响 |
|---|---|
| Profile 不是一等对象 | 无法整体导出/导入/版本化 |
| 无 `resolve`/effective profile | 用户不知道最终生效值 |
| 无 `plan/diff` | 保存即生效，改坏难发现 |
| 无 migration | 版本升级会破坏旧 profile |
| 无 registry/lock | preset 无法版本化分发 |
| 无 Agent 接口 | Agent 只能改文件，容易误伤 |
| 无 feedback 层 | 收藏/忽略不回流 |
| 无 change-only | 每天重复推相同内容 |
| 设置页保存丢未知字段 | 已导致 industry=0 真实事故 |
| `search` 块未执行 | 导出的 query/sets/journal_mode 形同虚设 |

---

## 2. 竞品与参考项目

### 2.1 研究/情报类商业产品

| 产品 | 关键机制 | 可借鉴 | 不照搬 |
|---|---|---|---|
| **Feedly** | AI Feed、Team/Personal Folders、Boards、OPML | profile 即订阅流；个人/团队作用域；AI Feed 条件化 | OPML 不含 AI Feed/Boards → 迁移必须包含规则本身 |
| **Inoreader** | Filter（看不看）与 Rule（做什么）分离；Active Search；重复过滤；整账号归档 | 检索策略与动作分层；规则日志/命中数；完整归档 | 规则数量/套餐限制不适合本地优先 |
| **Elicit** | Setup 页：问题/PICO/检索策略/筛选标准/提取列；项目关联 collection；双人筛选与审计 | profile = 问题 + 标准 + 检索 + 提取 schema；preset columns | 它是系统综述工作流，不是每日多源简报 |
| **Rayyan** | 纳入/排除标准、Include/Exclude/Maybe、盲审、冲突解决、导出含 `customizations_log` | 标准/决策/审计是一等对象；导出带历史 | 不含日常 RSS/创投/政策聚合 |
| **Zotero** | Saved Searches、Collections、Group Libraries、标准导入导出 | 保存搜索 + 集合层级 + 可迁移 | 不是自动日报/推送系统 |
| **ResearchRabbit / Litmaps** | 种子论文 → 推荐/图谱 | profile 支持 seed papers，比纯关键词更贴近研究者 | 推荐黑盒，难审计 |
| **Dimensions / Scopus / WoS** | 保存检索式 + alert + 字段语法 | 显式 query、saved search、定时订阅 | 商业闭源、不可自托管 |
| **Covidence / DistillerSR** | 系统综述流程、双人筛选、PRISMA、审计 | 研究型 profile 需要流程状态 | 重流程，不适合轻量日报 |

### 2.2 开源产品

| 项目 | 关键机制 | 可借鉴 |
|---|---|---|
| **OpenBioNews** | `setup` 向导、watchlist、主题预设、`doctor`、每源 `recent_days`、可选 RSS、change-only | 入门向导、preset/theme、配置体检、按源窗口、变化追踪 |
| **OpenRaiser/PaperFlow** | 每 user 一个 profile；自然语言/PDF/Scholar/主页冷启动；merge/reset；feedback loop | profile 生命周期、冷启动、增量合并、反馈回写 |
| **Horizon** | profile 是编辑规则（评分/筛选/输出）；source 可分配；profile_settings 管偏好 | profile 不止关键词，而是“筛选 + 评分 + 呈现” |
| **MaybeBio/pyPaperFlow** | 无持久 profile；显式每平台 query；output/storage 分离 | query 是一等公民；高级检索能力 |

### 2.3 配置/自动化基础设施

| 项目 | 机制 | 借鉴 |
|---|---|---|
| **Home Assistant** | UI + YAML 双编辑、config entries、迁移、备份、secrets | 双轨编辑、升级迁移、密钥分离 |
| **Terraform** | plan/apply、state、provider、version constraints | 改 profile 必须 plan → diff → apply；revision/lock |
| **Kubernetes CRD/Operator** | schema、版本化 CRD、conversion webhook | Profile schema 版本转换 |
| **Helm / Kustomize** | base + overlays / patch | preset base + theme + user override |
| **Hydra** | defaults list、层级组合、CLI override | 组合优先级、环境覆盖 |
| **dbt** | `profiles.yml` + `packages.yml` + target | 环境/凭据外置；依赖锁定 |
| **ESLint** | shareable config、`extends`、plugin、registry | profile 生态：preset/扩展/分发 |
| **VS Code Profiles** | 导出/导入、设置同步、扩展集合 | 一键迁移整个工作环境 |
| **JSON Schema / CUE / Pkl** | schema 校验、约束、默认值 | 人写 YAML，机器校验 |
| **n8n / Zapier** | 模板库、credentials 分离 | profile 模板市场；密钥不进模板 |
| **Argilla / Label Studio** | 标注指南 + schema + 模板 | 筛选/提取标准做成可复用 rubric |
| **Great Expectations** | 数据契约、可执行校验 | doctor + golden fixtures |

### 2.4 能力矩阵（定性，1–5）

> 基于公开文档的定性评估，不代表精确测评。

| 项目 | 人可读 | Agent 可改 | Schema/校验 | 组合/继承 | 迁移/导出 | 生态/分享 | 反馈闭环 | 变化追踪 | 团队/审计 | 本地/隐私 | 研究语义 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Feedly | 4 | 3 | 2 | 2 | 3 | 4 | 2 | 3 | 4 | 1 | 2 |
| Inoreader | 4 | 3 | 3 | 2 | 4 | 3 | 2 | 3 | 4 | 1 | 2 |
| Elicit | 4 | 3 | 3 | 2 | 3 | 2 | 3 | 2 | 5 | 1 | 5 |
| Rayyan | 4 | 3 | 3 | 1 | 4 | 2 | 3 | 2 | 5 | 1 | 5 |
| Zotero | 4 | 2 | 3 | 2 | 4 | 4 | 2 | 2 | 3 | 5 | 3 |
| ResearchRabbit | 4 | 2 | 2 | 1 | 2 | 2 | 3 | 2 | 2 | 2 | 4 |
| OpenBioNews | 5 | 3 | 4 | 1 | 3 | 2 | 2 | 5 | 2 | 5 | 3 |
| PaperFlow | 3 | 4 | 3 | 2 | 3 | 2 | 5 | 3 | 2 | 5 | 4 |
| Horizon | 4 | 3 | 3 | 3 | 2 | 2 | 3 | 3 | 2 | 4 | 4 |
| **NeuroDaily 目标** | **5** | **5** | **5** | **5** | **5** | **5** | **4** | **4** | **4** | **5** | **4** |

### 2.5 NeuroDaily 的差异化

- **本地优先 + 引用可追溯**：Feedly/Inoreader 强在云端聚合，Elicit/Rayyan 强在综述流程，但都不是“本地每日多源 + 可审计引用”。
- **Agent-native**：多数产品的配置不是给 Agent 设计的；NeuroDaily 可以把 profile 做成 Agent 可计划/可应用的一等对象。
- **多源覆盖**：论文 + 试验 + FDA + 政策 + 创投；Elicit/Rayyan 不做日常产业情报。
- **可迁移**：Feedly 的 AI Feed 不随 OPML 导出；NeuroDaily 要从第一天支持 profile bundle。

---

## 3. 目标架构

### 3.1 分层

```text
┌────────────────────────────────────────────┐
│ 人类 UI（表单 / YAML 编辑器 / diff / doctor） │
├────────────────────────────────────────────┤
│ Agent 接口（MCP / CLI / REST）               │
├────────────────────────────────────────────┤
│ Profile Engine                               │
│  resolve → validate → plan → apply           │
│  revision / backup / audit / migration       │
├────────────────────────────────────────────┤
│ Profile 文档层                               │
│  .ndprofile bundle                           │
│  profile.yaml + manifest + migrations        │
├────────────────────────────────────────────┤
│ Source Adapters                              │
│  PubMed / arXiv / RSS / trials / FDA / policy│
└────────────────────────────────────────────┘
```

### 3.2 Profile bundle

```text
neuro-2.ndprofile/
  manifest.json      # format/schema_version/id/revision/checksum/min_app_version
  profile.yaml       # 人类可读，可带注释
  README.md          # 说明/来源/变更
  migrations/        # 可选：该 profile 自带迁移
  fixtures/          # 可选：示例/测试数据
```

### 3.3 组合与优先级

推荐优先级（从低到高）：

```text
系统默认
  < base preset
  < theme preset
  < 用户 profile
  < 环境覆盖（profile.<env>.yaml）
  < 本次运行参数（Run now hours 等）
```

- `extends` 按顺序合并；后面的覆盖前面的
- `overrides` 是用户层，优先级最高（运行参数除外）
- 禁止数组深合并：数组默认**整体替换**，需要合并时显式 `merge: append|prepend|replace`
- 解析结果写入 `effective_profile.json` + `effective_hash`，供审计/缓存

### 3.4 Schema v1 示例

```yaml
format: neurodaily.profile
schema_version: 2
id: neuro-2
name: Neuroscience
description: 神经科学 + 精神科 + 神经外科
revision: 7
extends:
  - base/neuroscience@1.0.0
  - themes/bci@1.0.0

scope: personal          # personal | team

retrieval:
  watchlist:
    terms: [brain, neuro, EEG]
    mesh: [Neurosciences, Epilepsy]
    arxiv_cats: [q-bio.NC, cs.NE]
    bio_cats: [neuroscience]
  search:
    sets:
      epilepsy: 'Epilepsy[MeSH] AND (seizure[tiab] OR EEG[tiab])'
    journal_mode: any
    journals: [Nature Neuroscience, Neuron, Epilepsia]
    sort: relevance
  sources:
    pubmed: {enabled: true, recent_days: 2, search_set: epilepsy}
    arxiv: {enabled: true, recent_days: 2}
    neuro_vc_bci: {enabled: true, recent_days: 7}
  windows:
    papers: 36h
    trials: 36h
    funding: 36h
    news: 36h
  journals:
    - name: Nature Medicine
      impact_factor: 58.7
      jcr: Q1
      cas: 1区

review:                   # 可选：研究型筛选/提取
  question: ...
  include: [...]
  exclude: [...]
  labels: [...]
  decisions: [include, exclude, maybe]

presentation:
  language: zh
  citations: {style: parenthetical, one_per_sentence: true}
  sections: [papers, industry, trials, policy]

delivery:
  email_ref: default
  webhook_refs: [lab-feishu]

feedback:
  enabled: true
  mode: suggest           # suggest | auto

secrets_refs:
  deepseek: env:DEEPSEEK_API_KEY
  smtp: file:~/.neurodaily_smtp
```

### 3.5 Agent / CLI 契约

| 操作 | CLI | MCP tool | 返回 |
|---|---|---|---|
| 读取 | `profile show <id> [--raw|--resolved]` | `profile.get` | profile + revision |
| 校验 | `profile validate <file>` | `profile.validate` | errors: `{pointer, message, hint}` |
| 解析 | `profile resolve <id>` | `profile.resolve` | effective profile + hash |
| 计划 | `profile plan <id> --patch p.json` | `profile.plan` | diff + impact（预计条数/源/期刊） |
| 应用 | `profile apply <id> --patch p.json --revision N` | `profile.apply` | 新 revision + backup |
| 体检 | `profile doctor <id>` | `profile.doctor` | 源可达性/ISSN/RSS/LLM/邮件 |
| 导出 | `profile export <id> --bundle` | `profile.export` | `.ndprofile` |
| 导入 | `profile import <bundle> --mode merge|replace` | `profile.import` | plan → apply |
| 迁移 | `profile migrate <file>` | `profile.migrate` | 新文件 + 变更摘要 |

要求：

- JSON Patch（RFC 6902）或 Merge Patch（RFC 7386）
- `apply` 必须带 `base_revision`，冲突拒绝
- 错误定位 JSON Pointer
- 每次 apply 先备份，原子写
- 审计日志：who / when / patch / before_hash / after_hash
- Agent 只能改 allowlist 字段；不得执行 profile 内代码

### 3.6 人类 UI

- `/profiles` 页面（或扩展 `/settings`）
  - Preset 卡片：神经科学 / 肿瘤学 / 精神病学 / BCI
  - 表单：watchlist、sources、windows、journals、delivery
  - 高级 YAML tab：schema 校验、实时错误
  - 解析预览：effective values
  - 保存前：预计命中数、源可达性、diff
  - 导入：merge/replace/另存为
  - 一键备份/回滚
- `doctor` 页面：源/期刊/LLM/邮件检查

### 3.7 迁移

```text
v1 JSON → read → migrate v1_to_v2 → validate → resolve → write bundle
```

- 旧格式**双读兼容**；保存时迁移
- migration 链可测试：`migrations/v1_to_v2.py`
- bundle 导入先 `plan`，冲突需确认
- 备份保留最近 N 份
- `min_app_version` 不满足时拒绝并提示升级

### 3.8 Registry / 生态

```text
profiles/
  base/neuroscience@1.0.0/
  base/oncology@0.9.0/
  themes/bci@1.0.0/
  registry.json
```

- `registry.json`：名称、版本、checksum、schema、作者、`min_app_version`
- `profile.lock`：固定 extends 版本与 checksum
- `profile install neuro/bci@1.0.0`
- 先做内置/Git 仓库 registry；远程市场后置
- 分享只带 profile，不带 secrets

---

## 4. 分阶段落地计划

### P0（第 1–2 周）：Profile 核心

**交付物**

- `Profile` dataclass/Pydantic model + JSON Schema v2
- `profile validate/resolve/export/import/doctor` 基础版
- 旧 `version: 1` 读取 + `migrate v1→v2`
- 设置页保存**保留未知字段**（防再次 industry=0）
- 单元测试：schema、round-trip、旧格式、source 字段保留

**验收**

```bash
profile validate fixtures/neuro-v1.json        # 0 error
profile resolve neuro-2 --raw > /tmp/x.json    # 确定性
profile export neuro-2 --bundle /tmp/neuro.ndprofile
profile import /tmp/neuro.ndprofile --dry-run  # plan 输出
profile doctor neuro-2                         # 源/期刊/LLM/邮件检查
```

- 旧 profile 导入后 0 字段丢失
- 设置页保存后 `sources.type/url/kind` 仍在

### P1（第 3–5 周）：组合与双编辑

**交付物**

- `extends`、`overrides`、resolved profile、effective hash
- presets：`neuroscience` / `oncology`（+ 可选 psychiatry）
- theme：`bci` / `epilepsy`
- `profile plan/apply`（JSON Patch、revision、备份）
- `/profiles` UI：表单 + YAML + diff + 预览
- 每源 `recent_days`
- `search.sets` / `journal_mode` 真正接入检索

**验收**

- 改 theme 不影响用户 override
- plan 显示 diff 与预计条数
- apply 冲突时拒绝，备份可回滚
- YAML 注释可保留（ruamel）
- 搜索 set 能在 PubMed 查询中生效

### P2（第 6–8 周）：迁移与生态

**交付物**

- `.ndprofile` bundle v2 + manifest/checksum
- migration 链 + golden fixtures
- registry + lock + `profile install`
- feedback 层（收藏/忽略/已读，suggest 模式）
- change-only 模式（trial/paper/filing diff）
- 审计日志

**验收**

- v1 → v2 → bundle → import 全链路
- 导入校验 checksum/依赖版本
- 反馈不污染 raw profile（写到 feedback 层）
- 第二次运行只显示变化项

### P3（第 9–11 周）：Agent 与团队

**交付物**

- MCP server：profile tools + resources
- Agent plan/apply 审批流（人确认）
- team scope：共享 profile、成员/权限、审计
- registry 远程安装（可选）
- 文档/样例 profile/作者指南

**验收**

- Agent 可通过 MCP 读取/校验/计划/应用
- 人类能看到 diff 并批准
- 团队成员共享同一 profile，变更可审计
- 外部 profile 导入有 checksum/来源提示

### 并行建议

- 2 人：A 负责 Profile engine + CLI/MCP；B 负责 UI + presets + migration fixtures
- 每周一次 golden profile 回归；每阶段结束做一次真实用户试用

---

## 5. 测试与质量门

| 类型 | 内容 |
|---|---|
| Schema 测试 | 合法/非法字段、默认值、JSON Pointer 错误 |
| Round-trip | YAML/JSON/export/import 不丢字段 |
| 迁移测试 | v1 fixtures → v2 快照；失败回滚 |
| 组合测试 | extends/overrides 优先级、数组替换语义 |
| 安全测试 | YAML safe_load、zip 路径穿越、大小限制、checksum |
| Doctor 测试 | 源可达、RSS/ISSN、LLM/邮件 mock |
| Golden profiles | 神经科学/肿瘤学/BCI 三套固定 fixture |
| 端到端 | 创建 → doctor → run → 报告 → 反馈 → 再 plan |

强制门禁：

- `profile validate` 0 error
- 迁移 round-trip hash 一致（除预期变更）
- apply 必须生成 backup + audit
- 设置页保存后自定义 source 字段不丢

---

## 6. 安全与隐私

- Profile 不含密钥，只放 `credential_ref`
- YAML 使用 safe_load；禁止任意代码/模板执行
- bundle 导入限制大小、校验 checksum、拒绝路径穿越
- Agent 修改需 allowlist + revision + 人工确认（高风险变更）
- 审计日志不记录密钥
- 团队共享默认脱敏；导出前提示
- registry 安装显示来源/作者/checksum

---

## 7. 指标（上线后 4–8 周）

- 新建 profile 到首次成功报告的时间
- 首次 doctor 通过率
- 导入/迁移成功率
- Agent plan 被批准比例
- profile 修改后 7 天留存/使用率
- 因配置错误导致的 0 条运行比例（目标 <1%）
- 反馈采纳率（收藏/忽略）
- 分享 profile 的导入成功率

---

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| Schema 频繁变更 | `schema_version` + migration + 兼容窗口 |
| 迁移丢字段 | golden fixtures + round-trip + 备份 |
| Agent 改坏 | plan/apply + revision + 人工确认 + 回滚 |
| Preset 质量差 | doctor + 真实用户试用 + CI 校验 |
| Registry 供应链 | checksum + 来源提示 + 只读安装 |
| UI 过复杂 | 表单优先，YAML 高级；preset 降低门槛 |
| 与 1.0.0 发布冲突 | Profile 工作流独立；不阻塞桌面安装包 |
| 反馈污染 | feedback 独立层，可撤销 |

---

## 9. 需要审阅的决策

| # | 决策 | 推荐 |
|---|---|---|
| 1 | 主格式 | YAML + JSON Schema；JSON canonical |
| 2 | 第一版 scope | personal；team 放 P3 |
| 3 | registry | 先内置/Git；远程市场 P3 |
| 4 | 旧格式 | 双读兼容，保存时迁移 |
| 5 | feedback | 先 suggest，用户确认后写 |
| 6 | UI | 扩展 `/settings` + 新增 `/profiles` |
| 7 | 密钥 | credential_ref / env / keychain，不进 profile |
| 8 | 是否做研究型 review 块 | P1 只留 schema 占位，P2 再实现 |

---

## 10. 附录：竞品借鉴清单（按优先级）

### 必抄

- Feedly：profile 即订阅流；个人/团队作用域
- Inoreader：Filter/Rule 分离；完整归档
- Elicit：问题 + 标准 + 提取 schema；双人审计
- Rayyan：标准/决策/审计导出
- Home Assistant：UI/YAML 双轨 + 迁移/备份
- Terraform：plan/apply/revision
- Helm/Kustomize：base + overlay
- ESLint：extends/registry
- JSON Schema：校验

### 选抄

- Hydra：组合优先级/环境覆盖
- dbt：profiles/packages/target
- VS Code Profiles：一键迁移
- OpenBioNews：setup/doctor/change-only
- PaperFlow：冷启动/feedback/merge-reset
- Horizon：profile 作为评分/呈现规则
- Zotero：saved searches/collections
- ResearchRabbit：seed papers

### 不抄

- 可执行 Python/JS 配置（Agent 安全/迁移困难）
- 只做关键词列表（没有标准/反馈/审计）
- 只做 OPML 导出（AI Feed/规则会丢）
- 单一巨大表单（preset + override 更可持续）
- 保存即生效、无备份（这次 industry=0 的教训）

---

## 11. 附录：建议文件树

```text
neurodaily/
  profiles/
    base/neuroscience@1.0.0/profile.yaml
    base/oncology@0.9.0/profile.yaml
    themes/bci@1.0.0/profile.yaml
    registry.json
  neurodaily/
    profile/
      __init__.py
      model.py          # Pydantic schema
      compose.py        # extends/overrides/resolve
      validate.py
      plan.py           # diff/impact
      apply.py          # backup/revision/audit
      migrate.py        # v1->v2...
      bundle.py         # export/import
      doctor.py
      registry.py
  cli_profile.py
  mcp_profile_server.py
  tests/
    fixtures/profiles/
    test_profile_schema.py
    test_profile_migrate.py
    test_profile_roundtrip.py
```

---

*本文为审阅稿，确认决策后再进入实现。*
