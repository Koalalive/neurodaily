"""Interactive TUI to manage the daily email recipients.

    neurodaily mail --tui          # full-screen manager
    neurodaily mail --list         # print recipients
    neurodaily mail --add a@b.com
    neurodaily mail --remove a@b.com

Reads/writes config/email.json (other keys are preserved). Falls back to a
plain printout when stdin is not a TTY.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "config", "email.json")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def load_cfg() -> dict:
    from .mailer import DEFAULT_CFG
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_cfg(cfg: dict) -> None:
    os.makedirs(os.path.dirname(CFG_PATH), exist_ok=True)
    tmp = CFG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CFG_PATH)


def valid(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip()))


def add_recipient(email: str) -> tuple[bool, str]:
    email = email.strip()
    if not valid(email):
        return False, "invalid email format"
    cfg = load_cfg()
    to = list(cfg.get("to", []))
    if email.lower() in {x.lower() for x in to}:
        return False, "already in the list"
    to.append(email)
    cfg["to"] = to
    save_cfg(cfg)
    return True, "added"


def remove_recipient(email: str) -> tuple[bool, str]:
    cfg = load_cfg()
    to = list(cfg.get("to", []))
    kept = [x for x in to if x.lower() != email.strip().lower()]
    if len(kept) == len(to):
        return False, "not found"
    cfg["to"] = kept
    save_cfg(cfg)
    return True, "removed"


def print_list() -> None:
    cfg = load_cfg()
    print(f"config : {CFG_PATH}")
    print(f"from   : {cfg.get('from')}")
    print(f"smtp   : {cfg.get('smtp_host')}:{cfg.get('smtp_port')}  "
          f"email={'ON' if cfg.get('enabled', True) else 'OFF'}")
    to = cfg.get("to", [])
    print(f"to ({len(to)}):")
    for i, e in enumerate(to, 1):
        print(f"  {i}. {e}")


# ---------------------------------------------------------------------------
# curses TUI
# ---------------------------------------------------------------------------
def _run_tui() -> None:
    import curses

    cfg = load_cfg()
    to = list(cfg.get("to", []))
    sel = 0
    dirty = False
    status = "saved"

    def draw(stdscr):
        nonlocal sel, status, dirty
        stdscr.keypad(True)
        try:
            curses.curs_set(0)
        except Exception:
            pass
        try:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)
        except Exception:
            pass
        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            if h < 8 or w < 40:
                stdscr.erase()
                stdscr.addstr(0, 0, "Terminal too small - enlarge and press any key (q to quit)")
                stdscr.refresh()
                ch = stdscr.getch()
                if ch == ord("q"):
                    return
                continue
            title = " NeuroDaily - Email Recipients "
            try:
                stdscr.addstr(0, 2, title, curses.A_BOLD | curses.color_pair(1))
            except Exception:
                stdscr.addstr(0, 2, title, curses.A_BOLD)
            info = f" From: {cfg.get('from','')}   SMTP: {cfg.get('smtp_host','')}:{cfg.get('smtp_port','')}"
            send = "ON" if cfg.get("enabled", True) else "OFF"
            stdscr.addstr(1, 2, info[: max(0, w - 3)])
            stdscr.addstr(2, 2, f" Daily email: {send}   Recipients: {len(to)}"
                                f"   max_papers={cfg.get('max_papers',40)}"
                                f" max_other={cfg.get('max_other',15)}")
            stdscr.addstr(3, 0, "-" * max(0, w - 1))

            top = 4
            bottom = max(top + 1, h - 4)
            if not to:
                stdscr.addstr(top, 2, "(no recipients yet - press 'a' to add)")
            else:
                for i, e in enumerate(to):
                    y = top + i
                    if y >= bottom:
                        break
                    marker = ">" if i == sel else " "
                    line = f" {marker} {i+1}. {e}"
                    attr = curses.A_REVERSE if i == sel else curses.A_NORMAL
                    stdscr.addstr(y, 1, line[: max(0, w - 2)], attr)

            stdscr.addstr(h - 3, 0, "-" * max(0, w - 1))
            stdscr.addstr(h - 2, 2, "a add | d delete | e edit | t toggle email | "
                                    "l limits | s save | q quit")
            stdscr.addstr(h - 1, 2, f"status: {status}"[: max(0, w - 3)])
            stdscr.refresh()

            ch = stdscr.getch()
            if ch in (ord("q"), 27):
                if dirty:
                    if not _confirm(stdscr, "Unsaved changes. Quit anyway? (y/n)"):
                        continue
                return
            elif ch in (curses.KEY_UP, ord("k")):
                sel = max(0, sel - 1)
            elif ch in (curses.KEY_DOWN, ord("j")):
                sel = min(max(0, len(to) - 1), sel + 1)
            elif ch == ord("a"):
                text = _input(stdscr, "New recipient email: ")
                if text:
                    if not valid(text):
                        status = "invalid email"
                    elif text.lower() in {x.lower() for x in to}:
                        status = "already exists"
                    else:
                        to.append(text.strip())
                        sel = len(to) - 1
                        dirty = True
                        status = "modified (press s to save)"
            elif ch == ord("d"):
                if to:
                    if _confirm(stdscr, f"Delete {to[sel]}? (y/n)"):
                        to.pop(sel)
                        sel = min(sel, max(0, len(to) - 1))
                        dirty = True
                        status = "modified (press s to save)"
            elif ch == ord("e"):
                if to:
                    text = _input(stdscr, "Edit email: ", initial=to[sel])
                    if text:
                        if not valid(text):
                            status = "invalid email"
                        else:
                            to[sel] = text.strip()
                            dirty = True
                            status = "modified (press s to save)"
            elif ch == ord("t"):
                cfg["enabled"] = not cfg.get("enabled", True)
                dirty = True
                status = "modified (press s to save)"
            elif ch == ord("l"):
                mp = _input(stdscr, "max_papers: ", initial=str(cfg.get("max_papers", 40)))
                mo = _input(stdscr, "max_other: ", initial=str(cfg.get("max_other", 15)))
                try:
                    if mp:
                        cfg["max_papers"] = max(1, int(mp))
                    if mo:
                        cfg["max_other"] = max(1, int(mo))
                    dirty = True
                    status = "modified (press s to save)"
                except ValueError:
                    status = "numbers only"
            elif ch == ord("s"):
                cfg["to"] = to
                save_cfg(cfg)
                dirty = False
                status = f"saved to {os.path.basename(CFG_PATH)}"

    curses.wrapper(draw)


def _input(stdscr, prompt: str, initial: str = "") -> str:
    import curses
    h, w = stdscr.getmaxyx()
    buf = list(initial)
    try:
        curses.curs_set(1)
    except Exception:
        pass
    while True:
        stdscr.move(h - 1, 0)
        stdscr.clrtoeol()
        line = prompt + "".join(buf)
        stdscr.addstr(h - 1, 1, line[: max(0, w - 3)])
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (10, 13):
            try:
                curses.curs_set(0)
            except Exception:
                pass
            return "".join(buf).strip()
        if ch == 27:
            try:
                curses.curs_set(0)
            except Exception:
                pass
            return ""
        if ch in (curses.KEY_BACKSPACE, 127, 8):
            if buf:
                buf.pop()
        elif 32 <= ch < 127:
            buf.append(chr(ch))


def _confirm(stdscr, msg: str) -> bool:
    import curses
    h, w = stdscr.getmaxyx()
    stdscr.move(h - 1, 0)
    stdscr.clrtoeol()
    stdscr.addstr(h - 1, 1, msg[: max(0, w - 3)])
    stdscr.refresh()
    while True:
        ch = stdscr.getch()
        if ch in (ord("y"), ord("Y")):
            return True
        if ch in (ord("n"), ord("N"), 27):
            return False


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="neurodaily mail")
    p.add_argument("--tui", action="store_true")
    p.add_argument("--list", action="store_true")
    p.add_argument("--add", metavar="EMAIL")
    p.add_argument("--remove", metavar="EMAIL")
    args, _ = p.parse_known_args(argv)

    if args.add:
        ok, msg = add_recipient(args.add)
        print(f"[{'ok' if ok else 'fail'}] {msg}: {args.add}")
        return 0 if ok else 1
    if args.remove:
        ok, msg = remove_recipient(args.remove)
        print(f"[{'ok' if ok else 'fail'}] {msg}: {args.remove}")
        return 0 if ok else 1
    if args.list:
        print_list()
        return 0
    if args.tui or sys.stdin.isatty():
        if not sys.stdin.isatty():
            print_list()
            print("\n(stdin is not a TTY; use --list/--add/--remove)")
            return 0
        _run_tui()
        return 0
    print_list()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
