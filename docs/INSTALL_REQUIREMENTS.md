# 安装要求与发行版

macOS 用户通过私有 Homebrew tap 安装 NeuroDaily。Windows 和 Linux 用户使用附带 Python 运行时的桌面安装包。

## 1. 发行矩阵

| 平台 | 安装方式 | 架构 | 系统要求 |
|---|---|---|---|
| macOS | 私有 Homebrew tap | Apple Silicon（arm64）、Intel（x86_64） | 可运行 Homebrew 与公式依赖的 macOS。详见 [Homebrew 安装要求](https://docs.brew.sh/Installation) |
| Windows | `.msi` / `.exe`（NSIS） | x86_64 | Windows 10 1809+ / Windows 11 |
| Linux | `.AppImage` / `.deb` | x86_64 | Ubuntu 24.04（构建基线） |

Windows 和 Linux 安装包内置 Web UI 与 Python sidecar。macOS 公式由 Homebrew 准备 Python 3.13 和运行依赖。三平台的界面均由本机服务提供。

## 2. 通用软硬件要求

| 项目 | 最低 | 推荐 |
|---|---|---|
| CPU | 双核 64 位 | 四核及以上 |
| 内存 | 2 GB | 4 GB+（AI 摘要 + 大报告更稳） |
| 磁盘 | 600 MB（应用） | 2 GB+（报告、缓存、历史） |
| 网络 | 可访问 PubMed / arXiv / bioRxiv / 期刊 RSS | 稳定宽带；API 限流时更从容 |
| 显示 | 1024×700 | 1280×860+ |
| 权限 | 普通用户即可 | — |

### 可选依赖

- **AI 摘要**：DeepSeek 官方 API key（默认 `deepseek-flash`）；没有 key 时报告仍可生成。
- **邮件推送**：SMTP 账号/授权码 + 收件人；不配置则只生成本地报告。
- **Webhook**：飞书/企业微信机器人 URL（可选）。
- **Docker 替代**：Docker Desktop 4.x（仅在不想安装桌面包时使用）。

## 3. macOS

准备 Homebrew 和可以读取私有仓库的 GitHub SSH 密钥。完整命令见 [macOS 安装指南](MACOS_HOMEBREW.md)。

运行 `neurodaily web` 后，通过默认浏览器访问 `http://127.0.0.1:8031/desktop`。数据目录为 `~/Library/Application Support/NeuroDaily/`，可沿用旧版在该位置保存的配置、历史和日报。在启动服务的终端按 **Ctrl+C** 停止检索和定时推送。

## 4. Windows

- Windows 10 1809+ 或 Windows 11，x86_64。
- 需要 **WebView2 Runtime**：
  - Windows 11 通常已内置；
  - 安装包内嵌 WebView2 离线安装程序，缺失时由安装包处理。
- 数据目录：`%APPDATA%\NeuroDaily\`
- 未签名安装包会触发 SmartScreen：选择「更多信息 → 仍要运行」。
- 端口仅绑定 `127.0.0.1`。

## 5. Linux

- Linux x86_64 安装包在 Ubuntu 24.04 构建，其他发行版需验证系统库兼容性。
- 运行依赖（`.deb` 会自动安装；AppImage 需系统已有）：
  ```bash
  sudo apt install libwebkit2gtk-4.1-0 libgtk-3-0 libayatana-appindicator3-1
  ```
- AppImage：
  ```bash
  chmod +x NeuroDaily_1.0.6_amd64.AppImage
  ./NeuroDaily_1.0.6_amd64.AppImage
  ```
- 数据目录：`~/.local/share/neurodaily/`（或 `$XDG_DATA_HOME/neurodaily`）。

## 6. 首次启动与数据位置

1. Windows 和 Linux 双击安装后的 NeuroDaily。macOS 在终端运行 `neurodaily web`。
2. 在设置页选「神经科学」「肿瘤学」或「重症医学」预设，也可沿用保存的设置。
3. 确认学科、期刊、RSS 和时间窗口，保存设置并进入检索页。
4. 点击 **开始检索**。报告生成后自动在新标签页打开。

在设置页启用定时检索并保存后，NeuroDaily 按本地时间运行。Windows 和 Linux 最小化窗口时服务继续运行，退出应用前会提示。macOS 的服务随终端进程运行，浏览器页面关闭后仍可按时检索。独立系统定时任务由系统调度器管理。

配置与输出都在用户数据目录，卸载应用不会删除；备份该目录即可迁移。

## 7. 安全与隐私

- 本地服务只监听 `127.0.0.1`，不对外网开放。
- API key/SMTP 密码建议用系统钥匙串或 `chmod 600` 文件；不要提交到 Git。
- 报告和数据库包含个人订阅内容，默认在本地。
- 邮件/Webhook 只有配置后才会发送。

## 8. 构建者要求（不是终端用户要求）

- Python 3.12+、Node 20+、Rust stable、PyInstaller。
- Windows 需 MSVC Build Tools，Linux 需 WebKitGTK 开发包。桌面构建见 [Tauri 桌面指南](DESKTOP_TAURI.md)，各平台自动化见 [GitHub Actions 手册](GITHUB_ACTIONS.md)。
