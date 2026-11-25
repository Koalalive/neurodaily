# Docker 部署（Agent 协议）

> **中文** — Agent 的 Docker 部署协议（检查→构建→运行→验收→清理）。
> **English** — Agent protocol for Docker deployment (check → build → run → verify → clean).
> **Русский** — Протокол агента для развёртывания в Docker (проверка → сборка → запуск → приёмка → очистка).

> 给 Agent 的非交互部署流程：**检查 → 构建 → 运行 → 健康检查 → 验收 → 清理**。
> 所有命令返回明文 + 退出码；任何一步失败立即停止并打印日志。

## 0. 前置检查

```bash
docker info >/dev/null 2>&1 || { echo "FAIL: docker daemon not running"; exit 1; }
```

- 端口默认 `8031`（可用 `PORT` 覆盖）
- 容器名默认 `neurodaily`（可用 `NAME` 覆盖）

## 1. 一键（推荐）

```bash
# 构建 + 运行 + 健康检查 + 验收
bash scripts/docker_deploy.sh up

# 仅用已有镜像运行
bash scripts/docker_deploy.sh run

# 单独验收 / 查看日志 / 停止
bash scripts/docker_deploy.sh verify
bash scripts/docker_deploy.sh logs
bash scripts/docker_deploy.sh down
```

成功输出示例：

```
OK build neurodaily:local
OK run neurodaily on :8031
OK health
OK / 200
OK /api/status 200
OK /api/config 200
OK /settings 200
```

## 2. 手动步骤（等价）

```bash
# 构建
docker build -t neurodaily:local .

# 运行（挂载配置与输出）
docker run -d --name neurodaily \
  -p 127.0.0.1:8031:8031 \
  -v "$PWD/config:/app/neurodaily/config" \
  -v "$PWD/output:/app/neurodaily/output" \
  --restart unless-stopped \
  neurodaily:local

# 健康检查（最多 30s）
for i in $(seq 1 30); do
  curl -fsS http://127.0.0.1:8031/api/status >/dev/null && break
  sleep 1
done

# 验收
for p in / /api/status /api/config /settings; do
  printf "%s " "$p"; curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8031$p"
done
```

## 3. 验收标准（Agent 自检）

- [ ] `docker info` 成功
- [ ] 构建成功，镜像存在（`docker images neurodaily:local`）
- [ ] 容器 `Up`（`docker ps --filter name=neurodaily`）
- [ ] `/api/status` 200，且 30 秒内就绪
- [ ] `/`、`/api/config`、`/settings` 全部 200
- [ ] `docker logs` 无 `Traceback`
- [ ] 若挂了 `./config`，容器内 `config init` 不覆盖已有配置
- [ ] 重建容器后，设置中的 AI、邮件和 Webhook 仍可读取

## 4. 离线演示（答辩/断网）

```bash
DEMO=1 bash scripts/docker_deploy.sh up
# 或
docker run --rm -p 127.0.0.1:8031:8031 -e NEURODAILY_DEMO=1 neurodaily:local
```

## 5. 推送 Docker Hub

```bash
# 已登录（凭据存于 docker-credential-desktop）
docker tag neurodaily:local koalalive/neurodaily:latest
docker tag neurodaily:local koalalive/neurodaily:$(date +%Y%m%d)
docker push koalalive/neurodaily:latest
docker push koalalive/neurodaily:$(date +%Y%m%d)
```

或：

```bash
DOCKERHUB_USER=koalalive ./scripts/push_dockerhub.sh
```

### 更新仓库描述（三语）

仓库描述文件：`DOCKERHUB.md`（中文 → English → Русский）。
短描述（≤100 字符）：

```
NeuroDaily：神经科学每日情报+AI精读｜Self-hosted neuroscience digest｜Нейродайджест
```

用 API 更新（需要 PAT）：

```bash
curl -u koalalive:$DOCKERHUB_TOKEN -X PATCH \
  -H "Content-Type: application/json" \
  -d "$(python3 -c 'import json;print(json.dumps({"full_description":open("DOCKERHUB.md").read()}))')" \
  https://hub.docker.com/v2/repositories/koalalive/neurodaily/
```

## 6. 升级 / 回滚

容器将配置和运行数据写入 `NEURODAILY_HOME=/app/neurodaily`，与默认绑定的 `config` 和 `output` 目录一致。旧容器可能将 AI、邮件、Webhook 或期刊指标写在 `/app/config`。使用部署脚本升级时，保留现有容器，直接执行 `bash scripts/docker_deploy.sh up`。脚本会在替换容器前将旧文件备份到 `output/.container-settings.*`，并补齐宿主机缺少的文件。

直接使用 Compose 或 `docker run` 升级时，先查看并备份旧容器 `/app/config` 中仍需要的文件，再合并到宿主机 `config`。备份可能含凭据，请保存在本机的私有目录中。

```bash
# 升级
bash scripts/docker_deploy.sh up

# 回滚到某个标签
docker pull koalalive/neurodaily:20261120
docker tag koalalive/neurodaily:20261120 neurodaily:local
bash scripts/docker_deploy.sh run
```

## 7. 排障

| 现象 | 处理 |
|---|---|
| `Cannot connect to the Docker daemon` | 启动 Docker Desktop，等 `docker info` 成功 |
| `port is already allocated` | `PORT=8032 bash scripts/docker_deploy.sh up` |
| 容器反复重启 | `docker logs neurodaily --tail 50`；检查挂载目录权限 |
| 页面 502/空白 | 等 `/api/status` 就绪；首次会执行 `config init` |
| 邮件/AI 失效 | 容器内没有凭据：挂载 `config/` 并在宿主机放 `~/.neurodaily_*`，或用环境变量 |
| 推送 401 | `docker login` 重新登录，或用 `DOCKERHUB_TOKEN` |

## 8. 安全

- 不要把 API key/SMTP 密码写进镜像或 `Dockerfile`
- 凭据用环境变量或挂载的 600 权限文件
- 容器内服务监听 `0.0.0.0:8031`，由 `-p 127.0.0.1:8031:8031` 可限制为仅本机
