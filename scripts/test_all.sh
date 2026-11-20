#!/usr/bin/env bash
# One-command test suite (no network, no email, no AI cost).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=".venv/bin/python"; [ -x "$PY" ] || PY="python3"

echo "[1/6] compile"
"$PY" -m compileall -q neurodaily scripts

echo "[2/6] unit tests"
"$PY" -m unittest discover -s tests

echo "[3/6] config validate"
"$PY" -m neurodaily config validate

echo "[4/6] offline demo report"
"$PY" -m neurodaily demo --no-open >/dev/null

echo "[5/6] export JSON + BibTeX"
"$PY" -m neurodaily export --demo --format both >/dev/null

echo "[6/6] profile + patch dry-run"
"$PY" -m neurodaily profile new _ci_profile >/dev/null
"$PY" -m neurodaily config apply config/examples/oncology.patch.json --profile _ci_profile --dry-run >/dev/null
rm -f config/profiles/_ci_profile.json

echo "ALL TESTS PASSED"
