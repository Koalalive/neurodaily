# GitHub Actions 部署（Agent 协议）

> **中文** — 不用服务器：用 GitHub Actions 每天定时跑一次，生成报告并以邮件发送到指定邮箱，同时把 HTML 作为 artifact 保留。
> **English** — Serverless daily run on GitHub Actions: generate the digest, email it to a given address, and keep the HTML as an artifact.
> **Русский** — Ежедневный запуск без сервера через GitHub Actions: сформировать сводку, отправить её на указанный адрес и сохранить HTML как artifact.

适用：没有常驻服务器、只想每天收邮件的人；或作为本地部署的备份通道。

---

## 1. 前置

- 仓库已 fork/clone 到你的 GitHub（`Koalalive/neurodaily` 或你自己的 fork）
- 本机安装 `gh` 并登录：`gh auth login`
- 一个可用的 SMTP 账号与授权码（如 SJTU 邮箱 587 STARTTLS）
- 可选：AI 摘要的 API key

## 2. 需要设置的 Secrets

在仓库 **Settings → Secrets and variables → Actions**，或用 `gh secret set`。

| Secret | 必填 | 内容 |
|---|---|---|
| `NEURODAILY_CONFIG_JSON` | 建议 | 完整的 `config.json` 内容（学科、源、期刊、收件人无关） |
| `NEURODAILY_EMAIL_JSON` | 必填 | 完整 `config/email.json`（SMTP 主机/端口/发件人/**收件人**/主题） |
| `NEURODAILY_SMTP_PASSWORD` | 必填 | SMTP 授权码 |
| `NEURODAILY_AI_JSON` | 可选 | `config/ai_summary.json`（base_url/model） |
| `NEURODAILY_LLM_API_KEY` | 可选 | 大模型 key |

> 收件人写在 `NEURODAILY_EMAIL_JSON` 的 `to` 字段里，例如
> `{"to":["you@example.com"], "smtp_host":"smtp.sjtu.edu.cn", "smtp_port":587, ...}`

## 3. 五步部署

```bash
# 1) 设置配置与凭据（本机执行，不会回显密钥）
gh secret set NEURODAILY_CONFIG_JSON < config/config.json
gh secret set NEURODAILY_EMAIL_JSON  < config/email.json
gh secret set NEURODAILY_SMTP_PASSWORD
# 可选
gh secret set NEURODAILY_AI_JSON < config/ai_summary.json
gh secret set NEURODAILY_LLM_API_KEY

# 2) 查看已设置的 secret 名称（不显示值）
gh secret list

# 3) 手动触发一次
gh workflow run daily-digest.yml -f demo=false

# 4) 观察运行
gh run list --workflow daily-digest.yml --limit 3
gh run watch

# 5) 验收
gh run view --log | tail -50          # 应看到 "email sent"
# 或到 Actions → 该次运行 → Artifacts 下载 neurodaily-report
```

## 4. 定时

`daily.yml` 中：

```yaml
on:
  schedule:
    - cron: "0 0 * * *"   # 08:00 北京时间（UTC+8）
```

- GitHub cron 使用 **UTC**；北京时间 08:00 = UTC 00:00
- GitHub 的定时任务可能延迟几分钟到几十分钟（高负载时）
- 默认分支上的 workflow 才会按 schedule 运行

## 5. 限制与注意

| 项 | 说明 |
|---|---|
| 运行时长 | 单 job 最长 6 小时；本任务通常 2–4 分钟 |
| Secrets | Fork 的 PR 默认拿不到 secrets；尽量在自有仓库运行 |
| 公开仓库 | **不要把 config/email.json、key 提交进仓库**；只用 secrets |
| Artifact | 默认保留 14 天（`retention-days`） |
| 无持久化 | 每次 runner 是全新的；深读池随仓库代码提供，AI 缓存不会跨运行复用 |
| 网络 | GitHub runner 可访问 PubMed/arXiv/RSS；SMTP 建议 587 STARTTLS |

## 6. 排障

| 现象 | 原因 | 处理 |
|---|---|---|
| workflow 没触发 | 不在默认分支 / cron 延迟 | 用 `gh workflow run` 手动触发 |
| `email not sent: 缺少 SMTP 密码` | secret 未设置或名字写错 | `gh secret list` 核对；重新 set |
| `Authentication failed` | 用了登录密码而非授权码；或 465 被拦 | 用授权码；改 587 + STARTTLS |
| `config not found` | `NEURODAILY_CONFIG_JSON` 为空 | 本地 `config init` 后上传；或让工作流自动 init |
| 收件人没收到 | 进了垃圾箱 / `to` 为空 | 检查 `NEURODAILY_EMAIL_JSON` 的 `to`；加白名单 |
| AI 摘要缺失 | 没设 `NEURODAILY_LLM_API_KEY` | 设置后重跑；或忽略（报告仍生成） |

## 7. 验收清单

- [ ] `gh secret list` 含 3 个必填 secret
- [ ] `gh workflow run` 成功排队
- [ ] `gh run view` 状态 `success`
- [ ] 日志出现 `✅ wrote ... items` 与 `📧 email sent`
- [ ] Artifacts 里有 HTML 报告
- [ ] 目标邮箱收到主题 `神经病专家的厕所读物-日期 星期`

## 8. 与本地部署的关系

| 方式 | 优点 | 缺点 |
|---|---|---|
| 本地/小主机 | 数据不出机、可离线、单机多收件人、AI 缓存复用 | 需要机器常开 |
| GitHub Actions | 零服务器、免费额度、自动 artifact | Secrets 托管在 GitHub、无持久缓存、cron 有延迟 |

两者共用同一套配置格式，可互为备份。
