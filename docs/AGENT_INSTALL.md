# Agent 安装与部署手册

> 面向自动化 Agent 的非交互安装、启动、验收与排障协议。覆盖 **macOS / 命令行 / Docker / GitHub Actions**。
> 所有命令均可在非交互终端执行；失败时先收集退出码和日志，不要猜测成功。

## 0. 目标与环境

| 场景 | 推荐方式 | 是否常驻 | 数据目录 |
|---|---|---|---|
| macOS 单机 | Homebrew tap + `neurodaily web` | 可选 | `~/Library/Application Support/NeuroDaily/` |
| Linux/macOS CLI | Python venv + wheel/源码 | 可选 | `NEURODAILY_HOME` 或当前用户目录 |
| 服务器 | Docker / Compose | 是 | 挂载 `config/` 与 `output/` |
| 定时更新 | GitHub Actions `daily-demo` | 云端 | GitHub Pages |

先确认基础命令：

```bash
python3 --version
git --version
curl --version
```

Agent 不得在日志中输出 API key、SMTP 密码、Docker token 或完整 `config/email.json`。

## 1. macOS：Homebrew 安装与启动

### 1.1 安装

```bash
brew tap koalalive/neurodaily https://github.com/Koalalive/neurodaily.git
brew install koalalive/neurodaily/neurodaily
brew info koalalive/neurodaily/neurodaily
```

### 1.2 启动工作区

```bash
# 后台启动，不自动打开浏览器，适合 Agent
neurodaily web --no-open
```

默认监听 `http://127.0.0.1:8031/desktop`。检查：

```bash
curl -fsS http://127.0.0.1:8031/api/status >/dev/null && echo "OK status"
curl -fsS http://127.0.0.1:8031/ >/dev/null && echo "OK home"
```

如果需要自定义端口：

```bash
neurodaily web --no-open --port 8032
```

### 1.3 停止与升级

```bash
# 前台运行时按 Ctrl+C；脚本中用 PID 管理
pkill -f 'neurodaily web' || true

brew update
brew upgrade koalalive/neurodaily/neurodaily
neurodaily web --no-open
```

macOS 数据目录：

```bash
ls -la "$HOME/Library/Application Support/NeuroDaily"
```

升级前备份：

```bash
tar czf "$HOME/Desktop/neurodaily-macos-$(date +%F).tgz" \
  "$HOME/Library/Application Support/NeuroDaily"
```

### 1.4 Agent 验收

- [ ] `command -v neurodaily`
- [ ] `neurodaily --version` 与目标版本一致
- [ ] `/api/status`、`/`、`/settings` 均返回 200
- [ ] 没有把 `config/email.json` 或 key 打印到日志
- [ ] 端口 8031 没有被另一个实例占用：`lsof -nP -iTCP:8031 -sTCP:LISTEN`

## 2. 命令行安装与运行（macOS/Linux）

### 2.1 从源码安装

```bash
git clone https://github.com/Koalalive/neurodaily.git
cd neurodaily
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e '.[topics]'
.venv/bin/python -c 'import neurodaily; print(neurodaily.__version__)'
```

### 2.2 离线演示（不需要网络和密钥）

```bash
.venv/bin/python -m neurodaily demo --no-open
ls -1 output/*.html | tail -1
```

### 2.3 配置校验与真实运行

```bash
# 只校验，不发起检索
.venv/bin/python -m neurodaily config validate

# 运行一次；默认输出到 output/
.venv/bin/python -m neurodaily run --no-open

# 查看帮助
.venv/bin/python -m neurodaily --help
```

使用独立数据目录：

```bash
export NEURODAILY_HOME="$PWD/.agent-home"
.venv/bin/python -m neurodaily config init
.venv/bin/python -m neurodaily run --no-open
```

### 2.4 从 wheel 安装

```bash
python3 -m venv .venv
.venv/bin/pip install /path/to/neurodaily-1.0.10-py3-none-any.whl
.venv/bin/neurodaily --version
.venv/bin/neurodaily demo --no-open
```

