"""FastAPI web app for NeuroDaily.

Routes:
    GET  /            -> dashboard: run + view latest report inline
    GET  /run         -> one-range "run now" page (does not write config)
    POST /api/run     -> run now (background; ?force=1, ?hours=N overrides this run only)
    GET  /api/status  -> recent runs / health
    GET  /api/prompt  -> structured focus prompt JSON + text
    GET  /reports     -> list generated HTML reports
    GET  /reports/{file} -> serve a report
    GET  /history     -> list all past search runs (web page)
    GET  /history/{run_id} -> view a past run (saved report or summary page)
    GET  /api/history -> JSON list of past runs
"""
from __future__ import annotations

import logging
import os
import subprocess
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from threading import Event, Lock, Thread

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import Config, DEFAULT_CONFIG
from .desktop_schedule import run_schedule, scheduled_time
from .digest import run as run_digest, render_html_for
from .presets import research_presets
from .settings_page import SETTINGS_HTML, DASHBOARD_SETTINGS_LINK
from .run_page import RUN_HTML
from . import __version__, history as hist


def _cfg_with_hours(cfg: Config, hours: int) -> Config:
    import copy
    import math
    c = copy.deepcopy(cfg)
    w = dict(c.windows or {})
    for key in ("daily_paper_hours", "manual_paper_hours", "trials_hours",
                "funding_hours", "news_hours"):
        w[key] = hours
    w["other_lookback_days"] = max(1, math.ceil(hours / 24))
    c.windows = w
    return c


