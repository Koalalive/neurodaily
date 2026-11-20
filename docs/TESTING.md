# 测试说明

## 1. 一键运行

```bash
bash scripts/test_all.sh     # 推荐
make test                    # 等价
```

`test_all.sh` 顺序执行：

1. `compileall`（`neurodaily/`、`scripts/`）
2. **32 项 unittest**（`tests/`）
3. `config validate`
4. 离线 `demo` 生成报告
5. `export --demo --format both`（JSON + BibTeX）
6. `profile new` + `config apply --dry-run`

全部离线，不联网、不发邮件、不调用 AI（AI 相关用 mock）。

单独跑：

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## 2. 测试矩阵

| 测试类 | 覆盖点 |
|---|---|
| `ConfigTests` | 配置往返无损；空 disciplines 拒绝 |
| `SchemaTests` | 默认配置合法；通用源缺 url 报错；未知 kind 报错 |
| `ConfigOpsTests` | 合并语义（递归/数组替换/null 删除）；dry-run 不写；非法补丁拒绝 |
| `ProfileTests` | 新建 profile、列表、路径 |
| `OnThisDayTests` | 366 天全覆盖且每天有 ≥500 字长文；无「出生/逝世」条目 |
| `RenderTests` | 「历史上的今天」置顶；图谱 JS 只注入一次 |
| `MailerTests` | 主题格式；空收件人报错；附件超限跳过；缺失附件容错 |
| `MailTuiTests` | 增/删/去重；保留 SMTP 配置 |
| `PruneTests` | 保留最新 N 份 + 历史引用不删 |
| `ExportTests` | JSON 计数正确；BibTeX 含 `@article` 与标题 |
| `DemoTests` | 10 条演示数据；板块合计一致；渲染置顶 |
| `WebhookTests` | 文本包含标题；无配置时 no-op |
| `GenericSourceTests` | 通用 RSS 解析；JSON API 映射与日期过滤 |
| `AISummaryTests` | 输入含四大板块；缺 key 报错；缓存只调用一次；渲染置顶 |
| `RouteTests` | 6 个路由 200；非法 POST 400；路径穿越 404 |

## 3. CLI 黑盒检查

`/tmp/cli_test.sh` 风格（14 项）：

| 检查 | 期望 |
|---|---|
| `config describe` / `schema` / `validate` | 退出 0 |
| `profile new` / `list` | 退出 0，列表含新 profile |
| `config apply --dry-run` | 退出 0，输出 `dry-run OK` |
| `config apply` | 退出 0，写入 |
| `config validate --profile` | 退出 0 |
| `demo --profile` | 退出 0，10 条 |
| `export --demo` | 退出 0，写出文件 |
| `webhook --test`（无配置） | 退出 0，`{}` |
| 非法补丁 / 缺 profile / 缺补丁文件 | 退出 1 |

## 4. 真实端到端（已执行）

| 项 | 结果 |
|---|---|
| 真实检索 | ✅ 单日 **867 条**（含 4 个创投源共 24 条） |
| AI 摘要 | ✅ 约 1200 字，置顶于「历史上的今天」之上 |
| 邮件 | ✅ 测试邮件 + 完整日报（附件 1.64 MB）发送成功 |
| 缓存 | ✅ 同内容二次生成 0.5s（无 API 调用） |
| 定时任务 | ✅ 历史记录显示每日 08:05 左右自动运行 |
| Web | ✅ 6 个路由 200；非法配置 400；路径穿越 404 |
| Docker | ✅ 镜像 199 MB；容器 4 个端点 200；compose 校验通过 |

## 5. CI

`.github/workflows/ci.yml`：

- 触发：push / PR
- 矩阵：Python **3.12 / 3.13**
- 步骤：`pip install -e .` → `bash scripts/test_all.sh`

## 6. 已知未覆盖 / 未验证

| 项 | 说明 |
|---|---|
| Windows 原生 | 只在 macOS 测过；Windows 建议 WSL |
| 真实飞书/企微推送 | 没有可用 webhook URL，只测了失败降级路径 |
| 直连 DeepSeek | 使用 SJTU 网关的 `deepseek-chat` 测试；协议同为 OpenAI 兼容 |
| 936 篇 LLM 长文事实核查 | 抽样人工看过；提示词禁止编造，但未逐条核对 |
| 高并发/多实例 | 面向单机，未做大并发压测 |
| 浏览器兼容 | 报告为原生 HTML/JS，未做跨浏览器矩阵测试 |

## 7. 测试中发现并修复的问题

1. 深读编排器**缓存陈旧**（长驻进程反复重生成同一批）
2. 通用 RSS **回溯过滤失效**（RFC822 日期未解析）
3. `serve --profile` **不生效**（`/api/config` 固定读默认配置）
4. 空收件人**静默成功**（`sendmail([])` 无操作）
5. TUI **未合并默认配置**
6. 报告**无限增长**（已加 `keep_reports`）
7. 设置接口**错误结构不一致**
8. 通用源过滤里 `raw` 未定义

## 8. 新增测试

在 `tests/test_smoke.py` 追加 `unittest.TestCase` 子类即可；CI 会自动发现。
建议覆盖「输入 → 期望输出」与「失败路径」两类，避免只测 happy path。
