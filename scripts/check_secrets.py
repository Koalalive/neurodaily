#!/usr/bin/env python3
"""Fail on likely API keys without printing the secret value."""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

PATTERNS = [
    re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?i)(?:DEEPSEEK|OPENAI|ANTHROPIC|NEURODAILY_LLM)_API_KEY\s*[=:]\s*[^\s\"']{8,}"),
]
SKIP = {".git", ".venv", "node_modules", "target", "output", "dist", "build"}


def staged_files() -> list[Path]:
    raw = subprocess.check_output(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                                  text=True)
    return [Path(line) for line in raw.splitlines() if line.strip()]


def tracked_files() -> list[Path]:
    raw = subprocess.check_output(["git", "ls-files"], text=True)
    return [Path(line) for line in raw.splitlines() if line.strip()]


def check(paths: list[Path]) -> list[str]:
    hits = []
    for path in paths:
        if not path.is_file() or any(part in SKIP for part in path.parts):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        for number, line in enumerate(data.splitlines(), 1):
            if any(pattern.search(line) for pattern in PATTERNS):
                hits.append(f"{path}:{number}")
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", action="store_true", help="scan only staged files")
    args = parser.parse_args()
    hits = check(staged_files() if args.staged else tracked_files())
    if hits:
        print("Potential secret detected in: " + ", ".join(hits))
        print("Remove and rotate the credential; do not print its value.")
        return 1
    print("No high-confidence secret patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
