#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
bash desktop/build_sidecar.sh
cd desktop/tauri
npm install
npm run icon
npm run tauri build
echo "Artifacts: desktop/tauri/src-tauri/target/release/bundle/"
