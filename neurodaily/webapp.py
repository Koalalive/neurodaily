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
import json
import os
import re
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Event, Lock, Thread

from fastapi import FastAPI, BackgroundTasks, Query, Request
from starlette.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import Config, DEFAULT_CONFIG, DEFAULT_DIRS
from .desktop_schedule import RETRY_DELAY, run_schedule, scheduled_time
from .desktop_page import render_workspace
from .digest import preview_search, run as run_digest, render_html_for
from .presets import research_presets
from .settings_page import SETTINGS_HTML, DASHBOARD_SETTINGS_LINK
from .run_page import RUN_HTML
from .ui_translations import UI_LANGUAGES, localize_document
from . import __version__, history as hist, task_runs


def _saved_report_date(path: Path, html: str = "") -> str:
    try:
        if not html:
            with path.open(encoding="utf-8", errors="replace") as handle:
                html = handle.read(65536)
        meta = re.search(r'<meta name="nd-report-date" content="(\d{4}-\d{2}-\d{2})"', html)
        if meta:
            return meta[1]
        filename = re.search(r"\d{4}-\d{2}-\d{2}", path.name)
        return filename[0] if filename else datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
    except OSError:
        return ""


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


def create_app(config_path: str | None = None, *, desktop: bool = False,
               open_report_browser: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        stop = Event()
        guard = task_runs.acquire()
        if guard is not None:
            with guard:
                task_runs.recover()
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
    preferences = (Path(config_path).parent if config_path else Path(DEFAULT_DIRS["config"])) / "ui.json"

    def _language():
        try:
            value = json.loads(preferences.read_text(encoding="utf-8")).get("language")
            if value in UI_LANGUAGES:
                return value
        except (OSError, ValueError, AttributeError):
            pass
        return "zh"

    def _page(html: str):
        return HTMLResponse(localize_document(html, _language()), headers={"Cache-Control": "no-store"})

    def _report(path, ui):
        if ui:
            from .render import refresh_saved_research_map

            path = Path(path)
            html = path.read_text(encoding="utf-8", errors="replace")
            if 'name="nd-report-date"' not in html:
                date = _saved_report_date(path, html)
                html = html.replace("</head>", f'<meta name="nd-report-date" content="{date}"></head>', 1)
            html = re.sub(r'<details id="bibliometrics"\b[^>]*>[\s\S]*?</details>', "", html, count=1)
            return _page(refresh_saved_research_map(html, _language()))
        return FileResponse(path, media_type="text/html")

    def _cfg() -> Config:
        try:
            return Config.load(config_path)
        except Exception:
            return DEFAULT_CONFIG()

    @app.get("/api/ui/preferences")
    def api_ui_preferences():
        return {"language": _language()}

    @app.post("/api/ui/preferences")
    def api_ui_preferences_save(payload: dict):
        language = payload.get("language")
        if language not in UI_LANGUAGES:
            return JSONResponse({"error": "Unsupported UI language"}, status_code=400)
        preferences.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=preferences.parent, delete=False) as f:
            temp_path = Path(f.name)
            try:
                json.dump({"language": language}, f)
                f.close()
                temp_path.replace(preferences)
            finally:
                temp_path.unlink(missing_ok=True)
        return {"language": language}

    @app.get("/desktop", response_class=HTMLResponse)
    def desktop_workspace():
        latest = task_runs.latest()
        after = latest["id"] if latest else 0
        if latest and latest["status"] == "running" and not latest["report_ready"]:
            after -= 1
        report = _latest_report(_cfg(), include_demo=False)
        date = _saved_report_date(report) if report else ""
        return HTMLResponse(render_workspace(_language(), after, date), headers={"Cache-Control": "no-store"})

    @app.get("/api/ui/reports")
    def api_workspace_reports(after: int = 0):
        return JSONResponse({"reports": task_runs.reports_since(after)}, headers={"Cache-Control": "no-store"})

    @app.get("/", response_class=HTMLResponse)
    def dashboard(ui: bool = False):
        cfg = _cfg()
        result = app.state.last_run
        if result is not None and result.config_profile != cfg.profile:
            result = None
        if result is None:
            previous = _latest_report(cfg, include_demo=False)
            if previous is not None:
                return _report(previous, ui)
            if os.environ.get("NEURODAILY_DEMO"):
                from .demo import build_result
                result = build_result(cfg)
            else:
                if ui:
                    return _page("<!doctype html><html><head><meta charset='utf-8'>"
                                 f"<title>最新日报</title>{_css()}</head><body><main class='wrap'>"
                                 "<h1>最新日报</h1><p>尚无已保存的日报。</p>"
                                 "<p><a href='/run'>开始检索</a> · <a href='/settings'>设置</a></p>"
                                 "</main></body></html>")
                from .digest import DigestResult
                result = DigestResult(items=[], sections={"papers": [], "industry": [],
                                                         "trials_conferences": [], "policy": []},
                                      health=[], generated_at=datetime.now().isoformat(),
                                      config_profile=cfg.profile, config=cfg)
        html = render_html_for(result)
        return _page(html.replace("</body>", DASHBOARD_SETTINGS_LINK + "</body>", 1))

    @app.get("/run", response_class=HTMLResponse)
    def run_now_page():
        return _page(RUN_HTML)

    def _begin_search(cfg: Config, mode: str, scheduled_for: datetime | None = None):
        with search_lock:
            current = app.state.search_attempt
            if current and current["status"] == "running":
                return None
            guard = task_runs.acquire()
            if guard is None:
                return None
            try:
                task_runs.recover()
                if scheduled_for is not None:
                    previous = hist.desktop_schedule_result(cfg.profile, scheduled_for)
                    if previous and (previous["status"] == "completed" or datetime.now() <
                                     datetime.fromisoformat(previous["finished_at"]) + RETRY_DELAY):
                        guard.close()
                        return None
                attempt = task_runs.begin(cfg, mode, scheduled_for)
            except BaseException:
                guard.close()
                raise
            app.state.search_attempt = attempt
            return attempt, guard

    def _search_and_deliver(cfg: Config, attempt: dict, force: bool, mode: str):
        from .digest import index_saved_report, save_report, snapshot

        def sources(changes):
            attempt["sources"].update(changes)
            task_runs.save(attempt)

        def stage(name, status, error=""):
            task_runs.stage(attempt, name, status, error)
            task_runs.save(attempt)

        result = run_digest(cfg, check_duplicate=True, record=False, force=force,
                            mode=mode, progress=sources)
        if result.skipped:
            stage("search", "skipped")
            task_runs.finish(attempt, "skipped", result.skipped_reason)
            return

        sources({row["source"]: {"status": row.get("status", "ok" if row["ok"] else "failed"),
                                 **{key: row[key] for key in ("count", "fetched", "ms") if key in row}}
                 for row in result.health})
        attempt["item_count"] = len(result.items)
        if not any(row["ok"] for row in result.health):
            error = "All enabled sources failed." if result.health else "No sources are enabled."
            stage("search", "failed", error)
            task_runs.save(attempt, result=result, snapshot=snapshot(result, mode))
            task_runs.finish(attempt, "failed", error)
            return
        stage("search", "completed")
        fmt = cfg.output.get("filename_format") or "neurodaily_%Y-%m-%d_%H%M%S.html"
        path = Path(cfg.output_dir(), datetime.now().strftime(fmt)).absolute()
        if path.exists():
            path = path.with_name(f"{path.stem}-{attempt['id']}{path.suffix}")
        result.history_id = attempt["id"]
        base = getattr(app.state, "base_url", "") or "http://127.0.0.1:8031"
        result.report_base_url = base
        result.report_locale = _language()

        stage("metrics", "running")
        try:
            from .journal_metrics import ensure_fresh, for_item
            if ensure_fresh([j.name for j in cfg.journals]):
                for item in result.items:
                    metrics = for_item(item, cfg)
                    if metrics:
                        item.extra["metrics"] = metrics
            stage("metrics", "completed")
        except Exception:
            stage("metrics", "failed", "期刊指标更新失败。")

        stage("ai", "running")
        try:
            from .ai_summary import generate, load_cfg
            result.ai_summary = generate(result)
            if result.ai_summary:
                result.ai_summary_meta = {"model": load_cfg().get("model", "")}
            stage("ai", "completed" if result.ai_summary else "skipped")
        except Exception:
            stage("ai", "failed", "AI 摘要生成失败，请检查设置中的 AI 连通性。")

        try:
            from .research_activity import enrich_geography
            if enrich_geography(result):
                partial = bool(result.geography.get("deferred"))
                stage("geolocation", "partial" if partial else "completed")
            else:
                stage("geolocation", "skipped", "未启用或缺少大模型 API。")
        except Exception:
            stage("geolocation", "failed", "AI 地理定位未完成。")

        # Publish the report only after all optional sections are ready, so tabs
        # never show a half-finished report that is rewritten a few seconds later.
        stage("report", "running")
        result.report_revision = 1
        save_report(result, str(path))
        attempt.update(report_ready=True, report_file=str(path), report_revision=1)
        task_runs.stage(attempt, "report", "completed")
        task_runs.save(attempt, result=result, snapshot=snapshot(result, mode))
        index_saved_report(result)
        app.state.last_run = result

        stage("delivery", "running")
        try:
            from .delivery import deliver_report
            attempt["delivery"] = deliver_report(result, str(path), task_id=str(attempt["id"]))
            failures = any(value == "failed" for value in attempt["delivery"].values())
            stage("delivery", "partial" if failures else "completed",
                  "部分投递失败，可在任务详情中重试。" if failures else "")
        except Exception:
            logging.getLogger(__name__).exception("Could not deliver report")
            stage("delivery", "failed", "投递未完成，请查看任务详情。")

        task_runs.finish(attempt, "completed")
        if (open_report_browser and cfg.output.get("open_on_finish", True)
                and os.environ.get("NEURODAILY_NO_OPEN") != "1"):
            try:
                from webbrowser import open as open_browser
                open_browser(base.rstrip("/") + f"/history/{attempt['id']}/report")
            except Exception:
                logging.getLogger(__name__).debug("Could not open completed report", exc_info=True)

    def _execute_search(cfg: Config, attempt: dict, guard, force: bool = False, mode: str = "manual"):
        with guard:
            try:
                _search_and_deliver(cfg, attempt, force, mode)
            except Exception:
                logging.getLogger(__name__).exception("Search or report generation failed")
                error = "报告处理失败，请查看运行日志。"
                task_runs.stage(attempt, attempt["phase"], "failed", error)
                task_runs.finish(attempt, "completed" if attempt["report_ready"] else "failed", error)

    def _start_scheduled_search(cfg: Config, due: datetime) -> bool:
        started = _begin_search(cfg, "daily", due)
        if started is None:
            previous = hist.desktop_schedule_result(cfg.profile, due)
            return bool(previous and previous["status"] == "completed")
        _execute_search(cfg, *started, force=True, mode="daily")
        return started[0]["status"] == "completed"

    @app.post("/api/run")
    def api_run(background_tasks: BackgroundTasks, force: bool = False,
                hours: int | None = None):
        cfg = _cfg()
        if hours is not None and not (1 <= hours <= 8760):
            return JSONResponse({"error": "hours must be 1..8760"}, status_code=400)
        cfg = _cfg_with_hours(cfg, hours) if hours else cfg
        started = _begin_search(cfg, "manual")
        if started is None:
            return JSONResponse({"error": "A search is already running"}, status_code=409)

        attempt, guard = started
        background_tasks.add_task(_execute_search, cfg, attempt, guard, force)
        return JSONResponse({"status": "started", "profile": cfg.profile, "task_id": attempt["id"],
                             "force": force, "started_at": attempt["started_at"]})

    @app.get("/api/status")
    def api_status():
        cfg = _cfg()
        lr = app.state.last_run
        if lr is None or lr.config_profile != cfg.profile:
            task = task_runs.latest(profile=cfg.profile, ready=True)
            lr = task_runs.load_result(task["id"]) if task else None
        return {
            "profile": cfg.profile,
            "last_run": (lr.generated_at if lr else None),
            "item_count": (len(lr.items) if lr else 0),
            "sections": (lr.section_counts() if lr else {}),
            "health": (lr.health if lr else ["not run yet"]),
            "prompt": cfg.to_prompt(),
            "search": task_runs.latest(),
        }

    @app.get("/api/search/status")
    def api_search_status():
        return JSONResponse({"search": task_runs.latest()}, headers={"Cache-Control": "no-store"})

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
    def report_file(filename: str, ui: bool = False):
        cfg = _cfg()
        # sanitize
        base = os.path.basename(filename)
        path = os.path.join(cfg.output_dir(), base)
        if not os.path.exists(path):
            return HTMLResponse("<h3>report not found</h3>", status_code=404)
        return _report(path, ui)

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page():
        return _page(SETTINGS_HTML)

    @app.get("/archive", response_class=HTMLResponse)
    def archive_page():
        from .archive_search import opensearch_configured
        from .render import _stdlib_loader

        language = _language()
        template = _stdlib_loader().get_template("archive.html.j2")
        return _page(template.render(language=language, hybrid=opensearch_configured()))

    @app.get("/api/archive/search")
    def api_archive_search(q: str = Query(min_length=1, max_length=250), kind: str | None = None,
                           limit: int = Query(30, ge=1, le=100), backend: str = "local"):
        from .archive_search import ArchiveSearchError, search_archive

        try:
            result = search_archive(q, profile=_cfg().profile, kind=kind, limit=limit, backend=backend)
        except ValueError as error:
            return JSONResponse({"message": str(error)}, status_code=400)
        except ArchiveSearchError as error:
            return JSONResponse({"message": str(error)}, status_code=503)
        return JSONResponse(result, headers={"Cache-Control": "no-store"})

    @app.post("/api/archive/import")
    async def api_archive_import(request: Request):
        from .archive_search import ArchiveSearchError, index_report

        if await _service_draft(request) is None:
            return JSONResponse({"message": "Invalid archive request."}, status_code=400)

        def import_reports(profile):
            imported = 0
            for run_id in task_runs.archived_run_ids(profile):
                if result := task_runs.load_result(run_id):
                    index_report(result)
                    imported += 1
            return imported

        try:
            return {"reports": await run_in_threadpool(import_reports, _cfg().profile)}
        except ArchiveSearchError as error:
            return JSONResponse({"message": str(error)}, status_code=503)

    @app.get("/billing", response_class=HTMLResponse)
    def billing_page():
        from .render import _stdlib_loader

        language = _language()
        template = _stdlib_loader().get_template("billing.html.j2")
        return _page(template.render(language=language))

    @app.get("/api/billing")
    def api_billing_report(
        days: int = Query(30, ge=1, le=3650),
        limit: int = Query(50, ge=1, le=250),
        offset: int = Query(0, ge=0),
        purpose: str | None = None,
    ):
        from .api_billing import billing_report

        try:
            return JSONResponse(billing_report(days, limit, offset, purpose),
                                headers={"Cache-Control": "no-store"})
        except ValueError as exc:
            return JSONResponse({"message": str(exc)}, status_code=400)

    @app.get("/api/billing/settings")
    def api_billing_settings():
        from .api_billing import load_settings

        return JSONResponse(load_settings(), headers={"Cache-Control": "no-store"})

    @app.post("/api/billing/settings")
    async def api_billing_settings_save(request: Request):
        from .api_billing import save_settings

        draft = await _service_draft(request)
        if draft is None:
            return JSONResponse({"message": "Invalid billing settings."}, status_code=400)
        try:
            return JSONResponse(await run_in_threadpool(save_settings, draft),
                                headers={"Cache-Control": "no-store"})
        except ValueError as exc:
            return JSONResponse({"message": str(exc)}, status_code=400)

    @app.get("/api/config")
    def api_config_get():
        from .config import OPTIONAL_SOURCES

        config = _cfg()
        data = config.to_dict()
        data["sources"] = {**config.sources, **{name: config.source_opts(name) for name in OPTIONAL_SOURCES}}
        return JSONResponse(data)

    @app.get("/api/config/presets")
    def api_config_presets():
        return research_presets()

    @app.get("/api/config/export")
    def api_config_export():
        from .profile_exchange import export_profile
        cfg = _cfg()
        name = re.sub(r"[^a-zA-Z0-9_-]+", "-", cfg.profile).strip("-") or "research"
        return JSONResponse(export_profile(cfg), headers={
            "Content-Disposition": f'attachment; filename="neurodaily-{name}.json"',
            "Cache-Control": "no-store",
        })

    @app.post("/api/config/import")
    async def api_config_import(request: Request, apply: bool = False):
        from .profile_exchange import MAX_BYTES, import_profile
        payload = bytearray()
        async for block in request.stream():
            payload.extend(block)
            if len(payload) > MAX_BYTES:
                return JSONResponse({"error": "配置文件不能超过 256 KB"}, status_code=413)
        try:
            data = json.loads(payload)
        except (ValueError, UnicodeError):
            return JSONResponse({"error": "无法读取 JSON 配置文件"}, status_code=400)
        try:
            config, summary = import_profile(data, _cfg())
            if apply:
                config.save(config_path)
        except (ValueError, OSError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return {"ok": True, "applied": apply, "summary": summary}

    @app.post("/api/search/preview")
    async def api_search_preview(request: Request):
        from .schema import validate
        try:
            data = await request.json()
        except ValueError:
            return JSONResponse({"error": "无效 JSON"}, status_code=400)
        errors = validate(data)
        if errors:
            return JSONResponse({"error": errors[0], "errors": errors}, status_code=400)
        return await run_in_threadpool(preview_search, Config.from_dict(data))

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
            defaults = DEFAULT_CONFIG()
            if desktop:
                defaults.scheduled["enabled"] = False
            path = defaults.save(config_path)
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

    async def _service_draft(request: Request) -> dict | None:
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            return None
        try:
            draft = await request.json()
        except (ValueError, UnicodeError):
            return None
        return draft if isinstance(draft, dict) else None

    @app.post("/api/push/test")
    async def api_push_test(request: Request):
        from .mailer import test_connection

        draft = await _service_draft(request)
        if draft is None:
            return JSONResponse({"ok": False, "message": "邮件设置格式无效。"}, status_code=400)
        return await run_in_threadpool(test_connection, draft)

    @app.get("/api/ai/settings")
    def api_ai_settings():
        from .ai_summary import public_settings

        return JSONResponse(public_settings(), headers={"Cache-Control": "no-store"})

    @app.post("/api/ai/settings")
    async def api_ai_settings_save(request: Request):
        from .ai_summary import save_settings

        draft = await _service_draft(request)
        if draft is None:
            return JSONResponse({"ok": False, "message": "AI 设置格式无效。"}, status_code=400)
        try:
            return {"ok": True, **save_settings(draft)}
        except ValueError as exc:
            return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)
        except OSError:
            return JSONResponse({"ok": False, "message": "无法写入本机 AI 设置。"}, status_code=500)

    @app.post("/api/ai/test")
    async def api_ai_test(request: Request):
        from .ai_summary import test_connection

        draft = await _service_draft(request)
        if draft is None:
            return JSONResponse({"ok": False, "message": "AI 设置格式无效。"}, status_code=400)
        return await run_in_threadpool(test_connection, draft)

    def _latest_report(cfg: Config, *, include_demo: bool = True) -> Path | None:
        def header(path) -> str:
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    return handle.read(65536).split("</head>", 1)[0]
            except OSError:
                return ""

        task = task_runs.latest(profile=cfg.profile, ready=True)
        if task and "(demo)" not in header(task["report_file"]):
            return Path(task["report_file"])

        files = sorted((f for f in Path(cfg.output_dir()).glob("*.html") if f.is_file()),
                       key=os.path.getmtime, reverse=True)
        demo = None
        for file in files:
            text = header(file)
            if not (file.name.startswith("neurodaily_") or 'name="nd-base"' in text
                    or "<title>NeuroDaily</title>" in text):
                continue
            if "(demo)" not in text:
                return file
            demo = demo or file
        return demo if include_demo else None

    @app.get("/report/latest")
    def report_latest(ui: bool = False):
        path = _latest_report(_cfg())
        if path is not None:
            return _report(path, ui)
        return JSONResponse({"error": "no report yet"}, status_code=404)

    @app.get("/api/launchd/status")
    def api_launchd_status():
        cfg = _cfg()
        sched = cfg.scheduled or {}
        if desktop:
            schedule = scheduled_time(sched)
            current = datetime.now()
            due = datetime.combine(current.date(), schedule) if schedule is not None else None
            slot = hist.desktop_schedule_result(cfg.profile, due) if due is not None else None
            next_run = due
            if slot and slot["status"] == "completed":
                next_run += timedelta(days=1)
            if slot and slot["status"] != "completed":
                next_run = max(current, datetime.fromisoformat(slot["finished_at"]) + RETRY_DELAY)
                if next_run.date() != current.date():
                    next_run = due + timedelta(days=1)
            attempt = app.state.search_attempt or {}
            state = "off" if due is None else "scheduled"
            if due is not None and due <= current:
                if attempt.get("status") == "running" and attempt.get("scheduled_for") == due.isoformat():
                    state = "running"
                elif slot and slot["status"] != "completed":
                    state = "retrying"
                elif not slot:
                    state = "waiting"
            return JSONResponse({"backend": "desktop", "loaded": due is not None,
                                 "schedule": schedule.strftime("%H:%M") if schedule is not None else "",
                                 "state": state, "next_run": next_run.isoformat() if next_run else None,
                                 "last_run": hist.desktop_schedule_result(cfg.profile)})
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
            src_summary = ", ".join(f"{escape(k)}:{v}" for k, v in
                                    sorted(r.get("source_counts", {}).items()))
            detail = f"/history/{r['id']}"
            rows.append(
                f"<tr data-id='{r['id']}'><td><a href='{detail}'>#{r['id']}</a></td>"
                f"<td>{(r.get('finished_at') or r.get('started_at') or '')[:19].replace('T',' ')}</td>"
                f"<td><span class='{status_cls}'>{r.get('status')}</span></td>"
                f"<td>{r.get('item_count')}</td>"
                f"<td class='hist-src'>{src_summary}</td>"
                f"<td><a href='{detail}'>view</a> · "
                f"<a href='#' class='del' data-id='{r['id']}'>delete</a></td></tr>")
        body = "<div class='wrap'><h2>Search History</h2><p><a href='/archive'>历史条目检索</a></p>"
        snapshots = [r for r in runs if r["has_snapshot"]]
        if len(snapshots) >= 2:
            before, after = snapshots[1]["id"], snapshots[0]["id"]
            def options(selected):
                return "".join(f"<option value='{r['id']}'{' selected' if r['id'] == selected else ''}>"
                               f"#{r['id']} · {escape(r['profile'])}</option>" for r in snapshots)
            body += (
                "<form action='/history/compare' method='get'>"
                f"<label>基准 <select name='before'>{options(before)}</select></label> "
                f"<label>比较 <select name='after'>{options(after)}</select></label> "
                "<button type='submit'>比较检索</button></form>"
            )
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
                .then(function (r) { if (!r.ok) throw new Error(); })
                .then(function () { a.closest('tr').remove(); })
                .catch(function () { alert('delete failed'); });
            });
          });
          var ca = document.getElementById('clearAll');
          if (ca) ca.addEventListener('click', function () {
            if (!confirm('Delete ALL history records?')) return;
            fetch('/api/history/clear', { method: 'POST' })
              .then(function (r) { if (!r.ok) throw new Error(); })
              .then(function () { location.reload(); })
              .catch(function () { alert('clear history failed'); });
          });
        </script>"""
        return _page(f"<!DOCTYPE html><html><head><meta charset='utf-8'>" \
               f"<title>NeuroDaily — History</title>{_css()}</head><body>" \
               f"<header class='mini'><h1>NeuroDaily History</h1></header><main>{body}</main></body></html>")

    @app.get("/api/history/compare")
    @app.get("/history/compare", response_class=HTMLResponse)
    def history_compare(request: Request, before: int, after: int):
        older, newer = hist.get_run(before), hist.get_run(after)
        if not older or not newer:
            return JSONResponse({"error": "所选历史记录不存在"}, status_code=404)
        try:
            result = hist.compare_runs(older, newer)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        if request.url.path.startswith("/api/"):
            return JSONResponse(result)
        def run_summary(run):
            snapshot = run["snapshot"]
            query = snapshot["search"].get("query") or "按学科及全局关键词"
            sets = snapshot["search"].get("sets", {})
            sources = "".join(
                f"<li>{escape(row['source'])} · {escape(row['status'])} · "
                f"{escape(str(row.get('coverage') or ''))}<br>"
                f"<code>{escape('; '.join(row.get('queries') or [row.get('query') or '']) or '—')}</code></li>"
                for row in snapshot["sources"]
            )
            return (f"<h3>#{run['id']} · {escape(run['profile'])}</h3><pre>{escape(query)}</pre>"
                    + "".join(f"<div>#{escape(key.lstrip('#'))} · {escape(value)}</div>"
                              for key, value in sets.items())
                    + f"<ul>{sources}</ul>")
        def records(label, items):
            entries = "".join(f"<li>{escape(item['title'])}</li>" for item in items)
            return f"<h3>{label} {len(items)}</h3><ol>{entries}</ol>"
        return _page("<!doctype html><html lang='zh'><head><meta charset='utf-8'><title>比较检索</title>"
                f"{_css()}</head><body><main class='wrap'><h2>比较检索</h2>"
                f"<p>两次均命中 {result['in_both']} 条。来源状态和时间窗口见各次记录。</p>"
                f"{run_summary(older)}{run_summary(newer)}"
                f"{records('此次新增', result['added'])}{records('此次未出现', result['removed'])}"
                "<a href='/history'>返回历史</a></main></body></html>")

    @app.get("/api/history/{run_id}")
    def api_history_detail(run_id: int):
        row = hist.get_run(run_id)
        if row and row["task"]:
            from .delivery_receipts import list_receipts
            row["receipts"] = list_receipts(str(run_id))
        return JSONResponse(row) if row else JSONResponse({"error": "记录不存在"}, status_code=404)

    @app.get("/history/{run_id}/report")
    def history_task_report(run_id: int, ui: bool = False):
        row = hist.get_run(run_id)
        task = row and row["task"]
        if task and task["report_ready"] and Path(task["report_file"]).is_file():
            return _report(task["report_file"], ui)
        if row and not task and row.get("report_path"):
            path = Path(_cfg().output_dir(), os.path.basename(row["report_path"]))
            if path.is_file():
                return _report(path, ui)
        response = _page("<h3>日报未生成或已清理。</h3>")
        response.status_code = 404
        return response

    @app.post("/api/history/{run_id}/delivery/{destination}/retry")
    def api_delivery_retry(run_id: int, destination: str):
        from .delivery import retry_delivery
        guard = task_runs.acquire()
        if guard is None:
            return JSONResponse({"error": "任务正在运行，请结束后再重试。"}, status_code=409)
        with guard:
            task_runs.recover()
            row = hist.get_run(run_id)
            task = row and row["task"]
            if not task or not task["report_ready"] or not Path(task["report_file"]).is_file():
                return JSONResponse({"error": "找不到此任务的已保存日报。"}, status_code=404)
            result = task_runs.load_result(run_id)
            if result is None:
                return JSONResponse({"error": "找不到此任务的检索结果。"}, status_code=404)
            try:
                return JSONResponse(retry_delivery(result, task["report_file"], str(run_id), destination))
            except ValueError as exc:
                return JSONResponse({"error": str(exc)}, status_code=409)

    @app.get("/history/{run_id}", response_class=HTMLResponse)
    def history_detail(run_id: int, ui: bool = False):
        r = hist.get_run(run_id)
        if not r:
            return HTMLResponse("<h3>run not found</h3>", status_code=404)
        if r["task"]:
            from .delivery_receipts import list_receipts
            from .task_page import render_task
            return _page(render_task(r["task"], list_receipts(str(run_id)), _css()))
        # if a report was saved, serve/read it
        report_rel = r.get("report_path", "")
        if report_rel:
            path = os.path.join(_cfg().output_dir(), report_rel)
            if os.path.exists(path):
                return _report(path, ui)
        # otherwise render a summary page for skipped/failed runs
        src_summary = ", ".join(f"{k}: {v}" for k, v in sorted(r.get("source_counts", {}).items()))
        body = (
            f"<div class='wrap'><h2>Run #{r['id']}</h2>"
            f"<p><b>Profile:</b> {r.get('profile')}</p>"
            f"<p><b>Status:</b> <span class='{r.get('status')}'>{r.get('status')}</span>"
            f"{(' — ' + str(r.get('skipped_reason',''))) if r.get('skipped_reason') else ''}</p>"
            f"<p><b>Started:</b> {r.get('started_at','')[:19].replace('T',' ')}</p>"
            f"<p><b>Finished:</b> {(r.get('finished_at') or r.get('started_at') or '')[:19].replace('T',' ')}</p>"
            f"<p><b>Items:</b> {r.get('item_count')}</p>"
            f"<p><b>Sources:</b> {src_summary or '—'}</p>"
            f"<p><a href='/history'>← back to history</a> · <a href='/'>dashboard</a></p>"
            f"</div>")
        return _page(f"<!DOCTYPE html><html><head><meta charset='utf-8'>" \
               f"<title>NeuroDaily — Run #{r['id']}</title>{_css()}</head><body>" \
               f"<header class='mini'><h1>Run #{r['id']}</h1></header><main>{body}</main></body></html>")

    @app.get("/api/history")
    def api_history():
        runs = hist.list_runs(limit=100)
        return JSONResponse({"count": len(runs), "runs": runs})

    @app.delete("/api/history/{run_id}")
    def api_history_delete(run_id: int):
        guard = task_runs.acquire()
        if guard is None:
            return JSONResponse({"error": "任务正在运行。"}, status_code=409)
        with guard:
            removed = hist.delete_run(run_id)
            _refresh_static_history()
        return JSONResponse({"deleted": removed, "run_id": run_id})

    @app.post("/api/history/clear")
    def api_history_clear():
        guard = task_runs.acquire()
        if guard is None:
            return JSONResponse({"error": "任务正在运行。"}, status_code=409)
        with guard:
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
