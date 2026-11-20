#!/usr/bin/env bash
# One-command local start: venv -> install -> init config -> serve
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -e .
if [ ! -f config/config.json ]; then
  .venv/bin/python -m neurodaily config init >/dev/null
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8031}"
echo "NeuroDaily → http://${HOST}:${PORT}"
exec .venv/bin/python -m neurodaily serve --host "$HOST" --port "$PORT" "$@"
