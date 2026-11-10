# NeuroDaily 运维手册（启动 / 停止 / 配置 / 调度 / GUI）

> 面向本机 macOS。项目根目录：`~/neurodaily`。以下所有命令都在项目根目录执行。
> Python 虚拟环境：`.venv/`（已 `pip install -e .`）。

---

## 0. 当前运行状况（快照）

| 项目 | 状态 | 说明 |
|---|---|---|
| 每日定时任务 `com.neurodaily.daily` | ✅ 已装载 | `launchctl list` 可见；每天 **08:00** 自动运行 |
| 最近一次运行 | ✅ 成功 | 记录在 `output/search_history.db` |
| 常驻 Web 服务 (端口 8031) | ⏹ 未运行 | 需要时手动 `serve` 启动 |
| 最近报告 | `output/neurodaily_<日期>_<时间>.html` | 每次运行生成新文件 |

**历史运行规模（来自 `output/search_history.db`）**：多数日期抓取 600–840 条，报告 1.4–2.2MB。
> ⚠️ 已知偶发问题：个别日期（如 9/5、9/19、9/20）抓到 **0 条**、报告仅 ~26KB。多为上游 API 当日无新数据或网络抖动；见「排查」一节。

一键查看历史：
```bash
.venv/bin/python -m neurodaily history
```

---

## 1. 启动 / 停止

### 1.1 一次性生成今天的报告（脚本模式，跑完即退）
```bash
.venv/bin/python -m neurodaily run            # 生成并自动用浏览器打开
.venv/bin/python -m neurodaily run --no-open  # 不自动打开
.venv/bin/python -m neurodaily run --output /path/to/x.html
.venv/bin/python -m neurodaily run --dedupe   # 若今天同样配置已跑过则跳过
.venv/bin/python -m neurodaily run            # 默认 --force 语义：显式跑就执行
```

### 1.2 启动常驻 Web 应用（含 GUI / 后台运行按钮）
```bash
.venv/bin/python -m neurodaily serve --port 8031
# 浏览器打开： http://127.0.0.1:8031
```
- 前台运行；**停止 = 在终端按 `Ctrl+C`**。
- 若想后台常驻：
  ```bash
  nohup .venv/bin/python -m neurodaily serve --port 8031 > output/webapp.log 2>&1 &
  ```

### 1.3 停止 Web 应用（后台/卡住时）
```bash
lsof -ti tcp:8031 | xargs kill        # 杀掉占用 8031 的进程
# 或按进程名：
pkill -f "neurodaily serve"
```

### 1.4 启动 / 停止 / 卸载“每日 08:00 定时任务”
```bash
# 安装（写入 ~/Library/LaunchAgents/ 并 load）
.venv/bin/python -m neurodaily launchd install

# 预览要写入的 plist
.venv/bin/python -m neurodaily launchd show

# 卸载（停止并删除）
.venv/bin/python -m neurodaily launchd uninstall

# 验证是否在册
launchctl list | grep neurodaily
```

**临时停用（保留安装）**：
```bash
launchctl unload -w ~/Library/LaunchAgents/com.neurodaily.daily.plist   # 停
launchctl load  -w ~/Library/LaunchAgents/com.neurodaily.daily.plist    # 恢复
```
**修改运行时间**：编辑 `config/config.json` 里的 `scheduled.hour / scheduled.minute`，然后重新 `launchd install`（plist 由 config 生成）。

> ℹ️ 注意：`scheduled.enabled` 字段对已安装的 plist **不生效**——要真正停用请用上面的 `unload` 或 `launchd uninstall`。

---

## 2. 配置（config.json）

配置文件位置（gitignored，属个人数据）：
```
~/neurodaily/config/config.json
```
默认路径也可从代码取得：`Config.default_path()`。

### 2.1 命令行配置
```bash
.venv/bin/python -m neurodaily config show          # 打印“结构化提示词”（当前关注点的可读摘要）
.venv/bin/python -m neurodaily config init          # 首次写入默认配置（已存在则拒绝）
.venv/bin/python -m neurodaily config init --force  # 覆盖为默认配置
```

