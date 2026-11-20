#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="$ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "missing .venv; create it with: python3 -m venv .venv && .venv/bin/pip install -e ." >&2
  exit 1
fi

"$PY" -m pip install --quiet --upgrade pyinstaller
"$PY" -m PyInstaller --clean --noconfirm desktop/sidecar/neurodaily-server.spec

TRIPLE="$(rustc -vV | awk '/^host:/{print $2}')"
mkdir -p desktop/tauri/src-tauri/binaries
cp dist/neurodaily-server "desktop/tauri/src-tauri/binaries/neurodaily-server-$TRIPLE"
chmod +x "desktop/tauri/src-tauri/binaries/neurodaily-server-$TRIPLE"
echo "sidecar -> desktop/tauri/src-tauri/binaries/neurodaily-server-$TRIPLE"