def create_app(config_path: str | None = None, *, desktop: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        stop = Event()
        if desktop:
            Thread(target=run_schedule, args=(stop, lambda: Config.load(config_path),
                                                _start_scheduled_search),
                   name="neurodaily-schedule", daemon=True).start()
        try:
            yield
        finally:
            stop.set()

    app = FastAPI(title="NeuroDaily", version=__version__, lifespan=lifespan)
    app.state.last_run = None
    app.state.search_attempt = None
    search_lock = Lock()

    def _cfg() -> Config:
        try:
            return Config.load(config_path)
        except Exception:
            return DEFAULT_CONFIG()

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request=None):
        cfg = _cfg()
        result = app.state.last_run
        # render using last run if available, else show an empty-but-styled page
        if result is None:
            if os.environ.get("NEURODAILY_DEMO"):
                from .demo import build_result
                result = build_result(cfg)
            else:
                from .digest import DigestResult
                result = DigestResult(items=[], sections={"papers": [], "industry": [],
                                                         "trials_conferences": [], "policy": []},
                                      health=[], generated_at=datetime.now().isoformat(),
                                      config_profile=cfg.profile, config=cfg)
        html = render_html_for(result)
        return html.replace("</body>", DASHBOARD_SETTINGS_LINK + "</body>", 1)

    @app.get("/run", response_class=HTMLResponse)
    def run_now_page():
        return RUN_HTML

    def _begin_search():
        started_at = datetime.now().isoformat()
        attempt = {"started_at": started_at, "status": "running"}
        with search_lock:
            current = app.state.search_attempt
            if current and current["status"] == "running":
                return None
            app.state.search_attempt = attempt
        return attempt

    def _search_and_deliver(cfg: Config, attempt: dict, force: bool, mode: str):
        try:
            from .journal_metrics import ensure_fresh
            ensure_fresh([j.name for j in cfg.journals])
        except Exception:
            pass
        result = run_digest(cfg, check_duplicate=True, record=True, force=force,
                            mode=mode)
        if result.skipped:
            attempt.update(status="skipped", error=result.skipped_reason)
            return
        try:
            from .ai_summary import generate as _ai_gen, load_cfg as _ai_cfg
            _txt = _ai_gen(result)
            if _txt:
                result.ai_summary = _txt
                result.ai_summary_meta = {"model": _ai_cfg().get("model", "")}
        except Exception:
            pass
        from .digest import save_report
        fmt = cfg.output.get("filename_format") or "neurodaily_%Y-%m-%d_%H%M%S.html"
        path = os.path.join(cfg.output_dir(), datetime.now().strftime(fmt))
        save_report(result, path)
        base = getattr(app.state, "base_url", "") or "http://127.0.0.1:8031"
        try:
            with open(path, encoding="utf-8") as _f:
                _html = _f.read()
            _html = _html.replace('<meta name="nd-base" content="">',
                                  f'<meta name="nd-base" content="{base}">')
            with open(path, "w", encoding="utf-8") as _f:
                _f.write(_html)
        except Exception:
            pass
        app.state.last_report_path = path
        app.state.last_run = result
        try:
            from .mailer import (_password, load_cfg as _mail_cfg,
                                 render_email, save_last, send_with_retry)
            _mc = _mail_cfg()
            _atts = [path] if _mc.get("attach_report", True) else None
            _subj, _html, _text = render_email(result, _mc)
            save_last(_subj, _html, _text, path if _atts else None)
            if _mc.get("enabled", True) and _password(_mc):
                send_with_retry(_subj, _html, _text, _mc, _atts)
        except Exception:
            pass
        try:
            from .webhooks import send_all as _hooks
            _hooks(result)
        except Exception:
            pass
        try:
            if cfg.output.get("open_on_finish", True) and os.environ.get("NEURODAILY_NO_OPEN") != "1":
                import subprocess
                import sys
                url = base.rstrip("/") + "/report/latest"
                print("[neurodaily] opening report:", url, flush=True)
                if sys.platform == "darwin":
                    subprocess.run(["open", url], check=False)
                else:
                    import webbrowser
                    webbrowser.open(url)
                print("[neurodaily] opened report:", url, flush=True)
        except Exception:
            pass
        attempt.update(status="completed", item_count=len(result.items))

    def _execute_search(cfg: Config, attempt: dict, force: bool = False,
                        mode: str = "manual", scheduled_day: str | None = None):
        try:
            if scheduled_day is not None and not hist.claim_desktop_schedule(scheduled_day):
                attempt.update(status="skipped", error="Today's desktop schedule already ran.")
                return
            _search_and_deliver(cfg, attempt, force, mode)
        except Exception:
            logging.getLogger(__name__).exception("Search or report generation failed")
            attempt.update(status="failed", error="Report generation failed. See the server log.")

    def _start_scheduled_search(cfg: Config, day: date) -> bool:
        attempt = _begin_search()
        if attempt is None:
            return False
        _execute_search(cfg, attempt, mode="daily", scheduled_day=day.isoformat())
        return True

    @app.post("/api/run")
    def api_run(background_tasks: BackgroundTasks, force: bool = False,
                hours: int | None = None):
        cfg = _cfg()
        if hours is not None and not (1 <= hours <= 8760):
            return JSONResponse({"error": "hours must be 1..8760"}, status_code=400)
        cfg = _cfg_with_hours(cfg, hours) if hours else cfg
        attempt = _begin_search()
        if attempt is None:
            return JSONResponse({"error": "A search is already running"}, status_code=409)

        background_tasks.add_task(_execute_search, cfg, attempt, force)
        return JSONResponse({"status": "started", "profile": cfg.profile,
                             "force": force, "started_at": attempt["started_at"]})

    @app.get("/api/status")
    def api_status():
        cfg = _cfg()
        lr = app.state.last_run
        return {
            "profile": cfg.profile,
            "last_run": (lr.generated_at if lr else None),
            "item_count": (len(lr.items) if lr else 0),
            "sections": (lr.section_counts() if lr else {}),
            "health": (lr.health if lr else ["not run yet"]),
            "prompt": cfg.to_prompt(),
            "search": app.state.search_attempt,
        }

    @app.get("/api/prompt")
    def api_prompt():
        cfg = _cfg()
        return JSONResponse({"profile": cfg.profile, "prompt": cfg.to_prompt()})

    @app.get("/reports")
    def reports():
        cfg = _cfg()
        outdir = cfg.output_dir()
        files = []
        if os.path.isdir(outdir):
            for f in sorted(os.listdir(outdir), reverse=True):
                if f.endswith(".html"):
                    files.append(f)
        return JSONResponse({"reports": files, "dir": outdir})

    @app.get("/reports/{filename}")
    def report_file(filename: str):
        cfg = _cfg()
        # sanitize
        base = os.path.basename(filename)
        path = os.path.join(cfg.output_dir(), base)
        if not os.path.exists(path):
            return HTMLResponse("<h3>report not found</h3>", status_code=404)
        return FileResponse(path, media_type="text/html")

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page():
        return SETTINGS_HTML

    @app.get("/api/config")
    def api_config_get():
        return JSONResponse(_cfg().to_dict())

    @app.get("/api/config/presets")
    def api_config_presets():
        return research_presets()

    @app.post("/api/config")
    async def api_config_post(request: Request):
        try:
            data = await request.json()
        except Exception as e:
            return JSONResponse({"ok": False, "error": f"invalid json: {e}"}, status_code=400)
        if not isinstance(data, dict) or not data.get("disciplines"):
            return JSONResponse({"ok": False, "error": "disciplines 不能为空",
                                 "errors": ["disciplines: 至少需要一个学科"]}, status_code=400)
        from .schema import validate as _validate_cfg
        errs = _validate_cfg(data)
        if errs:
            return JSONResponse({"ok": False, "error": "; ".join(errs[:4]),
                                 "errors": errs}, status_code=400)
        try:
            cfg = Config.from_dict(data)
            path = cfg.save(config_path) if config_path else cfg.save()
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        return JSONResponse({"ok": True, "path": path})

    @app.post("/api/config/reset")
    def api_config_reset():
        try:
            path = DEFAULT_CONFIG().save(config_path) if config_path else DEFAULT_CONFIG().save()
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        return JSONResponse({"ok": True, "path": path})

    def _launchd_label() -> str:
        cfg = _cfg()
        sched = cfg.scheduled or {}
        return ((sched.get("launchd") or {}).get("label")) or "com.neurodaily.daily"

    @app.get("/api/push")
    def api_push_get():
        from .mailer import load_cfg as _mail_cfg, _password as _mail_pw
        from .webhooks import load_cfg as _hook_cfg
        e, w = _mail_cfg(), _hook_cfg()
        keys = ("enabled", "to", "smtp_host", "smtp_port", "use_ssl", "username",
                "from", "from_name", "subject_template", "attach_report",
                "attach_max_mb", "summary_papers", "summary_chars")
        return JSONResponse({
            "email": {k: e.get(k) for k in keys},
            "webhooks": {"feishu": w.get("feishu", ""), "wecom": w.get("wecom", ""),
                         "max_items": w.get("max_items", 8)},
            "password_set": bool(_mail_pw(e)),
        })

    @app.post("/api/push")
    async def api_push_post(request: Request):
        import json as _json
        from .mailer import CFG_PATH as EMAIL_PATH, load_cfg as _mail_cfg
        from .webhooks import CFG_PATH as HOOK_PATH, load_cfg as _hook_cfg
        try:
            data = await request.json()
        except Exception as exc:
            return JSONResponse({"ok": False, "error": f"invalid json: {exc}"}, status_code=400)
        email = data.get("email") or {}
        hooks = data.get("webhooks") or {}
        if email.get("to") is not None:
            if isinstance(email["to"], str):
                email["to"] = [x.strip() for x in email["to"].replace("\n", ",").split(",") if x.strip()]
            if not email["to"] and email.get("enabled", True):
                return JSONResponse({"ok": False, "error": "收件人不能为空"}, status_code=400)

        def _write(path, obj):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                _json.dump(obj, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)

        if email:
            cfg_e = _mail_cfg()
            cfg_e.update({k: v for k, v in email.items() if v is not None})
            _write(EMAIL_PATH, cfg_e)
        if hooks:
            cfg_w = _hook_cfg()
            cfg_w.update({k: v for k, v in hooks.items() if v is not None})
            _write(HOOK_PATH, cfg_w)
        return JSONResponse({"ok": True})

    @app.post("/api/push/password")
    async def api_push_password(request: Request):
        from .mailer import load_cfg as _mail_cfg
        try:
            data = await request.json()
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        pw = (data.get("password") or "").strip()
        if not pw:
            return JSONResponse({"ok": False, "error": "密码不能为空"}, status_code=400)
        path = os.path.expanduser(_mail_cfg().get("password_file", "~/.neurodaily_smtp"))
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(pw)
            os.chmod(path, 0o600)
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return JSONResponse({"ok": True, "path": path})

    @app.get("/report/latest")
    def report_latest():
        def _header(path) -> str:
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    return f.read(4096)
            except OSError:
                return ""

        p = getattr(app.state, "last_report_path", None)
        if p and os.path.isfile(p) and "(demo)" not in _header(p):
            return FileResponse(p, media_type="text/html")

        files = sorted((f for f in Path(_cfg().output_dir()).glob("*.html") if f.is_file()),
                       key=os.path.getmtime, reverse=True)
        demo = None
        for file in files:
            header = _header(file)
            # Custom filenames can still be identified by either report renderer.
            if not (file.name.startswith("neurodaily_") or 'name="nd-base"' in header
                    or "<title>NeuroDaily</title>" in header):
                continue
            if "(demo)" not in header:
                return FileResponse(file, media_type="text/html")
            demo = demo or file
        if demo is not None:
            return FileResponse(demo, media_type="text/html")
        return JSONResponse({"error": "no report yet"}, status_code=404)

    @app.get("/api/launchd/status")
    def api_launchd_status():
        cfg = _cfg()
        sched = cfg.scheduled or {}
        if desktop:
            due = scheduled_time(sched)
            return JSONResponse({"backend": "desktop", "loaded": due is not None,
                                 "schedule": due.strftime("%H:%M") if due else ""})
        label = _launchd_label()
        dest = os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")
        loaded = False
        try:
            out = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10).stdout
            loaded = label in out
        except Exception:
            pass
        return JSONResponse({
            "installed": os.path.exists(dest),
            "loaded": loaded,
            "label": label,
            "schedule": f"{int(sched.get('hour', 8)):02d}:{int(sched.get('minute', 0)):02d}",
        })

    @app.post("/api/launchd/install")
    def api_launchd_install():
        if desktop:
            return JSONResponse({"ok": False, "error": "Save desktop schedule settings instead."},
                                status_code=400)
        try:
            from .cli import _plist_content
            cfg = _cfg()
            pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            label = _launchd_label()
            content = _plist_content(cfg, pkg_root)
            plist_path = os.path.join(pkg_root, "scripts", f"{label}.plist")
            os.makedirs(os.path.dirname(plist_path), exist_ok=True)
            with open(plist_path, "w", encoding="utf-8") as f:
                f.write(content)
            dest = os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")
            subprocess.run(["cp", plist_path, dest], check=False)
            subprocess.run(["launchctl", "unload", dest], check=False)
            subprocess.run(["launchctl", "load", "-w", dest], check=False)
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        return JSONResponse({"ok": True})

    @app.post("/api/launchd/uninstall")
    def api_launchd_uninstall():
        if desktop:
            return JSONResponse({"ok": False, "error": "Disable the schedule in desktop settings."},
                                status_code=400)
        try:
            label = _launchd_label()
            dest = os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")
            subprocess.run(["launchctl", "unload", dest], check=False)
            if os.path.exists(dest):
                os.remove(dest)
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        return JSONResponse({"ok": True})

    # ------------------------------------------------------------- history
    @app.get("/history", response_class=HTMLResponse)
    def history_page():
        runs = hist.list_runs(limit=200)
        rows = []
        for r in runs:
            status_cls = "ok" if r["status"] == "completed" else ("bad" if r["status"] == "failed" else "warn")
            src_summary = ", ".join(f"{k}:{v}" for k, v in
                                    sorted(r.get("source_counts", {}).items()))
            detail = f"/history/{r['id']}"
            rows.append(
                f"<tr data-id='{r['id']}'><td><a href='{detail}'>#{r['id']}</a></td>"
                f"<td>{r.get('finished_at','')[:19].replace('T',' ')}</td>"
                f"<td><span class='{status_cls}'>{r.get('status')}</span></td>"
                f"<td>{r.get('item_count')}</td>"
                f"<td class='hist-src'>{src_summary}</td>"
                f"<td><a href='{detail}'>view</a> · "
                f"<a href='#' class='del' data-id='{r['id']}'>delete</a></td></tr>")
        body = f"<div class='wrap'><h2>Search History</h2>"
        if rows:
            body += ("<p><button id='clearAll' class='btn-danger'>Clear all history</button></p>"
                     "<table class='hist'><thead><tr><th>#</th><th>Time</th><th>Status</th>"
                     "<th>Items</th><th>Sources</th><th></th></tr></thead><tbody>"
                     + "".join(rows) + "</tbody></table>")
        else:
            body += "<div class='empty'>No searches recorded yet. Run one first.</div>"
        body += "<p><a href='/'>← back to dashboard</a></p></div>"
        body += """<script>
          document.querySelectorAll('a.del').forEach(function (a) {
            a.addEventListener('click', function (e) {
              e.preventDefault();
              var id = a.getAttribute('data-id');
              if (!confirm('Delete history record #' + id + '?')) return;
              fetch('/api/history/' + id, { method: 'DELETE' })
                .then(function (r) { return r.json(); })
                .then(function () { a.closest('tr').remove(); })
                .catch(function () { alert('delete failed'); });
            });
          });
          var ca = document.getElementById('clearAll');
          if (ca) ca.addEventListener('click', function () {
            if (!confirm('Delete ALL history records?')) return;
            fetch('/api/history/clear', { method: 'POST' })
              .then(function (r) { return r.json(); })
              .then(function () { location.reload(); });
          });
        </script>"""
        return f"<!DOCTYPE html><html><head><meta charset='utf-8'>" \
               f"<title>NeuroDaily — History</title>{_css()}</head><body>" \
               f"<header class='mini'><h1>NeuroDaily History</h1></header><main>{body}</main></body></html>"

    @app.get("/history/{run_id}", response_class=HTMLResponse)
    def history_detail(run_id: int):
        r = hist.get_run(run_id)
        if not r:
            return HTMLResponse("<h3>run not found</h3>", status_code=404)
        # if a report was saved, serve/read it
        report_rel = r.get("report_path", "")
        if report_rel:
            path = os.path.join(_cfg().output_dir(), report_rel)
            if os.path.exists(path):
                return FileResponse(path, media_type="text/html")
        # otherwise render a summary page for skipped/failed runs
        src_summary = ", ".join(f"{k}: {v}" for k, v in sorted(r.get("source_counts", {}).items()))
        body = (
            f"<div class='wrap'><h2>Run #{r['id']}</h2>"
            f"<p><b>Profile:</b> {r.get('profile')}</p>"
            f"<p><b>Status:</b> <span class='{r.get('status')}'>{r.get('status')}</span>"
            f"{(' — ' + str(r.get('skipped_reason',''))) if r.get('skipped_reason') else ''}</p>"
            f"<p><b>Started:</b> {r.get('started_at','')[:19].replace('T',' ')}</p>"
            f"<p><b>Finished:</b> {r.get('finished_at','')[:19].replace('T',' ')}</p>"
            f"<p><b>Items:</b> {r.get('item_count')}</p>"
            f"<p><b>Sources:</b> {src_summary or '—'}</p>"
            f"<p><a href='/history'>← back to history</a> · <a href='/'>dashboard</a></p>"
            f"</div>")
        return f"<!DOCTYPE html><html><head><meta charset='utf-8'>" \
               f"<title>NeuroDaily — Run #{r['id']}</title>{_css()}</head><body>" \
               f"<header class='mini'><h1>Run #{r['id']}</h1></header><main>{body}</main></body></html>"

    @app.get("/api/history")
    def api_history():
        runs = hist.list_runs(limit=100)
        return JSONResponse({"count": len(runs), "runs": runs})

    @app.delete("/api/history/{run_id}")
    def api_history_delete(run_id: int):
        removed = hist.delete_run(run_id)
        _refresh_static_history()
        return JSONResponse({"deleted": removed, "run_id": run_id})

    @app.post("/api/history/clear")
    def api_history_clear():
        removed = hist.clear_history()
        _refresh_static_history()
        return JSONResponse({"deleted": removed})

    return app


