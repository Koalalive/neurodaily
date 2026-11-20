#!/usr/bin/env bash
# Agent-friendly Docker deploy/verify. Usage: docker_deploy.sh [build|up|run|verify|logs|down]
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE="${IMAGE:-neurodaily:local}"
NAME="${NAME:-neurodaily}"
PORT="${PORT:-8031}"
DEMO="${DEMO:-0}"
VOLUMES="${VOLUMES:-1}"
CMD="${1:-up}"

need_docker() { docker info >/dev/null 2>&1 || { echo "FAIL: docker daemon not running"; exit 1; }; }

build() { need_docker; docker build -t "$IMAGE" . >/dev/null; echo "OK build $IMAGE"; }

run() {
  need_docker
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  args=(-d --name "$NAME" -p "127.0.0.1:${PORT}:8031")
  if [ "$VOLUMES" = "1" ]; then
    mkdir -p config output
    args+=(-v "$PWD/config:/app/neurodaily/config" -v "$PWD/output:/app/neurodaily/output")
  fi
  [ "$DEMO" = "1" ] && args+=(-e NEURODAILY_DEMO=1)
  docker run "${args[@]}" "$IMAGE" >/dev/null
  echo "OK run $NAME on 127.0.0.1:$PORT"
}

wait_health() {
  for _ in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>&1; then
      echo "OK health"; return 0
    fi
    sleep 1
  done
  echo "FAIL health"; docker logs "$NAME" 2>&1 | tail -20; exit 1
}

verify() {
  for p in "/" "/api/status" "/api/config" "/settings"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT}${p}")
    [ "$code" = "200" ] && echo "OK $p 200" || { echo "FAIL $p $code"; exit 1; }
  done
}

down() { docker rm -f "$NAME" >/dev/null 2>&1 && echo "OK removed $NAME" || echo "OK nothing to remove"; }

case "$CMD" in
  build) build ;;
  up) build; run; wait_health; verify ;;
  run) run; wait_health; verify ;;
  verify) verify ;;
  logs) docker logs "$NAME" 2>&1 | tail -50 ;;
  down) down ;;
  *) echo "usage: $0 [build|up|run|verify|logs|down]"; exit 2 ;;
esac