### 2.5 服务模式

```bash
.venv/bin/python -m neurodaily web --host 127.0.0.1 --port 8031 --no-open
curl -fsS http://127.0.0.1:8031/api/status
```

## 3. Docker 部署

### 3.1 快速验收（推荐 Agent 使用）

```bash
docker info >/dev/null 2>&1 || { echo 'FAIL: docker daemon is not running'; exit 1; }
bash scripts/docker_deploy.sh up
bash scripts/docker_deploy.sh verify
```

成功时应看到构建、容器启动、`/`、`/api/status`、`/api/config`、`/settings` 的 200 检查。

### 3.2 手动运行与持久化

```bash
docker build -t neurodaily:local .

docker run -d --name neurodaily \
  -p 127.0.0.1:8031:8031 \
  -v "$PWD/config:/app/neurodaily/config" \
  -v "$PWD/output:/app/neurodaily/output" \
  --restart unless-stopped \
  neurodaily:local
```

验收：

```bash
for i in $(seq 1 30); do
  curl -fsS http://127.0.0.1:8031/api/status >/dev/null && break
  sleep 1
done
for p in / /api/status /api/config /settings; do
  printf '%-16s %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:8031$p")"
done
docker logs --tail 80 neurodaily
```

### 3.3 Compose

```bash
docker compose up --build -d
docker compose logs -f --tail 80
docker compose down
```

### 3.4 停止、升级、回滚

```bash
bash scripts/docker_deploy.sh down
docker compose build --pull
bash scripts/docker_deploy.sh up

# 回滚示例
docker pull koalalive/neurodaily:20261120
docker tag koalalive/neurodaily:20261120 neurodaily:local
bash scripts/docker_deploy.sh run
```

### 3.5 Agent 验收

- [ ] `docker info` 成功
- [ ] 镜像存在：`docker images neurodaily:local`
- [ ] 容器 `Up`：`docker ps --filter name=neurodaily`
- [ ] 四个 HTTP 路径均为 200
- [ ] `docker logs` 无 `Traceback`
- [ ] 挂载的 `config/` 未被容器覆盖
- [ ] 没有把密码或 key 写进 Dockerfile/镜像

## 4. GitHub Actions 自动更新主页

公开仓库已配置：

| 工作流 | 时间 | 作用 |
|---|---|---|
| `daily-demo.yml` | 每天 `0 0 * * *` UTC = **08:00 Asia/Shanghai** | 生成 168h 中英俄 demo，提交 `docs/demo/`，触发 Pages 部署 |
| `daily.yml` | 可配置 | 真实检索/邮件 |
| `release-tauri.yml` | tag/手动 | 跨平台安装包与发布 |

手动触发并验收：

```bash
gh workflow run daily-demo.yml
sleep 5
gh run list --workflow daily-demo.yml --limit 3

# 下载/检查线上 demo 的试验计数
curl -fsSL https://koalalive.github.io/neurodaily/demo/latest-report.zh.html | \
  sed -n '/<section id="trials"/,/<\/h2>/p' | head -5
```

如果 Actions 因 60 天无活动被禁用：在 Actions 中重新启用 `daily-demo`，或手动运行一次并保持仓库有正常提交。

## 5. 失败处理与交接

1. 记录命令、退出码、run URL、失败 job/step。
2. 不删除失败日志；不要用 `continue-on-error` 掩盖真实回归。
3. Docker：先看 `docker logs` 与 `bash scripts/docker_deploy.sh verify`。
4. macOS：确认 Homebrew tap、Python 版本、端口占用和 Keychain 权限。
5. 发布：先看 `gh run view RUN_ID --log-failed`，再判断是产品回归还是 CI 基线兼容问题。
6. 任何涉及发布的变更必须记录在根目录 [HANDOFF.md](../HANDOFF.md)。

相关文档：[macOS Homebrew](MACOS_HOMEBREW.md) · [Docker](DOCKER.md) · [Docker Agent 协议](DOCKER_AGENT.md) · [GitHub Actions](GITHUB_ACTIONS.md)