def _refresh_static_history() -> None:
    """Rewrite output/history.html so file:// browsing reflects deletions."""
    try:
        from .digest import _write_static_history
        outdir = DEFAULT_CONFIG().output_dir()
        _write_static_history(outdir)
    except Exception:
        pass


def _css() -> str:
    return ("<style>"
            "body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#000;color:#e8e8e8;margin:0}"
            ".wrap{max-width:1080px;margin:0 auto;padding:24px}"
            "header.mini{padding:20px 24px;border-bottom:1px solid #222;background:#000}"
            "header.mini h1{margin:0;font-size:1.3rem;color:#38bdf8}"
            "a{color:#38bdf8;text-decoration:none}a:hover{text-decoration:underline}"
            "table.hist{width:100%;border-collapse:collapse;font-size:.85rem;margin-top:12px}"
            "table.hist th,table.hist td{text-align:left;padding:8px;border-bottom:1px solid #222}"
            "table.hist th{color:#8a8a8a} .hist-src{color:#8a8a8a;font-size:.75rem}"
            ".ok{color:#34d399}.bad{color:#fbbf24}.warn{color:#fbbf24}"
            ".empty{color:#8a8a8a;padding:12px;border:1px dashed #222;border-radius:12px}"
            ".del{color:#f87171}.btn-danger{background:#1c0a0a;color:#fecaca;border:1px solid #b91c1c;"
            "border-radius:8px;padding:6px 14px;font-size:.8rem;cursor:pointer}"
            ".btn-danger:hover{background:#2a0f0f}"
            "</style>")


# For `uvicorn neurodaily.webapp:app`
app = create_app()
