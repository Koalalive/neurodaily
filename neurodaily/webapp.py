"""FastAPI web app for NeuroDaily.

Routes:
    GET  /            -> dashboard: run + view latest report inline
    POST /api/run     -> run a digest now (background task; dedup-aware, ?force=1 bypasses)
    GET  /api/status  -> recent runs / health
    GET  /api/prompt  -> structured focus prompt JSON + text
    GET  /reports     -> list generated HTML reports
    GET  /reports/{file} -> serve a report
    GET  /history     -> list all past search runs (web page)
    GET  /history/{run_id} -> view a past run (saved report or summary page)
    GET  /api/history -> JSON list of past runs
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import Config, DEFAULT_CONFIG
from .digest import run as run_digest, render_html_for
from .settings_page import SETTINGS_HTML, DASHBOARD_SETTINGS_LINK
from . import history as hist


def create_app() -> FastAPI:
    app = FastAPI(title="NeuroDaily", version="0.1.0")
    app.state.last_run = None

    def _cfg() -> Config:
        try:
            return Config.load()
        except Exception:
            return DEFAULT_CONFIG()

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request=None):
        cfg = _cfg()
        result = app.state.last_run
        # render using last run if available, else show an empty-but-styled page
        if result is None:
            from .digest import DigestResult
            result = DigestResult(items=[], sections={"papers": [], "industry": [],
                                                     "trials_conferences": [], "policy": []},
                                  health=[], generated_at=datetime.now().isoformat(),
                                  config_profile=cfg.profile, config=cfg)
        html = render_html_for(result)
        return html.replace("</body>", DASHBOARD_SETTINGS_LINK + "</body>", 1)

    @app.post("/api/run")
    def api_run(background_tasks: BackgroundTasks, force: bool = False):
        cfg = _cfg()

        def _do():
            result = run_digest(cfg, check_duplicate=True, record=True, force=force)
            app.state.last_run = result
            from .digest import save_report
            fmt = cfg.output.get("filename_format", "neurodaily_%Y-%m-%d.html")
            path = os.path.join(cfg.output_dir(), datetime.now().strftime(fmt))
            save_report(result, path)
            app.state.last_report_path = path
            return result

        background_tasks.add_task(_do)
        return JSONResponse({"status": "started", "profile": cfg.profile,
                             "force": force,
                             "started_at": datetime.now().isoformat()})

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
        return JSONResponse(Config.load().to_dict())

    @app.post("/api/config")
    async def api_config_post(request: Request):
        try:
            data = await request.json()
        except Exception as e:
            return JSONResponse({"ok": False, "error": f"invalid json: {e}"}, status_code=400)
        if not isinstance(data, dict) or not data.get("disciplines"):
            return JSONResponse({"ok": False, "error": "disciplines 不能为空"}, status_code=400)
        try:
            cfg = Config.from_dict(data)
            path = cfg.save()
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        return JSONResponse({"ok": True, "path": path})

    @app.post("/api/config/reset")
    def api_config_reset():
        try:
            path = DEFAULT_CONFIG().save()
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        return JSONResponse({"ok": True, "path": path})

    def _launchd_label() -> str:
        cfg = Config.load()
        sched = cfg.scheduled or {}
        return ((sched.get("launchd") or {}).get("label")) or "com.neurodaily.daily"

    @app.get("/api/launchd/status")
    def api_launchd_status():
        cfg = Config.load()
        sched = cfg.scheduled or {}
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
        try:
            from .cli import _plist_content
            cfg = Config.load()
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
