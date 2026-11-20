# Docker 部署

> **中文** — 镜像构建、运行、compose 与 Docker Hub 推送。
> **English** — Image build, run, compose and Docker Hub push.
> **Русский** — Сборка образа, запуск, compose и публикация в Docker Hub.

> 已实测：镜像构建成功（**约 199 MB**），容器启动后 `/`、`/api/status`、`/api/config`、`/settings` 均返回 200，`docker compose config` 校验通过。

## 1. 前置

- Docker Desktop / Docker Engine（macOS 需先启动 Docker Desktop）
- 本机已构建或拉取镜像

```bash
docker info >/dev/null && echo "daemon ok"
```

## 2. 构建

```bash
cd neurodaily
docker build -t neurodaily:local .
```

Dockerfile 关键点：

| 项 | 值 | 说明 |
|---|---|---|
| 基础镜像 | `python:3.12-slim` | 体积小、兼容 3.12/3.13 代码 |
| `HOME` | `/app` | 配置与输出落在 `/app/neurodaily/` 下，便于挂载 |
| 端口 | `8031` | 容器内 `0.0.0.0:8031` |
| 启动 | `config init || true` → `serve --host 0.0.0.0` | 首次自动初始化配置 |

## 3. 运行

### 3.1 快速运行（无持久化）

```bash
docker run -d --name neurodaily -p 8031:8031 neurodaily:local
open http://127.0.0.1:8031
```

### 3.2 推荐：挂载配置与输出

```bash
docker run -d --name neurodaily \
  -p 8031:8031 \
  -v "$PWD/config:/app/neurodaily/config" \
  -v "$PWD/output:/app/neurodaily/output" \
  --restart unless-stopped \
  neurodaily:local
```

| 宿主机 | 容器 | 内容 |
|---|---|---|
| `./config` | `/app/neurodaily/config` | `config.json`、profile、email/ai/webhook 配置 |
| `./output` | `/app/neurodaily/output` | HTML 日报、历史库、缓存 |

### 3.3 docker compose

```bash
docker compose up --build -d
docker compose logs -f
docker compose down
```

`docker-compose.yml`：

```yaml
services:
  neurodaily:
    build: .
    ports:
      - "8031:8031"
    volumes:
      - ./config:/app/neurodaily/config
      - ./output:/app/neurodaily/output
    restart: unless-stopped
```

## 4. 环境变量

| 变量 | 说明 |
|---|---|
| `HOME` | 镜像内固定 `/app`（决定配置/输出路径） |
| `NEURODAILY_DEMO=1` | 仪表盘使用离线演示数据（等价 `serve --demo`） |
| `NEURODAILY_LLM_API_KEY` | 可选：AI 摘要 key（也可放挂载后的 `~/.neurodaily_llm`） |
| `NEURODAILY_SMTP_PASSWORD` | 可选：SMTP 授权码 |

> 凭据在容器内也可通过挂载配置文件提供；**不要把 key 写进镜像**。

## 5. 持久化与升级

```bash
# 备份
tar czf neurodaily-config-$(date +%F).tgz config output

# 升级
docker compose build --pull
docker compose up -d
```

报告裁剪由 `output.keep_reports` 控制（默认 60），容器内同样生效。

## 6. 推送 Docker Hub

### 6.1 手动

```bash
docker login -u <你的用户名>
docker tag neurodaily:local <用户名>/neurodaily:latest
docker tag neurodaily:local <用户名>/neurodaily:$(date +%Y%m%d)
docker push <用户名>/neurodaily:latest
docker push <用户名>/neurodaily:$(date +%Y%m%d)
```

### 6.2 脚本（推荐）

```bash
DOCKERHUB_USER=<你的用户名> ./scripts/push_dockerhub.sh
# 使用 access token（CI / 无交互）：
DOCKERHUB_USER=<用户名> DOCKERHUB_TOKEN=<token> ./scripts/push_dockerhub.sh
```

- 自动检查 daemon、登录、打 `latest` + 日期标签、推送
- 需要在 Docker Hub 先创建仓库 `<用户名>/neurodaily`（或推送时自动创建）

### 6.3 拉取运行（其他人）

```bash
docker run -d -p 8031:8031 --name neurodaily <用户名>/neurodaily:latest
```

## 7. 排障

| 现象 | 原因 | 解决 |
|---|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop 未启动/后端退出 | 打开 Docker Desktop，等 `docker info` 成功 |
| 端口被占用 | 8031 已有服务 | 改 `-p 8032:8031` |
| 容器启动即退出 | 配置目录权限/初始化失败 | `docker logs neurodaily`；确认挂载目录可写 |
| 页面空白 | 首次未初始化 | 容器内 CMD 已 `config init`；或手动 `docker exec neurodaily python -m neurodaily config init` |
| 邮件/AI 不工作 | 容器内没有凭据 | 挂载 `config/` 并在宿主机放 `~/.neurodaily_*`，或传环境变量 |
| 镜像过大 | 含缓存 | 使用多阶段/`.dockerignore`（已配置） |

## 8. 已验证结果

| 项 | 结果 |
|---|---|
| 构建 | ✅ `neurodaily:local` 199 MB |
| 启动 | ✅ `Uvicorn running on http://0.0.0.0:8031` |
| `/` | ✅ 200 |
| `/api/status` | ✅ 200 |
| `/api/config` | ✅ 200 |
| `/settings` | ✅ 200 |
| `docker compose config` | ✅ 通过 |