### 2.2 命令行之外的配置方式
- **GUI（推荐）**：启动 web 应用后打开 `http://127.0.0.1:8031/settings`，可视化编辑全部设置并保存（见第 4 节）。
- **直接编辑 JSON**：修改 `config/config.json` 后，下次运行即生效（无需重启 web 应用，`Config.load()` 每次调用都会重读文件）。

### 2.3 config.json 各字段说明

| 字段 | 作用 |
|---|---|
| `profile` | 配置档名称（仅标签，如 `neuro`） |
| `disciplines[]` | 关注学科。每项：`name`、`arxiv_cats`（arXiv 分类）、`mesh_terms`（PubMed MeSH）、`bio_cats`（bioRxiv 分类）、`keywords`、`enabled` |
| `global_keywords[]` | 跨所有来源的通用关键词 |
| `sources{}` | 每个数据源：`enabled`、`max_results`、`lookback_days`（回看天数）。源包括 `journal` / `arxiv` / `pubmed` / `biorxiv` / `fda_drugs` / `fda_devices` / `trials` / `policy` |
| `output{}` | `dir`（报告目录）、`filename_format`（时间戳格式）、`open_on_finish`（跑完是否自动打开） |
| `scheduled{}` | `enabled`、`hour`、`minute`、`launchd{label,stdout,stderr}` |
| `policy_feeds[]` | 政策/新闻 RSS 地址列表（NIMH/NIDA/NINDS/Nature 子刊等） |
| `journals[]` | 顶级期刊观察列表：`name`、`url`、`rss`（有 RSS 的才会抓）、`category` |

### 2.4 常用调整示例
- **只想每天抓最近 1 天**：把 `sources.<每个源>.lookback_days` 改为 `1`。
- **加一个学科**：在 `disciplines` 追加一项（GUI 里点“添加学科”更简单）。
- **换报告目录**：`output.dir` 改路径，确保目录可写。
- **改定时时间**：`scheduled.hour/minute` → `launchd install`。

---

## 3. Web 应用路由（API）

启动 `serve` 后可访问：

| 路由 | 方法 | 用途 |
|---|---|---|
| `/` | GET | 仪表盘（最近一次结果 + 报告内联） |
| `/settings` | GET | **设置 GUI（可调所有配置）** |
| `/api/run` | POST | 后台立即跑一次（`?force=1` 跳过去重） |
| `/api/status` | GET | 最近运行状态 + 各源健康 |
| `/api/prompt` | GET | 结构化提示词 JSON |
| `/reports` | GET | 已生成报告列表 |
| `/reports/{file}` | GET | 读取某份报告 |
| `/history` | GET | 历史运行列表 |
| `/history/{id}` | GET | 某次运行详情 |
| `/api/history` | GET | 历史 JSON |
| `/api/config` | GET | 读取完整配置 JSON |
| `/api/config` | POST | 保存完整配置（写入 config.json） |
| `/api/config/reset` | POST | 重置为默认配置 |
| `/api/launchd/status` | GET | 定时任务安装/装载状态 |
| `/api/launchd/install` | POST | 安装并装载定时任务 |
| `/api/launchd/uninstall` | POST | 卸载定时任务 |

---

## 4. 设置 GUI 使用

1. 启动 web 应用：`.venv/bin/python -m neurodaily serve --port 8031`
2. 打开：**http://127.0.0.1:8031/settings**
3. 页面可编辑：`profile`、学科（增删改）、全局关键词、各数据源开关与 `max_results/lookback_days`、输出目录与文件名格式、定时开关与时间、政策 RSS、期刊列表。
4. 点击 **Save** 写入 `~/neurodaily/config/config.json`；点击 **Reset to defaults** 恢复默认；用 **Scheduler 区域** 直接 安装/卸载 定时任务并看到实时状态。
5. 保存后无需重启服务；下一次 `run` 或定时任务会读取新配置。

