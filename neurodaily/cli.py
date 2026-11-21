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
    if getattr(args, "lang", None):
        cfg.scheduled.setdefault("on_this_day", {})["lang"] = args.lang
    if not getattr(args, "demo", False) and os.environ.get("NEURODAILY_NO_METRICS") != "1":
        try:
            from .journal_metrics import ensure_fresh
            _mr = ensure_fresh([j.name for j in cfg.journals])
            if _mr:
                print(f"[neurodaily] journal metrics refreshed: {_mr}")
        except Exception as e:
            print(f"[neurodaily] ⚠ metrics skipped: {e}")
    if getattr(args, "demo", False):
        from .demo import build_result
        print("[neurodaily] demo mode: offline sample data (no network)")
        result = build_result(cfg)
    else:
        _mode = getattr(args, "mode", "auto")
        if _mode == "auto":
            _mode = os.environ.get("NEURODAILY_MODE", "manual")
        result = run(cfg, check_duplicate=True, record=True, force=not args.dedupe,
                     mode=_mode)
        try:
            from . import ai_summary as _ai
            _txt = _ai.generate(result)
            if _txt:
                result.ai_summary = _txt
                result.ai_summary_meta = {"model": _ai.load_cfg().get("model", "")}
                print("[neurodaily] 🧠 AI summary generated")
        except Exception as e:
            print(f"[neurodaily] ⚠ AI summary skipped: {e}")
    # default filename from config
    from datetime import datetime
    fmt = cfg.output.get("filename_format") or "neurodaily_%Y-%m-%d.html"
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
        status = h.get("status", "ok" if h["ok"] else "failed")
        print(f"    {h['source']:<16} {status:<8} {h['count']:>3} items  {h['ms']}ms")
    if result.errors:
        print("[neurodaily] ⚠ source errors:")
        for e in result.errors:
            print(f"    - {e}")
    if not getattr(args, "demo", False):
        try:
            from .delivery import deliver_report
            outcomes = deliver_report(result, path)
            if outcomes:
                print(f"[neurodaily] delivery: {outcomes}")
        except Exception as e:
            print(f"[neurodaily] ⚠ delivery failed: {e}")
    try:
        from .onthisday import should_notify as _should_notify, is_enabled as _otd_enabled, day_label
        from .notify import notify_on_this_day
        if _otd_enabled(cfg) and _should_notify(cfg) and result.on_this_day:
            evs = result.on_this_day
            notify_on_this_day(evs, day_label(evs))
    except Exception:
        pass
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
    import os
    import uvicorn
    from .webapp import create_app
    if getattr(args, "demo", False):
        os.environ["NEURODAILY_DEMO"] = "1"
    app = create_app(args.config)
    host = getattr(args, "host", "127.0.0.1")
    base_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    try:
        app.state.base_url = f"http://{base_host}:{args.port}"
    except Exception:
        pass
    print(f"[neurodaily] web app → http://{host}:{args.port}")
    if getattr(args, "open", False):
        import threading, webbrowser
        threading.Timer(2.0, lambda: webbrowser.open(f"http://{host}:{args.port}/settings")).start()
    uvicorn.run(app, host=host, port=args.port, log_level="info")
    return 0


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
def cmd_config(args) -> int:
    cfg = Config.load(args.config)
    if args.config_action == "show":
        print(cfg.to_prompt())
        return 0
    if args.config_action == "schema":
        import json as _json
        from .config_ops import schema_json
        js = _json.dumps(schema_json(), ensure_ascii=False, indent=2)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(js)
            print(f"[neurodaily] wrote JSON Schema → {args.out}")
        else:
            print(js)
        return 0
    if args.config_action == "describe":
        import json as _json
        from .config_ops import describe
        print(_json.dumps(describe(), ensure_ascii=False, indent=2))
        return 0
    if args.config_action == "apply":
        import json as _json
        from .config_ops import apply_patch
        path = args.config or Config.default_path()
        try:
            with open(args.patch, encoding="utf-8") as f:
                patch = _json.load(f)
        except Exception as e:
            print(f"[neurodaily] ✖ cannot read patch: {e}")
            return 1
        ok, errs, diff = apply_patch(path, patch, dry_run=args.dry_run)
        if diff:
            print(diff)
        if not ok:
            print(f"[neurodaily] ✖ patch rejected ({len(errs)} error(s)):")
            for e in errs:
                print("   -", e)
            return 1
        if args.dry_run:
            print("[neurodaily] ✔ dry-run OK (nothing written)")
        else:
            print(f"[neurodaily] ✔ applied → {path}")
        return 0
    if args.config_action == "validate":
        from .schema import validate_file
        target = args.config or Config.default_path()
        errs = validate_file(target)
        if errs:
            print(f"[neurodaily] ✖ config invalid ({len(errs)} error(s)): {target}")
            for e in errs:
                print("   -", e)
            return 1
        print(f"[neurodaily] ✔ config OK: {target}")
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
    cmd = [python, "-m", "neurodaily", "run", "--mode", "daily"]
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
def cmd_deepen(args) -> int:
    from . import deepen
    if args.status:
        import json
        print(json.dumps(deepen.status(), ensure_ascii=False, indent=2))
        return 0
    if args.backend == "template":
        deepen.expand_template(limit=args.limit)
    else:
        deepen.expand_llm(limit=args.limit, model=args.model, base_url=args.base_url,
                          api_key=args.api_key, concurrency=args.concurrency)
    return 0


