# GitHub Actions 部署（Agent 协议）

由 [GitHub Actions 手册](GITHUB_ACTIONS.md) 统一说明仓库配置、云端日报、安装包构建、签名发布和排障。

## 运行顺序

1. 用 `gh repo view OWNER/REPO --json visibility,defaultBranchRef` 确认目标仓库与默认分支。
2. 运行 `gh workflow run daily.yml -f demo=true`，从该次运行下载 `neurodaily-report` 并打开 `report.html`。
3. 按需校验研究配置并配置对应 Actions Secrets，再以 `demo=false` 手动运行。查看来源状态，配置邮件发送时再核对 SMTP 记录和收件结果。
4. 定时计划在默认分支的 `daily.yml`，云端日报从 Actions Artifacts 下载。
5. 构建桌面预览使用 `release-tauri.yml` 的分支模式。正式发布从匹配软件版本的标签构建，经实装回归和更新验签后出现在 Releases。

参阅 [每日运行、Secrets 与发布命令](GITHUB_ACTIONS.md)。
