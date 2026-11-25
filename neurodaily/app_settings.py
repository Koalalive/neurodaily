"""Portable application settings (not the research/search profile).

This covers local app behavior: output, schedule, email recipients/language,
webhooks and AI connection defaults. Research identity, disciplines, sources,
journals and search queries stay in the profile export.

Secrets are omitted by default. `include_secrets=True` is only for an explicit
local backup, never for a shared settings file.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .config import Config, DEFAULT_DIRS
from . import ai_summary, mailer, webhooks

FORMAT = "neurodaily.app-settings"
VERSION = 1
OUTPUT_KEYS = {"dir", "filename_format", "open_on_finish", "keep_reports", "extra_formats", "topic_map", "topic_ai_labels"}
SCHEDULE_KEYS = {"enabled", "hour", "minute"}
AI_KEYS = {"enabled", "base_url", "model", "max_papers", "max_other", "max_input_chars", "max_tokens"}
EMAIL_KEYS = {"enabled", "to", "recipients", "language", "smtp_host", "smtp_port", "use_ssl",
              "username", "from", "from_name", "subject_template", "attach_report",
              "attach_max_mb", "summary_papers", "summary_chars", "body_mode", "max_papers", "max_other",
              "public_url"}
SECRET_KEYS = {"password", "api_key", "password_env", "api_key_env", "password_file", "api_key_file"}


def _write(path: str, value: Any) -> None:
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".settings-", suffix=".json", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as stream:
            data = json.load(stream)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _ui_path(config_path: str | None) -> str:
    return os.path.join(os.path.dirname(config_path or Config.default_path()), "ui.json")


def _clean_email(cfg: dict, include_secrets: bool) -> dict:
    out = {key: cfg[key] for key in EMAIL_KEYS if key in cfg}
    out["to"] = list(cfg.get("to") or [])
    out["recipients"] = mailer.recipients(cfg)
    if not include_secrets:
        for key in SECRET_KEYS:
            out.pop(key, None)
        out["password_set"] = bool(mailer._password(cfg))
    return out


def _clean_ai(cfg: dict, include_secrets: bool) -> dict:
    out = {key: cfg[key] for key in AI_KEYS if key in cfg}
    if not include_secrets:
        for key in SECRET_KEYS:
            out.pop(key, None)
        out["api_key_set"] = bool(ai_summary.api_key(cfg))
    return out


def export_settings(config_path: str | None = None, *, include_secrets: bool = False) -> dict:
    cfg = Config.load(config_path)
    email = mailer.load_cfg()
    hooks = webhooks.load_cfg()
    ai = ai_summary.load_cfg()
    web = {key: hooks.get(key, "") for key in ("feishu", "wecom")}
    if not include_secrets:
        web = {key: "" for key in web}
    return {
        "format": FORMAT,
        "version": VERSION,
        "settings": {
            "output": {key: cfg.output.get(key) for key in OUTPUT_KEYS if key in cfg.output},
            "scheduled": {key: (cfg.scheduled or {}).get(key) for key in SCHEDULE_KEYS
                          if key in (cfg.scheduled or {})},
            "email": _clean_email(email, include_secrets),
            "webhooks": web,
            "ai": _clean_ai(ai, include_secrets),
            "ui": {"language": _read_ui(config_path)},
        },
    }


def _read_ui(config_path: str | None) -> str:
    value = _json(_ui_path(config_path)).get("language")
    return value if value in {"zh", "en", "ru"} else "zh"


def _merge(current: dict, incoming: Any, allowed: set[str]) -> dict:
    if not isinstance(incoming, dict):
        raise ValueError("settings section must be an object")
    result = dict(current)
    for key, value in incoming.items():
        if key in allowed:
            result[key] = value
    return result


def import_settings(document: Any, config_path: str | None = None, *, expected_version: str | None = None) -> dict:
    if not isinstance(document, dict) or document.get("format") != FORMAT or document.get("version") != VERSION:
        raise ValueError(f"settings must use format {FORMAT!r} and version {VERSION}")
    settings = document.get("settings")
    if not isinstance(settings, dict):
        raise ValueError("settings must be an object")

    hooks = settings.get("webhooks")
    if "webhooks" in settings and not isinstance(hooks, dict):
        raise ValueError("settings.webhooks must be an object")
    hook_updates = webhooks.normalize_updates(hooks or {}, allow_clear=False)

    ai = settings.get("ai")
    if isinstance(ai, dict):
        current = ai_summary.load_cfg()
        incoming = {key: ai[key] for key in AI_KEYS if key in ai}
        ai, _ = ai_summary._settings_draft(incoming, current)
        ai.update({key: incoming[key] for key in incoming.keys() - {"base_url", "enabled", "model"}})

    email = settings.get("email")
    if isinstance(email, dict):
        saved = mailer.load_cfg()
        email = {**saved, **{key: value for key, value in email.items() if key in EMAIL_KEYS}}
        mailer.validate_smtp_change(saved, email)

    cfg = Config.load(config_path)
    baseline_version = expected_version if expected_version is not None else cfg.version()
    if "output" in settings:
        cfg.output = _merge(cfg.output, settings["output"], OUTPUT_KEYS)
    if "scheduled" in settings:
        current = dict(cfg.scheduled or {})
        incoming = settings["scheduled"]
        if not isinstance(incoming, dict):
            raise ValueError("settings.scheduled must be an object")
        for key in SCHEDULE_KEYS:
            if key in incoming:
                current[key] = incoming[key]
        cfg.scheduled = current
    cfg.save(config_path, expected_version=baseline_version)

    if isinstance(email, dict):
        if isinstance(email.get("recipients"), list):
            email["recipients"] = [
                {"address": str(row.get("address", "")).strip(),
                 "time": str(row.get("time", "")).strip(),
                 "language": str(row.get("language") or "zh")}
                for row in email["recipients"] if isinstance(row, dict) and row.get("address")
            ]
            email["to"] = [row["address"] for row in email["recipients"]]
        _write(mailer.CFG_PATH, email)

    if hook_updates:
        current = webhooks.load_cfg()
        current.update(hook_updates)
        _write(webhooks.CFG_PATH, current)

    if isinstance(ai, dict):
        _write(ai_summary.CFG_PATH, ai)

    ui = settings.get("ui")
    if isinstance(ui, dict) and ui.get("language") in {"zh", "en", "ru"}:
        _write(_ui_path(config_path), {"language": ui["language"]})
    return {"ok": True, "profile": cfg.profile}
