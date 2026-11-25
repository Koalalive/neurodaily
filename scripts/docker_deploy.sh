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

restore_legacy_settings() {
  local backup file target
  backup=$(mktemp -d "$PWD/output/.container-settings.XXXXXX")
  for file in config/ai_summary.json config/email.json config/webhooks.json config/journal_metrics.json output/last_email.json; do
    target="$backup/${file##*/}"
    if docker cp "$NAME:/app/$file" "$target" >/dev/null 2>"$backup/copy-error"; then
      chmod 600 "$target"
      if [[ ! -e "$PWD/$file" ]]; then
        cp -n "$target" "$PWD/$file"
      fi
    elif ! grep -qi 'could not find the file' "$backup/copy-error"; then
      printf '%s\n' 'Could not check the old container settings. The existing container was preserved.' >&2
      return 1
    fi
  done
  rm -f "$backup/copy-error"
  if ! rmdir "$backup" 2>/dev/null; then
    printf 'Backup of previous container settings: %s\n' "$backup"
  fi
}

run() {
  need_docker
  args=(-d --name "$NAME" -p "127.0.0.1:${PORT}:8031")
  if [ "$VOLUMES" = "1" ]; then
    mkdir -p config output
    if docker container inspect "$NAME" >/dev/null 2>&1; then
      restore_legacy_settings
    fi
    args+=(-v "$PWD/config:/app/neurodaily/config" -v "$PWD/output:/app/neurodaily/output")
  fi
  docker rm -f "$NAME" >/dev/null 2>&1 || true
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
