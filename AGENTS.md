# AGENTS.md

Agent 入口。**改配置前先读 [`docs/AGENT_GUIDE.md`](docs/AGENT_GUIDE.md)**。

## 非交互配置协议
```bash
neurodaily config describe                  # 可配置项 + 补丁语义
neurodaily config schema --out schema.json  # JSON Schema
neurodaily config apply patch.json --dry-run [--profile NAME]
neurodaily config apply patch.json [--profile NAME]
neurodaily config validate [--profile NAME]
```

## 独立学科配置（不动默认）
```bash
neurodaily profile new oncology
neurodaily --profile oncology demo --no-open     # 离线冒烟
neurodaily --profile oncology run --no-open      # 真正跑一次
```

## 其他
```bash
neurodaily demo --no-open                       # 离线演示
neurodaily export --format json|bibtex|both     # 数据导出
neurodaily webhook --test                       # 飞书/企微
scripts/start.sh                                # 一键启动
docker compose up --build                       # 容器启动
bash scripts/docker_deploy.sh up                # 容器：构建+运行+验收
bash scripts/docker_deploy.sh down              # 停止容器
# Docker 部署协议见 docs/DOCKER_AGENT.md
```

## 禁止提交
`config/profiles/`、`config/email.json`、`config/webhooks.json`、`competition/`、`output/`
