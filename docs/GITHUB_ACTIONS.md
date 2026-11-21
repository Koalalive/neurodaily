# 在 GitHub Actions 上运行 NeuroDaily

GitHub Actions 可以每天生成一份日报，也可以检查 macOS Homebrew 安装、构建 Windows 和 Linux 安装包。日报从私有仓库的运行记录下载，Windows 和 Linux 安装包在同一仓库的 Releases 下载。macOS 通过私有 Homebrew tap 安装。 [macOS 指南](MACOS_HOMEBREW.md)

## 选择工作流

| 文件 | 用途 | 触发条件 | 产物 |
|---|---|---|---|
| [daily.yml](../.github/workflows/daily.yml) | 在 Linux runner 检索，按配置发送邮件 | 默认分支日程，或 **Run workflow** | `neurodaily-report` 中的 `report.html`，保留 14 天 |
| [ci.yml](../.github/workflows/ci.yml) | 在 Python 3.12 和 3.13 上做离线测试 | Pull Request，或推送 `main` | 测试日志 |
| [release-tauri.yml](../.github/workflows/release-tauri.yml) | 验证 macOS Homebrew 安装，构建和回归 Windows、Linux 安装包，发布签名更新 | 手动运行、`release/**`、`verify/**` 或 `v*` 标签 | 预览安装包或正式 Windows、Linux Release 资产 |

## 1. 首次运行离线日报