---

## 5. 排查（Troubleshooting）

| 现象 | 可能原因 / 处理 |
|---|---|
| 定时任务没跑 | `launchctl list \| grep neurodaily` 看是否在册；`tail -50 output/launchd_stdout.log` / `launchd_stderr.log`；确认 `~/Library/LaunchAgents` 存在 |
| 报告 0 条 / 很小 | 上游当日无新数据或网络抖动；看 `output/launchd_stdout.log` 里各源 `ok 0 items`。可把 `lookback_days` 调大（如 3–7）再试 |
| 某源报错 | 报告底部“Source Health”会显示 ✗ failed；多为限流/网络。稍后重试或临时禁用该源 |
| 端口被占用 | `lsof -ti tcp:8031 \| xargs kill`，或换 `--port` |
| 改了 config 不生效 | 确认改的是 `~/neurodaily/config/config.json`（不是 `config.example.json`） |
| 自动化失败但网络正常 | 检查 venv 路径：plist 里用的是安装时的 `sys.executable`；移动项目后需重新 `launchd install` |

日志位置：
- 定时任务：`output/launchd_stdout.log`、`output/launchd_stderr.log`
- Web 应用（若用 nohup）：`output/webapp.log`

---

## 6. 每日推送：「历史上的今天」+「🕸 图谱」

### 6.1 历史上的今天（每天 08:00 自动进报告 + 桌面通知）
- 报告顶部新增 **📅 历史上的今天** 板块；每日 08:00 定时任务生成报告时自动附带，并弹出 macOS 桌面通知。
- 内容聚焦**学术发现 / 关键手术 / 药物获批 / 器械技术**（不含出生、逝世）。
- **保证每天都有内容**：精确命中日显示当日事件；无精确记载的日子推送「近邻事件（≤3 天）」或「经典里程碑」，并在标签中**如实标注**，绝不伪造日期。
- 开关（写在 `config/config.json` 的 `scheduled.on_this_day`）：
  ```json
  "scheduled": {
    "on_this_day": { "enabled": true, "notify": true }
  }
  ```
  - `enabled: false` → 报告不显示该板块；
  - `notify: false` → 不弹桌面通知（仍显示在报告里）。
  - 缺省（不写）时两者默认开启。

### 6.2 🕸 图谱（每篇一键跳转）
- 报告里每个条目的底部新增 **🕸 图谱** 下拉，可一键打开：
  - **Connected Papers**（相似文献图）
  - **OpenAlex**（引用/被引/相关）
  - **Semantic Scholar**（含引用语境）
  - **本地引用网络 Local Citation Network**（开源，粘贴 DOI 即出图）
- 仅对被引用条目显示；「历史上的今天」卡片不显示。
- 纯前端实现（无新增依赖、不联网即生成链接）。

### 6.3 手动立即验证
```bash
.venv/bin/python -m neurodaily run --no-open
# 打开 output/ 下最新的 neurodaily_<时间>.html，检查顶部「历史上的今天」与条目底部「🕸 图谱」
```

### 6.4 深读池（长文）扩写

每日展示会优先从「深读池」（有长文的条目）中轮换，保证当天看到的是完整长文。

```bash
# 查看进度：总条目 / 已缓存 / 待扩写
.venv/bin/python -m neurodaily deepen --status

# 方式 A：用 LLM 批量扩写（质量最好，需 OpenAI 兼容 key）
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1   # 可选
.venv/bin/python -m neurodaily deepen --limit 50 --model gpt-4o-mini --concurrency 4

# 方式 B：离线模板扩写（无需 key，但文风模板化、信息密度低，仅作兜底）
.venv/bin/python -m neurodaily deepen --backend template --limit 50
```

- 生成结果缓存在 `neurodaily/data/onthisday_deep.json`，渲染时自动读取；新增条目无需改代码。
- LLM 提示词已强制「不得编造日期/数字/人名/试验名称」，只依据已给出的事实扩写。
- 也可以像 `scripts/seed_deep_batch1.py` 那样**手工分批**写入缓存（质量最高）。

