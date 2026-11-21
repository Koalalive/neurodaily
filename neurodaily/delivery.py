"""Send new report records to each destination and record acknowledged deliveries."""
from __future__ import annotations

import hashlib
import logging
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from . import history, mailer, webhooks
from .digest import DigestResult, render_html_for
from .records import delivery_ids

_LOG = logging.getLogger(__name__)


def _limit(value, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _destination(channel: str, address: str) -> str:
    return channel + ":" + hashlib.sha256(address.encode()).hexdigest()


def _increment(result: DigestResult, destination: str, limits: dict[str, int], total: int | None):
    sent = history.delivered_ids(result.config_profile, destination)
    sections = {key: [] for key in result.sections}
    items, identities = [], set()
    for key, group in result.sections.items():
        for item in group:
            if len(sections[key]) >= limits.get(key, len(group)):
                break
            if total is not None and len(items) >= total:
                break
            ids = delivery_ids(item)
            if not sent.isdisjoint(ids):
                continue
            sections[key].append(item)
            items.append(item)
            identities.update(ids)
    event_key = "on-this-day:" + result.generated_at[:10]
    events = result.on_this_day if event_key not in sent else []
    if events:
        identities.add(event_key)
    if len(items) == len(result.items) and events == result.on_this_day:
        return result, identities
    return replace(result, items=items, sections=sections, on_this_day=events,
                   ai_summary="", ai_summary_meta={}), identities


def deliver_report(result: DigestResult, report_path: str) -> dict:
    """Leave the on-disk report complete and send only each destination's new items."""
    outcomes: dict[str, str] = {}
    email = mailer.load_cfg()
    attach = email.get("attach_report", True)
    subject, html, message = mailer.render_email(result, email)
    mailer.save_last(subject, html, message, report_path if attach else None)
    if email.get("enabled", True) and mailer._password(email):
        paper_cap = (_limit(email.get("summary_papers"), 12)
                     if (email.get("body_mode") or "summary") == "summary"
                     else _limit(email.get("max_papers"), 40))
        limits = {key: _limit(email.get("max_other"), 15) for key in result.sections}
        limits["papers"] = paper_cap
        recipients = email.get("to") or []
        if isinstance(recipients, str):
            recipients = [recipients]
        for index, address in enumerate(dict.fromkeys(recipients), 1):
            destination = _destination("email", address.strip().casefold())
            with history.delivery_lease(result.config_profile, destination) as acquired:
                if not acquired:
                    continue
                subset, sent = _increment(result, destination, limits, None)
                if not sent:
                    continue
                try:
                    subject, html, message = mailer.render_email(subset, email)
                    with TemporaryDirectory(prefix="neurodaily-email-") as directory:
                        attachments = None
                        if attach:
                            if subset is result:
                                attachments = [report_path]
                            else:
                                path = Path(directory) / Path(report_path).name
                                path.write_text(render_html_for(subset), encoding="utf-8")
                                attachments = [str(path)]
                        mailer.send_with_retry(subject, html, message, {**email, "to": [address]}, attachments)
                    history.mark_delivered(result.config_profile, destination, sent)
                    outcomes[f"email {index}"] = "ok"
                except Exception:
                    outcomes[f"email {index}"] = "failed"
                    _LOG.warning("Delivery to email recipient %s failed", index)

    hooks = webhooks.load_cfg()
    for name in ("feishu", "wecom"):
        if not hooks.get(name):
            continue
        destination = _destination(name, hooks[name])
        with history.delivery_lease(result.config_profile, destination) as acquired:
            if not acquired:
                continue
            cap = _limit(hooks.get("max_items"), 8)
            subset, sent = _increment(result, destination, {}, cap)
            if not sent:
                continue
            status = webhooks.send_all(subset, {name: hooks[name], "max_items": cap}).get(name)
            outcomes[name] = "ok" if status == "ok" else "failed"
            if status == "ok":
                history.mark_delivered(result.config_profile, destination, sent)
    return outcomes
