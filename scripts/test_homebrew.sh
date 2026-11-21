#!/usr/bin/env bash
set -euo pipefail

if [[ "${RUNNER_OS:-}" != macOS || "${RUNNER_ENVIRONMENT:-}" != github-hosted ]]; then
  printf '%s\n' 'Run this installation test on a disposable GitHub-hosted macOS runner.' >&2
  exit 1
fi

repo=$(git rev-parse --show-toplevel)
source_formula="$repo/Formula/neurodaily.rb"
release=$(sed -nE 's/.*tag: "(v[0-9.]+)".*/\1/p' "$source_formula")
[[ "$release" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]
version=${release#v}
tap=koalalive/neurodaily
formula="$tap/neurodaily"
legacy_home="$HOME/Library/Application Support/NeuroDaily"
export HOMEBREW_NO_AUTO_UPDATE=1
export HOMEBREW_NO_INSTALL_CLEANUP=1

if brew tap | grep -Fxq "$tap" || [[ -e "$(brew --cellar)/neurodaily" ]]; then
  printf '%s\n' 'The runner already has the NeuroDaily tap or formula.' >&2
  exit 1
fi
if [[ -e "$legacy_home" || -L "$legacy_home" ]]; then
  printf '%s\n' 'The runner already has desktop data. Keep it intact and use a fresh runner.' >&2
  exit 1
fi

scratch=$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/neurodaily-homebrew.XXXXXX")
server_pid=""
tapped=0
installed=0
created_legacy_home=0
cleanup() {
  local result=$?
  if [[ -n "$server_pid" ]]; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
  if (( result != 0 )) && [[ -f "$scratch/web.log" ]]; then
    cat "$scratch/web.log" >&2
  fi
  if (( installed )); then
    brew uninstall --formula "$formula" || true
  fi
  if (( tapped )); then
    brew untap "$tap" || true
  fi
  if (( created_legacy_home )); then
    rm -rf -- "$legacy_home"
  fi
  rm -rf -- "$scratch"
  return "$result"
}
trap cleanup EXIT

# Intel hosted images also provide Python.org's versioned links in /usr/local/bin.
# The formula uses Homebrew's opt/bin path, so the dependency needs no global links.
brew install --skip-link python@3.13

commit=$(git -C "$repo" rev-parse HEAD)
git clone --quiet --no-hardlinks --no-tags "$repo" "$scratch/source"
git -C "$scratch/source" checkout --quiet --detach "$commit"
git -C "$scratch/source" tag "$release" "$commit"

mkdir -p "$scratch/tap/Formula"
sed "s|ssh://git@github.com/Koalalive/neurodaily.git|file://$scratch/source|" \
  "$source_formula" > "$scratch/tap/Formula/neurodaily.rb"
git -C "$scratch/tap" init --quiet --initial-branch=main
git -C "$scratch/tap" add Formula/neurodaily.rb
git -C "$scratch/tap" -c user.name='NeuroDaily CI' -c user.email=ci@example.invalid \
  commit --quiet -m 'Verify the formula from the candidate checkout'

brew tap "$tap" "file://$scratch/tap"
tapped=1
installed=1
brew install --formula "$formula"
brew test "$formula"

python="$(brew --prefix python@3.13)/bin/python3.13"
entry="$(brew --prefix "$formula")/bin/neurodaily"
port=$("$python" -c 'import socket
with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    print(probe.getsockname()[1])')
app_home="$scratch/app-home"
NEURODAILY_HOME="$app_home" "$entry" web --no-open --port "$port" > "$scratch/web.log" 2>&1 &
server_pid=$!

base_url="http://127.0.0.1:$port"
curl_options=(--noproxy '*' --fail --silent --show-error --max-time 3)
for ((attempt=0; attempt < 60; attempt++)); do
  if curl "${curl_options[@]}" "$base_url/openapi.json" > "$scratch/api.json" 2>/dev/null; then
    break
  fi
  kill -0 "$server_pid"
  sleep 1
done
curl "${curl_options[@]}" "$base_url/desktop" > "$scratch/workspace.html"
curl "${curl_options[@]}" "$base_url/api/ui/preferences" > "$scratch/preferences.json"
curl "${curl_options[@]}" "$base_url/api/launchd/status" > "$scratch/scheduler.json"
"$python" - "$scratch" "$version" <<'PY'
import json
from pathlib import Path
import sys

scratch, version = Path(sys.argv[1]), sys.argv[2]
def read(name):
    return json.loads((scratch / name).read_text(encoding="utf-8"))

assert read("api.json")["info"]["version"] == version
assert read("preferences.json")["language"] == "zh"
scheduler = read("scheduler.json")
assert scheduler["backend"] == "desktop" and scheduler["state"] == "off", scheduler
assert 'role="tablist"' in (scratch / "workspace.html").read_text(encoding="utf-8")
assert (scratch / "app-home" / "config" / "config.json").is_file()
PY

kill "$server_pid"
stop_code=0
wait "$server_pid" || stop_code=$?
server_pid=""
[[ "$stop_code" == 0 || "$stop_code" == 143 ]]
if curl "${curl_options[@]}" "$base_url/api/status" >/dev/null 2>&1; then
  printf '%s\n' 'The installed web server continued listening after exit.' >&2
  exit 1
fi

created_legacy_home=1
env -u NEURODAILY_HOME "$entry" demo --no-open
test -d "$legacy_home/output"
printf 'Homebrew %s installed, started the localhost workspace and used the desktop data path.\n' "$version"
