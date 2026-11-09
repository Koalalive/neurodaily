"""Run deep-dive expansion until done, then regenerate the report and push.

Resumable and idempotent: already-cached entries are skipped, so re-running this
after an interruption continues where it left off.

    nohup .venv/bin/python -u scripts/deepen_until_done.py > /tmp/deepen_until_done.log 2>&1 &

It reads the SJTU gateway key from the local opencode config (never printed).
Environment: CONCURRENCY (default 3), MODEL (default deepseek-chat), MAX_ROUNDS.
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from neurodaily.deepen import expand_llm, load_cache, targets  # noqa: E402

CFG_PATH = os.path.expanduser("~/.config/opencode/opencode.json")
_cfg = json.load(open(CFG_PATH, encoding="utf-8"))
_sjtu = _cfg["provider"]["sjtu"]["options"]
BASE_URL = _sjtu["baseURL"]
API_KEY = _sjtu["apiKey"]
MODEL = os.environ.get("MODEL", "deepseek-chat")
CONCURRENCY = int(os.environ.get("CONCURRENCY", "3"))
MAX_ROUNDS = int(os.environ.get("MAX_ROUNDS", "80"))


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run(cmd, env=None):
    log("$ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=False, env=env)


def main() -> int:
    log(f"start: remaining={len(targets())} concurrency={CONCURRENCY} model={MODEL}")
    stalls = 0
    for rnd in range(1, MAX_ROUNDS + 1):
        rem = len(targets())
        if rem == 0:
            break
        before = len(load_cache())
        log(f"round {rnd}: remaining={rem}")
        try:
            expand_llm(limit=None, model=MODEL, base_url=BASE_URL, api_key=API_KEY,
                       concurrency=CONCURRENCY)
        except SystemExit as exc:
            log(f"expand_llm aborted: {exc}")
            break
        after = len(load_cache())
        log(f"round {rnd}: +{after - before} (cache {after})")
        if after == before:
            stalls += 1
            if stalls >= 3:
                log("no progress across 3 rounds; stopping")
                break
            time.sleep(60)
        else:
            stalls = 0
            time.sleep(5)

    rem = len(targets())
    cached = len(load_cache())
    log(f"expansion finished: cached={cached} remaining={rem}")

    log("regenerating report ...")
    run([sys.executable, "-m", "neurodaily", "run", "--no-open"])

    run(["git", "add", "neurodaily/data/onthisday_deep.json", "neurodaily/deepen.py",
         "scripts/deepen_until_done.py"])
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if staged.returncode == 0:
        log("nothing new to commit")
    else:
        run(["git", "commit", "-m",
             f"chore(on-this-day): auto-generate deep dives ({cached} cached)"])
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        run(["git", "push", "origin", "main"], env=env)

    log(f"DONE cached={cached} remaining={rem}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
