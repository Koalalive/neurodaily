"""Cross-platform, dependency-free notification helpers for NeuroDaily.

Used to "push" the morning digest / on-this-day item to the user:
- macOS: ``osascript display notification`` (also tries ``terminal-notifier``)
- Linux: ``notify-send``
- Anything else: silently no-ops (the report is still generated).

All failures are swallowed — a failed notification must never break a run.
"""
from __future__ import annotations

import shutil
import subprocess
import sys


def _apple_escape(s: str) -> str:
    # Escape for AppleScript double-quoted string literals.
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _macos(title: str, message: str, subtitle: str = "") -> bool:
    if shutil.which("terminal-notifier"):
        cmd = ["terminal-notifier", "-title", title, "-message", message]
        if subtitle:
            cmd += ["-subtitle", subtitle]
        try:
            subprocess.run(cmd, check=False, timeout=10)
            return True
        except Exception:
            pass
    script = f'display notification "{_apple_escape(message)}" with title "{_apple_escape(title)}"'
    if subtitle:
        script += f' subtitle "{_apple_escape(subtitle)}"'
    script += ' sound name "Glass"'
    try:
        subprocess.run(["osascript", "-e", script], check=False, timeout=10)
        return True
    except Exception:
        return False


def _linux(title: str, message: str) -> bool:
    if not shutil.which("notify-send"):
        return False
    try:
        subprocess.run(["notify-send", title, message], check=False, timeout=10)
        return True
    except Exception:
        return False


def notify(title: str, message: str, subtitle: str = "") -> bool:
    """Best-effort desktop notification. Returns True if a notifier ran."""
    try:
        if sys.platform == "darwin":
            return _macos(title, message, subtitle)
        if sys.platform.startswith("linux"):
            return _linux(title, message)
    except Exception:
        pass
    return False


def notify_on_this_day(events: list[dict], date_label: str = "") -> bool:
    """Push a short 'on this day' banner. `events` come from onthisday.today_events()."""
    if not events:
        return notify("NeuroDaily · 历史上的今天", "今天没有收录的神经科学史条目。", date_label)
    lines = []
    for e in events[:3]:
        cat = e.get("category_label", "")
        lines.append(f"{e.get('year')} · {e.get('title')}" + (f"（{cat}）" if cat else ""))
    msg = "\n".join(lines)
    return notify("NeuroDaily · 历史上的今天", msg, date_label)
