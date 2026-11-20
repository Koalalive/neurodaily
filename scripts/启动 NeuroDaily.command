#!/bin/bash
# Double-click to start NeuroDaily and open the settings page.
cd "$(dirname "$0")/.." || exit 1
PORT="${PORT:-8031}"
if lsof -ti tcp:"$PORT" >/dev/null 2>&1; then
  open "http://127.0.0.1:$PORT/settings"
  exit 0
fi
mkdir -p output
nohup .venv/bin/python -m neurodaily serve --port "$PORT" > output/webapp.log 2>&1 &
sleep 3
open "http://127.0.0.1:$PORT/settings"
