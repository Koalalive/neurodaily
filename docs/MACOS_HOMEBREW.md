# macOS 安装与启动

在 macOS 上，通过项目的 Homebrew tap 安装 NeuroDaily，用浏览器查看本机日报、设置和运行历史。先完成 Homebrew 的终端环境配置。 [Homebrew 安装文档](https://docs.brew.sh/Installation)

## 首次安装

在终端添加 tap 并安装公式。

```bash
brew tap koalalive/neurodaily https://github.com/Koalalive/neurodaily.git
brew install koalalive/neurodaily/neurodaily
```

tap 和源代码来自同一个 GitHub 仓库。公式从 Git 版本标签安装项目，并由 Homebrew 准备 Python 3.13 和运行依赖。`brew tap` 的双参数形式让 Homebrew 直接使用项目的 HTTPS 地址。 [Homebrew tap 文档](https://docs.brew.sh/Taps)

## 启动和停止

```bash
neurodaily web
```

服务启动后会在默认浏览器打开 `http://127.0.0.1:8031/desktop`。可在设置页选择神经科学、肿瘤学或重症医学，设置检索时间和推送渠道。设置、历史与新日报在各自的标签页里查看。

```bash
neurodaily web --no-open
```

该命令适合想手动打开页面的情况。关闭浏览器页面后服务继续运行。在启动命令所在的终端按 **Ctrl+C** 停止服务，定时检索和推送随之停止。

## 升级和沿用现有资料

如果仍在运行旧版桌面应用，先退出，再启动 Homebrew 版本，避免两个进程定时发送同一份日报。macOS 版使用 `~/Library/Application Support/NeuroDaily/` 作为数据目录，可沿用旧版保存在这里的配置、日报和历史。备份这整个目录即可保留可迁移的数据。

停止正在运行的服务后，在终端执行升级并重启。

```bash
brew update && brew upgrade koalalive/neurodaily/neurodaily
neurodaily web
```

## 常见问题

| 现象 | 核对方法 |
|---|---|
| `brew: command not found` | 安装 Homebrew，并按安装程序提示将 `brew shellenv` 加到当前 shell 的配置中 |
| 旧 tap 拉取时提示 `Permission denied (publickey)` | 用 `git -C "$(brew --repository koalalive/neurodaily)" remote set-url origin https://github.com/Koalalive/neurodaily.git` 改用 HTTPS |
| Intel Mac 的 `python@3.13` 与 Python.org 链接冲突 | 先运行 `brew install --skip-link python@3.13`，再安装 NeuroDaily。配方通过 Homebrew 的版本目录访问 Python |
| 浏览器没有自动打开 | 如果服务已启动，可直接访问 `http://127.0.0.1:8031/desktop` |
| 端口 8031 已被占用 | 用 `lsof -nP -iTCP:8031 -sTCP:LISTEN` 确认是否已有实例。如需使用其他端口，可运行 `neurodaily web --port 8032` |
| 看不到新版本 | 先运行 `brew update`，再执行 `brew info koalalive/neurodaily/neurodaily` 查看 tap 提供的版本 |

GitHub Actions 的 macOS 安装测试与 Windows、Linux 发布流程见 [GitHub Actions 手册](GITHUB_ACTIONS.md)。