1. 登录 GitHub，打开私有仓库的 **Actions**。如果仓库策略禁用了 Actions，请在 **Settings → Actions → General** 启用仓库允许使用的工作流。使用命令行时先运行 `gh auth login --hostname github.com`。
2. 选左侧 **daily-digest**，点 **Run workflow**，选 `main`，勾选 **Run with offline demo data** 后运行。手动运行需要仓库写权限，且该工作流文件须已存在于默认分支。[GitHub 手动运行文档](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
3. 打开本次运行，下载 **Artifacts → neurodaily-report**，解压并用浏览器打开 `report.html`。此模式使用内置示例，跳过实时检索、AI 请求和推送。下载需要登录并有仓库读取权限。[GitHub Artifact 文档](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)

命令行执行同一流程。用 `run list` 输出中的本次运行编号替换 `RUN_ID`。

```bash
repo=Koalalive/neurodaily
gh repo view "$repo" --json visibility,defaultBranchRef
gh workflow run daily.yml --repo "$repo" --ref main -f demo=true
gh run list --repo "$repo" --workflow daily.yml --event workflow_dispatch --limit 5 \
  --json databaseId,status,conclusion,createdAt,url
gh run watch RUN_ID --repo "$repo" --exit-status
gh run download RUN_ID --repo "$repo" -n neurodaily-report --dir ./digest-download
```

## 2. 使用自己的检索配置

实际检索可直接运行。没有 `NEURODAILY_CONFIG_JSON` 时使用内置默认配置。要更换学科、检索式或数据源，请先在本机校验完整配置，再到 **Settings → Secrets and variables → Actions → New repository secret** 上传。桌面端导出的共享对象带 `format`、`version` 和 `config` 外层，Actions Secret 使用完整的研究配置 JSON。可用本机配置文件，或从共享对象提取 `.config` 后校验。 [配置手册](CONFIGURATION.md) · [GitHub Secrets 文档](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)

```bash
.venv/bin/python -m neurodaily --config config/config.json config validate
gh secret set NEURODAILY_CONFIG_JSON --repo "$repo" < config/config.json
gh workflow run daily.yml --repo "$repo" --ref main -f demo=false
```

从桌面共享文件复用检索条件时，可以用 `jq -e '.config' research-profile.json > actions-config.json` 提取配置，然后用上面的校验命令检查 `actions-config.json` 再上传。

工作流将配置写入 runner 临时目录，通过 `NEURODAILY_HOME` 供 CLI 读取，并将最终日报固定输出到 `output/report.html`。上传步骤只选这一份 HTML。配置、密码文件、SQLite 历史和 AI 缓存留在 runner 数据目录内。日报内容可包含检索主题与条目链接，应按课题组的分享范围管理仓库成员。认证凭据通过 Secrets 注入，查询或订阅 URL 适合使用可写入日报的地址。

## 3. 可选邮件和 AI 摘要

以下步骤都可在私有仓库的 **Actions secrets** 中操作。SMTP 和模型配置分别以 [邮件模板](../config/email.example.json) 和 [AI 模板](../config/ai_summary.example.json) 为起点，记得使用实际服务商的 SMTP 地址、端口、加密方式和模型名称。

| Secret | 何时配置 | 值 |
|---|---|---|
| `NEURODAILY_EMAIL_JSON` | 需要邮件时 | 完整邮件 JSON，`enabled` 为 `true`，填写 `smtp_host`、`smtp_port`、`use_ssl`、`username`、`from` 和 `to`。`password_env` 用 `NEURODAILY_SMTP_PASSWORD` |
| `NEURODAILY_SMTP_PASSWORD` | 需要邮件时与上一项一起配置 | SMTP 授权码或应用专用密码 |
| `NEURODAILY_AI_JSON` | 需要指定 API 服务器、模型或其他 AI 参数时 | `base_url`、`model` 等配置。`api_key_env` 用 `NEURODAILY_LLM_API_KEY`，默认兼容 `DEEPSEEK_API_KEY` |
| `NEURODAILY_LLM_API_KEY` | 需要 AI 摘要时 | OpenAI 兼容服务的 API key |

```bash
gh secret set NEURODAILY_EMAIL_JSON --repo "$repo" < config/email.json
gh secret set NEURODAILY_SMTP_PASSWORD --repo "$repo"
# 以下两项仅在需要 AI 时执行
gh secret set NEURODAILY_AI_JSON --repo "$repo" < config/ai_summary.json
gh secret set NEURODAILY_LLM_API_KEY --repo "$repo"
gh secret list --repo "$repo"
```

首次发送建议用一个受控收件地址。跑 `demo=false` 后分别看日报、运行日志里的 `delivery` 状态和收件箱。运行成功表示流程完成，邮箱是否收到由 SMTP 接受情况和邮箱投递规则决定。当前工作流直接接入邮件与 AI 的 Secrets。桌面端可以在设置页另行配置飞书与企业微信。

## 4. 调整日程和存档

`daily.yml` 中的 `0 0 * * *` 按 UTC 解释，对应北京时间每天 08:00。想改为北京时间 08:15，可以把 cron 改成 `15 0 * * *`，再把改动合入默认分支。整点高峰会使任务晚于预定时间启动。应用内定时与 Actions cron 各自负责启动自己的进程。若只需要一封邮件，请让一个运行环境负责该配置的定时发送。[GitHub schedule 文档](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

GitHub 托管 runner 每次运行使用独立环境。本机日报、已推送标记和历史去重状态不会自动跨运行共享。需要长期保留某份日报时从 Artifact 下载，或在自己的持久存储中运行定时检索。暂停云端日程可以在 **Actions → daily-digest → … → Disable workflow** 操作。[GitHub 工作流启停文档](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)

## 5. 构建桌面预览与正式发布

### 预览安装包

在 **Actions → Release NeuroDaily → Run workflow** 选择要验证的分支，或将已提交的候选代码推送到 `release/<版本>-preview`。成功的预览产物可以用于 `verify/<版本>` 分支的补充安装回归。例如 `verify/v1.0.6` 查找 `release/v1.0.6-preview` 最近一次成功推送的 Windows 和 Linux 产物。只需检查 Homebrew 时，可使用 `verify/homebrew-<说明>` 分支。检查运行对应的 commit，确保验证的是准备发布的版本。

```bash
gh workflow run release-tauri.yml --repo "$repo" --ref release/v1.0.6-preview
gh run list --repo "$repo" --workflow release-tauri.yml --branch release/v1.0.6-preview --limit 5
gh run view RUN_ID --repo "$repo"
gh run download RUN_ID --repo "$repo" -n neurodaily-x86_64-pc-windows-msvc --dir ./preview-win
```

| Runner | 安装方式 | 发布前检查 |
|---|---|---|
| `macos-15` 和 `macos-15-intel` | Apple Silicon 和 Intel 通过 Homebrew 公式安装 | **Verify macOS Homebrew** 执行 `bash scripts/test_homebrew.sh`，检查公式安装及 `neurodaily web` 的本地服务 |
| `windows-latest` | x64 NSIS `.exe` 和 `.msi` | NSIS 全新安装和覆盖升级，MSI 安装和卸载 |
| `ubuntu-24.04` | x64 `.deb` 和 `.AppImage` | DEB 安装和升级，AppImage 解包运行，GTK 保存和外链调用 |

Windows 和 Linux 先冻结 Python sidecar，再用 Tauri 构建应用。升级测试用隔离目录保留上一正式版的配置、历史和定时记录。当前回归基线为 v1.0.4。后续发布切换基线时，同步检查工作流中的 `BASELINE_TAG` 和对应安装包文件名。macOS 利用同一私有仓库的 `Formula/neurodaily.rb`，从 Git 版本标签和固定版本的 Python 依赖安装。 [桌面架构](DESKTOP_TAURI.md) · [测试矩阵](TESTING.md)

### 发布带更新签名的版本

1. 更新 `pyproject.toml`、`neurodaily/__init__.py`、`desktop/tauri/package.json`、`desktop/tauri/src-tauri/Cargo.toml`、`tauri.conf.json` 以及对应锁文件中的应用版本。更新 `Formula/neurodaily.rb` 中的稳定版本和 Git 标签。先跑上面的预览和实装验证，再把发布提交合入默认分支。
2. 在 **Settings → Secrets and variables → Actions** 检查 `TAURI_SIGNING_PRIVATE_KEY` 和 `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`。Windows 和 Linux 使用与已安装应用公钥配对的私钥签名，使现有安装可以接受更新。Windows Authenticode 使用单独的凭据。 [桌面签名说明](DESKTOP_TAURI.md)
3. 给已审核的提交创建与应用版本一致的 `v<版本>` 标签并推送。示例从 `tauri.conf.json` 读当前版本，请确认这个版本号尚未发布。

```bash
git fetch origin main
git switch main
git pull --ff-only
version=$(python3 -c 'import json; print(json.load(open("desktop/tauri/src-tauri/tauri.conf.json"))["version"])')
git tag -a "v$version" -m "NeuroDaily v$version"
git push origin "refs/tags/v$version"
gh run list --repo "$repo" --workflow release-tauri.yml --commit "$(git rev-parse HEAD)" --limit 5
```

4. 等待全部安装测试和 `publish` 作业。工作流核验 Windows 和 Linux 安装包、更新签名和签名中的版本号，再把完整资产上传至草稿，最后将 Release 设为最新正式版。macOS 可以通过私有 tap 更新到对应发布标签。

```bash
gh run watch RUN_ID --repo "$repo" --exit-status
gh release view "v$version" --repo "$repo" --json isDraft,isPrerelease,assets,url \
  --jq '{isDraft,isPrerelease,url,assets:[.assets[].name]}'
```

Releases 包含 Windows NSIS 和 MSI、Linux DEB 和 AppImage，共 4 个安装包与对应的 4 个 `.sig`。协作者用自己的 GitHub 登录下载。Windows 和 Linux 可在应用内配置仅能读取此仓库内容的更新令牌。macOS 使用 `brew update && brew upgrade koalalive/neurodaily/neurodaily`。 [桌面更新授权](DESKTOP_TAURI.md#private-desktop-updates) · [macOS 升级](MACOS_HOMEBREW.md)

## 6. 查日志和排障

| 问题 | 核对位置 |
|---|---|
| 找不到 **Run workflow** | 默认分支是否已有工作流文件，是否具有写权限，该工作流是否处于启用状态 |
| 日报 Artifact 缺失 | 查看 **Run digest** 和 **Upload artifact**。正常运行应写出 `output/report.html` |
| 结果为 0 或为空 | 打开日报的来源状态，区分无匹配、超时和来源失败，核对配置文件与检索时间窗口 |
| 邮件失败 | 核对邮件 JSON 的 `to`、SMTP 授权码、端口和加密方式。验证服务商是否允许 GitHub runner 所在网络连接 |
| AI 摘要缺失 | 核对 `enabled`、模型名、`base_url` 和 API key 环境变量。日报可独立生成 |
| Release 无新资产 | 查看标签对应运行，查找第一个失败的构建、实装或验签步骤。`gh run view RUN_ID --log-failed` 可下载失败日志。短暂网络故障可用 `gh run rerun RUN_ID --failed` 重跑对应作业 |

私有仓库首页使用 [README](../README.md)。如果团队另需一个登录后访问的静态站点，先核对组织是否具备 GitHub Enterprise Cloud 的私有 Pages 访问控制。 [GitHub 私有 Pages 文档](https://docs.github.com/en/enterprise-cloud%40latest/pages/getting-started-with-github-pages/about-privately-published-github-pages-sites)
