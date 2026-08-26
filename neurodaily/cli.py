"""NeuroDaily CLI — standalone script mode + launchd scheduler + config editing.

Usage:
    neurodaily run [--output PATH]          # generate today's HTML report
    neurodaily serve [--port PORT]          # start the FastAPI web app
    neurodaily config show                  # print the structured prompt
    neurodaily config init [--force]        # write default config + prompt file
    neurodaily launchd install [--dry-run]  # register 08:00 launchd job
    neurodaily launchd uninstall
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

from .config import Config, DEFAULT_CONFIG, DEFAULT_DIRS


def _ensure_imports():
    """Add the package root to sys.path so `python -m neurodaily` works."""
    if __package__ in (None, ""):
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------
def cmd_run(args) -> int:
    from .digest import run, save_report
    from .config import Config as C
    cfg = C.load(args.config)
    print(f"[neurodaily] loading config: profile={cfg.profile}")
    # Explicit CLI run always executes (records history) unless --dedup is set.
    result = run(cfg, check_duplicate=True, record=True, force=not args.dedupe)
    # default filename from config
    from datetime import datetime
    fmt = cfg.output.get("filename_format", "neurodaily_%Y-%m-%d.html")
    default_name = datetime.now().strftime(fmt)
    outdir = cfg.output_dir()
    out_path = args.output or os.path.join(outdir, default_name)
    path = save_report(result, out_path)
    if result.skipped:
        print(f"[neurodaily] ⏭ skipped (duplicate) — no report overwritten. "
              f"Reason: {result.skipped_reason}")
        print(f"    use --force to re-run, or --dedupe to honor same-day de-dup")
        return 0
    print(f"[neurodaily] ✅ wrote {len(result.items)} items → {path}")
    for h in result.health:
        status = "ok" if h["ok"] else "FAILED"
        print(f"    {h['source']:<16} {status:<8} {h['count']:>3} items  {h['ms']}ms")
    if result.errors:
        print("[neurodaily] ⚠ source errors:")
        for e in result.errors:
            print(f"    - {e}")
    if cfg.output.get("open_on_finish", True) and args.no_open is False:
        try:
            subprocess.run(["open", path], check=False)
        except Exception:
            pass
    return 0


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------
def cmd_serve(args) -> int:
    import uvicorn
    from .webapp import create_app
    app = create_app()
    print(f"[neurodaily] web app → http://127.0.0.1:{args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")
    return 0


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
def cmd_config(args) -> int:
    cfg = Config.load(args.config)
    if args.config_action == "show":
        print(cfg.to_prompt())
        return 0
    if args.config_action == "init":
        target = args.config or DEFAULT_CONFIG().default_path()
        if os.path.exists(target) and not args.force:
            print(f"[neurodaily] config exists at {target}, use --force to overwrite")
            return 1
        c = DEFAULT_CONFIG()
        path = c.save(target)
        print(f"[neurodaily] wrote default config → {path}")
        print("\n--- structured prompt ---\n")
        print(c.to_prompt())
        return 0
    return 0


# ---------------------------------------------------------------------------
# launchd
# ---------------------------------------------------------------------------
def _plist_content(cfg: Config, script_path: str) -> str:
    outfile = os.path.join(cfg.output_dir(), "launchd_stdout.log")
    errfile = os.path.join(cfg.output_dir(), "launchd_stderr.log")
    os.makedirs(cfg.output_dir(), exist_ok=True)
    sched = cfg.scheduled.get("launchd", {})
    label = sched.get("label", "com.neurodaily.daily")
    hour = int(cfg.scheduled.get("hour", 8))
    minute = int(cfg.scheduled.get("minute", 0))
    # Use the CURRENT interpreter (the venv python that invoked this command),
    # not a hardcoded /usr/bin/python3 which won't have neurodaily + deps.
    python = sys.executable
    cmd = [python, "-m", "neurodaily", "run"]
    args_xml = "".join(f"<string>{_esc(a)}</string>" for a in cmd)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{_esc(label)}</string>
    <key>ProgramArguments</key>
    <array>{args_xml}</array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>{hour}</integer>
        <key>Minute</key><integer>{minute}</integer>
    </dict>
    <key>WorkingDirectory</key><string>{_esc(script_path)}</string>
    <key>StandardOutPath</key><string>{_esc(outfile)}</string>
    <key>StandardErrorPath</key><string>{_esc(errfile)}</string>
    <key>RunAtLoad</key><false/>
</dict>
</plist>
"""


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def cmd_launchd(args) -> int:
    cfg = Config.load(args.config)
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plist_path = os.path.join(pkg_root, "scripts", "com.neurodaily.daily.plist")
    sched = cfg.scheduled.get("launchd", {})
    label = sched.get("label", "com.neurodaily.daily")
    content = _plist_content(cfg, pkg_root)

    if args.launchd_action == "install":
        os.makedirs(os.path.dirname(plist_path), exist_ok=True)
        with open(plist_path, "w", encoding="utf-8") as f:
            f.write(content)
        dest = os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")
        subprocess.run(["cp", plist_path, dest], check=False)
        if args.dry_run:
            print(f"[neurodaily] DRY RUN. plist would install to {dest}")
            print(content)
            return 0
        subprocess.run(["launchctl", "unload", dest], check=False)
        r = subprocess.run(["launchctl", "load", "-w", dest], check=False)
        if r.returncode != 0:
            print(f"[neurodaily] ⚠ launchctl load returned {r.returncode}")
        print(f"[neurodaily] ✅ installed LaunchAgent {label} at {dest}")
        print(f"    runs daily at {int(cfg.scheduled.get('hour', 8)):02d}:{int(cfg.scheduled.get('minute', 0)):02d}")
        print("    verify with:  launchctl list | grep neurodaily")
        return 0
    if args.launchd_action == "uninstall":
        dest = os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")
        subprocess.run(["launchctl", "unload", dest], check=False)
        if os.path.exists(dest):
            os.remove(dest)
        print(f"[neurodaily] ✅ removed LaunchAgent {label}")
        return 0
    if args.launchd_action == "show":
        print(content)
        return 0
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def cmd_history(args) -> int:
    from . import history as hist
    runs = hist.list_runs(limit=args.limit)
    if not runs:
        print("[neurodaily] no searches recorded yet.")
        return 0
    print(f"[neurodaily] search history ({len(runs)} runs):")
    for r in runs:
        status = r["status"]
        items = r["item_count"]
        fin = (r.get("finished_at") or "")[:19].replace("T", " ")
        note = f" ({r['skipped_reason']})" if r.get("skipped_reason") else ""
        print(f"  #{r['id']:<3} {status:<10} {items:>3} items  {fin}  {note}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="neurodaily",
                                description="Daily neuroscience/psychiatry digest → HTML.")
    p.add_argument("--config", help="path to config.json (default: ~/neurodaily/config/config.json)")
    sub = p.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="generate today's HTML report")
    run_p.add_argument("--output", help="output HTML path")
    run_p.add_argument("--no-open", action="store_true", help="do not auto-open the report")
    run_p.add_argument("--dedupe", action="store_true",
                       help="skip if an identical query already ran today (dedup)")
    run_p.set_defaults(func=cmd_run)

    serve_p = sub.add_parser("serve", help="start the web app")
    serve_p.add_argument("--port", type=int, default=8031)
    serve_p.set_defaults(func=cmd_serve)

    cfg_p = sub.add_parser("config", help="view or init config")
    cfg_sub = cfg_p.add_subparsers(dest="config_action", required=True)
    cfg_sub.add_parser("show", help="print structured prompt")
    cfg_sub.add_parser("init", help="write default config file")
    cfg_p.add_argument("--force", action="store_true")
    cfg_p.set_defaults(func=cmd_config)

    ld_p = sub.add_parser("launchd", help="scheduler install/uninstall")
    ld_sub = ld_p.add_subparsers(dest="launchd_action", required=True)
    ld_sub.add_parser("install")
    ld_sub.add_parser("uninstall")
    ld_sub.add_parser("show")
    ld_p.add_argument("--dry-run", action="store_true")
    ld_p.set_defaults(func=cmd_launchd)

    hist_p = sub.add_parser("history", help="list past search runs")
    hist_p.add_argument("--limit", type=int, default=100)
    hist_p.set_defaults(func=cmd_history)

    return p


def main(argv: list[str] | None = None) -> int:
    _ensure_imports()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
