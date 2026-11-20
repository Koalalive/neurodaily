# 安装要求与发行版

NeuroDaily 1.0.0 提供三种桌面安装包；终端用户**不需要安装 Python、Node 或 Rust**，运行时已随安装包打包。

## 1. 发行矩阵

| 平台 | 安装包 | 架构 | 最低系统 |
|---|---|---|---|
| macOS | `.dmg`（拖入 Applications） | Apple Silicon（arm64）、Intel（x86_64） | macOS 12 Monterey |
| Windows | `.msi` / `.exe`（NSIS） | x86_64 | Windows 10 1809+ / Windows 11 |
| Linux | `.AppImage` / `.deb` | x86_64 | Ubuntu 24.04（构建基线） |

> 所有安装包均附带本地 Web UI + Python sidecar；启动后不依赖外部 Web 服务。

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

- macOS 12 Monterey 及以上；Apple Silicon 与 Intel 分别提供安装包。
- 首次打开未签名/未公证版本时：
  - 右键 App → **打开**，或
  - `xattr -dr com.apple.quarantine /Applications/NeuroDaily.app`
- 数据目录：`~/Library/Application Support/NeuroDaily/`
  - `config/`、`output/`、`last_email.json`
- 端口：仅监听 `127.0.0.1` 随机端口，不触发防火墙入站提示。

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
  chmod +x NeuroDaily_1.0.0_amd64.AppImage
  ./NeuroDaily_1.0.0_amd64.AppImage
  ```
- 数据目录：`~/.local/share/neurodaily/`（或 `$XDG_DATA_HOME/neurodaily`）。

## 6. 首次启动与数据位置

1. 双击安装后的 NeuroDaily。
2. 首次启动打开设置页（若配置不存在）。
3. 选择/确认学科、期刊、RSS、时间窗口；可选填 DeepSeek key、SMTP。
4. 点 **Save & run now** 或 **Run now** 开始。

配置与输出都在用户数据目录，卸载应用不会删除；备份该目录即可迁移。

## 7. 安全与隐私

- 本地服务只监听 `127.0.0.1`，不对外网开放。
- API key/SMTP 密码建议用系统钥匙串或 `chmod 600` 文件；不要提交到 Git。
- 报告和数据库包含个人订阅内容，默认在本地。
- 邮件/Webhook 只有配置后才会发送。

## 8. 构建者要求（不是终端用户要求）

- Python 3.12+、Node 20+、Rust stable、PyInstaller。
- macOS 需 Xcode Command Line Tools；Windows 需 MSVC Build Tools；Linux 需 WebKitGTK 开发包。
- 详见 [`DESKTOP_TAURI.md`](DESKTOP_TAURI.md) 与 `.github/workflows/release-tauri.yml`。