def cmd_mail(args) -> int:
    from . import mail_tui
    if args.tui or args.list_recipients or args.add or args.remove:
        argv = []
        if args.tui:
            argv.append("--tui")
        if args.list_recipients:
            argv.append("--list")
        if args.add:
            argv += ["--add", args.add]
        if args.remove:
            argv += ["--remove", args.remove]
        return mail_tui.main(argv)
    from .mailer import load_last, render_email, save_last, send_digest, send_test, send_with_retry
    if getattr(args, "send_latest", False):
        last = load_last()
        if not last:
            print("[neurodaily] no cached email yet; run 'mail --send' first")
            return 1
        att = last.get("attachment") or ""
        atts = [att] if att and os.path.exists(att) else None
        send_with_retry(last["subject"], last["html"], last["text"], attachments=atts)
        print(f"[neurodaily] 📧 resent: {last['subject']}")
        return 0
    if args.test:
        send_test()
        print("[neurodaily] 📧 test email sent")
        return 0
    from .config import Config
    from .digest import run as run_digest
    cfg = Config.load(args.config)
    print("[neurodaily] running digest to build the email ...")
    result = run_digest(cfg, check_duplicate=False, record=False, force=True)
    subject, html, text = render_email(result)
    if args.preview:
        with open(args.preview, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[neurodaily] preview written → {args.preview} ({len(html)} bytes)")
    if args.send:
        from .digest import save_report
        from datetime import datetime
        fmt = cfg.output.get("filename_format") or "neurodaily_%Y-%m-%d.html"
        report_path = os.path.join(cfg.output_dir(), datetime.now().strftime(fmt))
        save_report(result, report_path)
        from .mailer import load_cfg as _mail_cfg
        atts = [report_path] if _mail_cfg().get("attach_report", True) else None
        send_with_retry(subject, html, text, attachments=atts)
        save_last(subject, html, text, report_path if atts else None)
        print(f"[neurodaily] 📧 sent: {subject}")
    if not args.preview and not args.send and not args.test:
        print("[neurodaily] nothing to do: use --test, --preview PATH, or --send")
    return 0


def cmd_ai_summary(args) -> int:
    from datetime import datetime
    from . import ai_summary
    from .config import Config as C
    from .demo import build_result
    from .digest import run as run_digest, save_report
    cfg = C.load(args.config)
    result = build_result(cfg) if getattr(args, "demo", False) else run_digest(
        cfg, check_duplicate=False, record=False, force=True)
    txt = ai_summary.generate(result, force=getattr(args, "force", False),
                              api_key_override=args.api_key,
                              base_url=args.base_url, model=args.model)
    if not txt:
        print("[neurodaily] AI summary disabled or empty")
        return 1
    if getattr(args, "save", False):
        result.ai_summary = txt
        result.ai_summary_meta = {"model": args.model or ai_summary.load_cfg().get("model", "")}
        fmt = cfg.output.get("filename_format") or "neurodaily_%Y-%m-%d.html"
        out = os.path.join(cfg.output_dir(), datetime.now().strftime(fmt))
        save_report(result, out)
        print(f"[neurodaily] report with AI summary → {out}")
    print(txt)
    return 0


def cmd_metrics(args) -> int:
    import json as _json
    from . import journal_metrics as jm
    act = args.action
    if act == "refresh":
        print(_json.dumps(jm.refresh(args.journal or None, force=args.force),
                          ensure_ascii=False))
        return 0
    if act == "import":
        print(_json.dumps(jm.import_csv(args.path), ensure_ascii=False))
        return 0
    if act == "status":
        print(_json.dumps(jm.status(), ensure_ascii=False, indent=2))
        return 0
    if act == "show":
        from .config import Config as C
        cfg = C.load(args.config)
        for j in cfg.journals:
            print(f"{j.name}: {jm.lookup(j.name)}")
        return 0
    return 0


def cmd_export(args) -> int:
    from datetime import datetime
    from .config import Config as C
    from .demo import build_result
    from .digest import run as run_digest
    from .exporters import write_bibtex, write_json
    cfg = C.load(args.config)
    result = build_result(cfg) if getattr(args, "demo", False) else run_digest(
        cfg, check_duplicate=False, record=False, force=True)
    outdir = cfg.output_dir()
    os.makedirs(outdir, exist_ok=True)
    stem = os.path.join(outdir, "neurodaily_" + datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    paths = []
    if args.format in ("json", "both"):
        paths.append(write_json(result, stem + ".json"))
    if args.format in ("bibtex", "both"):
        paths.append(write_bibtex(result, stem + ".bib"))
    for pth in paths:
        print(f"[neurodaily] wrote {pth}")
    return 0


def cmd_webhook(args) -> int:
    from .webhooks import send_all, send_test
    if args.test:
        print("[neurodaily] webhook:", send_test())
        return 0
    from .config import Config as C
    from .demo import build_result
    from .digest import run as run_digest
    cfg = C.load(args.config)
    result = build_result(cfg) if getattr(args, "demo", False) else run_digest(
        cfg, check_duplicate=False, record=False, force=True)
    print("[neurodaily] webhook:", send_all(result))
    return 0


def cmd_demo(args) -> int:
    args.demo = True
    args.dedupe = False
    args.output = None
    args.no_open = getattr(args, "no_open", False)
    return cmd_run(args)


def cmd_profile(args) -> int:
    import json as _json
    from .config_ops import list_profiles, new_profile, profile_path
    act = args.profile_action
    if act == "list":
        names = list_profiles()
        print("\n".join(names) if names else "(no profiles yet)")
        return 0
    if act == "new":
        try:
            path = new_profile(args.name, args.from_path)
        except FileExistsError:
            print(f"[neurodaily] profile already exists: {args.name}", file=sys.stderr)
            return 1
        print(f"[neurodaily] created profile → {path}")
        return 0
    if act == "path":
        print(profile_path(args.name))
        return 0
    if act == "show":
        path = profile_path(args.name)
        try:
            with open(path, encoding="utf-8") as f:
                print(_json.dumps(_json.load(f), ensure_ascii=False, indent=2))
        except FileNotFoundError:
            print(f"[neurodaily] profile not found: {args.name}")
            return 1
        return 0
    return 0


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


def cmd_search_quality(args) -> int:
    import json
    from pathlib import Path

    from .search_quality import evaluate_corpus, load_corpus

    def config(path):
        if path is None:
            return None
        if not Path(path).is_file():
            raise ValueError(f"config not found: {path}")
        return Config.load(path)

    try:
        result = evaluate_corpus(load_corpus(args.corpus), config(args.config),
                                 baseline=config(args.baseline), top=args.top)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(f"[neurodaily] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
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
    run_p.add_argument("--demo", action="store_true", help="offline demo data (no network)")
    run_p.add_argument("--mode", choices=["auto", "daily", "manual"], default="auto",
                       help="time window: daily / manual (default: auto)")
    run_p.add_argument("--lang", choices=["zh", "en", "ru"], default=None,
                       help="on-this-day language (default: from config)")
    run_p.set_defaults(func=cmd_run)

    serve_p = sub.add_parser("serve", help="start the web app")
    serve_p.add_argument("--port", type=int, default=8031)
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--demo", action="store_true", help="dashboard uses offline demo data")
    serve_p.add_argument("--open", action="store_true", help="open the settings page in a browser")
    serve_p.set_defaults(func=cmd_serve)

    cfg_p = sub.add_parser("config", help="view or init config")
    cfg_sub = cfg_p.add_subparsers(dest="config_action", required=True)
    cfg_sub.add_parser("show", help="print structured prompt")
    cfg_sub.add_parser("init", help="write default config file")
    cfg_sub.add_parser("validate", help="validate config.json against the schema")
    cfg_sub.add_parser("schema", help="print the JSON Schema").add_argument("--out")
    cfg_sub.add_parser("describe", help="print an agent-readable capability map")
    apply_p = cfg_sub.add_parser("apply", help="merge a JSON patch into the config")
    apply_p.add_argument("patch")
    apply_p.add_argument("--dry-run", action="store_true")
    cfg_p.add_argument("--force", action="store_true")
    cfg_p.set_defaults(func=cmd_config)

    ld_p = sub.add_parser("launchd", help="scheduler install/uninstall")
    ld_sub = ld_p.add_subparsers(dest="launchd_action", required=True)
    ld_sub.add_parser("install")
    ld_sub.add_parser("uninstall")
    ld_sub.add_parser("show")
    ld_p.add_argument("--dry-run", action="store_true")
    ld_p.set_defaults(func=cmd_launchd)

    deepen_p = sub.add_parser("deepen", help="bulk-generate long-form on-this-day bodies")
    deepen_p.add_argument("--status", action="store_true")
    deepen_p.add_argument("--backend", choices=["llm", "template"], default="llm")
    deepen_p.add_argument("--limit", type=int, default=None)
    deepen_p.add_argument("--model", default=None)
    deepen_p.add_argument("--base-url", default=None)
    deepen_p.add_argument("--api-key", default=None)
    deepen_p.add_argument("--concurrency", type=int, default=4)
    deepen_p.set_defaults(func=cmd_deepen)

    met_p = sub.add_parser("metrics", help="journal metrics (OpenAlex auto + official import)")
    met_sub = met_p.add_subparsers(dest="action", required=True)
    met_r = met_sub.add_parser("refresh")
    met_r.add_argument("--force", action="store_true")
    met_r.add_argument("--journal", action="append")
    met_i = met_sub.add_parser("import")
    met_i.add_argument("path")
    met_sub.add_parser("status")
    met_sub.add_parser("show")
    met_p.set_defaults(func=cmd_metrics)

    ai_p = sub.add_parser("ai-summary", help="generate the AI daily overview")
    ai_p.add_argument("--demo", action="store_true")
    ai_p.add_argument("--force", action="store_true")
    ai_p.add_argument("--save", action="store_true", help="also write a report embedding it")
    ai_p.add_argument("--api-key", default=None)
    ai_p.add_argument("--base-url", default=None)
    ai_p.add_argument("--model", default=None)
    ai_p.set_defaults(func=cmd_ai_summary)

    export_p = sub.add_parser("export", help="export the digest as JSON / BibTeX")
    export_p.add_argument("--format", choices=["json", "bibtex", "both"], default="both")
    export_p.add_argument("--demo", action="store_true")
    export_p.set_defaults(func=cmd_export)

    demo_p = sub.add_parser("demo", help="generate an offline demo report")
    demo_p.add_argument("--no-open", action="store_true")
    demo_p.set_defaults(func=cmd_demo)

    hook_p = sub.add_parser("webhook", help="push to Feishu / WeCom")
    hook_p.add_argument("--test", action="store_true")
    hook_p.add_argument("--demo", action="store_true")
    hook_p.set_defaults(func=cmd_webhook)

    prof_p = sub.add_parser("profile", help="manage config profiles")
    prof_sub = prof_p.add_subparsers(dest="profile_action", required=True)
    prof_sub.add_parser("list")
    new_p = prof_sub.add_parser("new")
    new_p.add_argument("name")
    new_p.add_argument("--from", dest="from_path", default=None)
    for act in ("path", "show"):
        sp = prof_sub.add_parser(act)
        sp.add_argument("name")
    prof_p.set_defaults(func=cmd_profile)

    mail_p = sub.add_parser("mail", help="send / preview today's digest as email")
    mail_p.add_argument("--test", action="store_true", help="send a tiny test email")
    mail_p.add_argument("--preview", metavar="PATH", help="write the email HTML to PATH")
    mail_p.add_argument("--send", action="store_true", help="send today's digest")
    mail_p.add_argument("--send-latest", dest="send_latest", action="store_true",
                        help="resend the last rendered email (no new digest run)")
    mail_p.add_argument("--tui", action="store_true", help="interactive recipients manager")
    mail_p.add_argument("--list", dest="list_recipients", action="store_true",
                        help="print current recipients")
    mail_p.add_argument("--add", metavar="EMAIL", help="add a recipient")
    mail_p.add_argument("--remove", metavar="EMAIL", help="remove a recipient")
    mail_p.set_defaults(func=cmd_mail)

    hist_p = sub.add_parser("history", help="list past search runs")
    hist_p.add_argument("--limit", type=int, default=100)
    hist_p.set_defaults(func=cmd_history)

    quality_p = sub.add_parser("search-quality", help="evaluate retrieval rules on a frozen paper corpus")
    quality_p.add_argument("--corpus", help="path to a labelled corpus JSON (default: bundled synthetic sample)")
    quality_p.add_argument("--baseline", help="path to a baseline config JSON for comparison")
    quality_p.add_argument("--top", type=int, default=20, help="size of the ranking cutoff (default: 20)")
    quality_p.set_defaults(func=cmd_search_quality)

    return p


def main(argv: list[str] | None = None) -> int:
    _ensure_imports()
    argv = list(sys.argv[1:] if argv is None else argv)
    profile = None
    if "--profile" in argv:
        i = argv.index("--profile")
        if i + 1 < len(argv):
            profile = argv[i + 1]
            del argv[i:i + 2]
    parser = build_parser()
    args = parser.parse_args(argv)
    if profile:
        from .config_ops import profile_path
        args.config = profile_path(profile)
        if not os.path.isfile(args.config):
            parser.error(f"profile not found: {profile}")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
