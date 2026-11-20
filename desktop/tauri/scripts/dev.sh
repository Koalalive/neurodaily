#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
bash desktop/build_sidecar.sh
TRIPLE="$(rustc -vV | awk '/^host:/{print $2}')"
export NEURODAILY_SIDECAR="$ROOT/desktop/tauri/src-tauri/binaries/neurodaily-server-$TRIPLE"
cd desktop/tauri
npm install
npm run icon
npm run tauri dev