### 6.5 每天早上自动邮件推送

每日 08:00 的 `neurodaily run` 完成后，会自动把当天结果渲染成 HTML 邮件并发送（若已配置密码）。

配置：`config/email.json`（从 `config/email.example.json` 复制；该文件已 gitignore）
```json
{
  "enabled": true,
  "smtp_host": "smtp.sjtu.edu.cn", "smtp_port": 465, "use_ssl": true,
  "username": "you@sjtu.edu.cn",
  "from": "you@sjtu.edu.cn",
  "to": ["you@example.com"],
  "password_file": "~/.neurodaily_smtp",
  "max_papers": 40, "max_other": 15
}
```

**密码只放本地文件（0600），不要写进仓库：**
```bash
printf '%s' '你的SMTP授权码' > ~/.neurodaily_smtp && chmod 600 ~/.neurodaily_smtp
```

命令：
```bash
.venv/bin/python -m neurodaily mail --test            # 发测试邮件
.venv/bin/python -m neurodaily mail --preview /tmp/mail.html   # 只渲染预览
.venv/bin/python -m neurodaily mail --send            # 立即跑一次并发送
.venv/bin/python -m neurodaily mail --send-latest     # 复用上次渲染的邮件重发（不跑检索）
```

> SJTU 邮箱通常需要在网页版邮箱设置里**开启 SMTP** 并使用「客户端专用密码/授权码」，而不是网页登录密码。
> 收件方（QQ 邮箱）若未收到，请检查垃圾邮件并加入白名单。

**收件人管理（TUI / 命令行）**
```bash
.venv/bin/python -m neurodaily mail --tui        # 全屏 TUI（见下方按键）
.venv/bin/python -m neurodaily mail --list       # 打印当前收件人
.venv/bin/python -m neurodaily mail --add a@b.com
.venv/bin/python -m neurodaily mail --remove a@b.com
```

TUI 按键：
`↑/↓` 选择 · `a` 增 · `d` 删 · `e` 改 · `t` 开关发送 · `p` 设置/更新授权码（隐藏输入，写入 600 权限文件）·
`x` 清除授权码 · `c` 配置 SMTP（host/port/SSL/账号/发件人）· `l` 条数上限 · `T` 发送测试邮件 · `s` 保存 · `q` 退出

> TUI 从不显示已保存的密码，只显示 `auth: set / MISSING`。

**邮件形态**（`config/email.json`）
```json
{
  "subject_template": "神经病专家的厕所读物-{date} {weekday}",
  "body_mode": "summary",        // summary=正文只放摘要；full=正文放全部条目
  "attach_report": true,         // 附带完整 HTML 报告
  "summary_papers": 12,          // 摘要里展示的论文数
  "summary_chars": 420,          // 历史上今天的摘要字数
  "smtp_timeout": 120
}
```
> 若附件导致投递失败，把 `attach_report` 设为 `false`，或把 `body_mode` 设为 `full` 去掉附件。

---

## 7. 上传到 GitHub

远程仓库：`https://github.com/Koalalive/neurodaily.git`（分支 `main`）。

### 6.1 一次性推送
```bash
cd ~/neurodaily
git add -A
git commit -m "docs: add operations manual + settings GUI"
git push origin main
```

### 6.2 如果 push 报认证失败（当前环境 `gh auth status` 显示 token 失效）
```bash
gh auth login -h github.com      # 交互式重新登录（推荐）
# 或使用 Personal Access Token：
#   git remote set-url origin https://<TOKEN>@github.com/Koalalive/neurodaily.git
#   git push origin main
```

### 6.3 提交内容说明
- 会被提交：源码 `neurodaily/`、`docs/`、`README.md`、`pyproject.toml`、`config.example.json` 等。
- **不会**被提交（`.gitignore` 已排除）：`output/`（报告/历史库/日志——个人数据）、`config/config.json`（含本地绝对路径）、`.venv/`、`scripts/*.plist`。
