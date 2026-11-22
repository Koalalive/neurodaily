"""Send new report records to each destination and record acknowledged deliveries."""
from __future__ import annotations

import hashlib
import logging
import smtplib
from dataclasses import replace

from . import delivery_receipts, history, mailer, webhooks
from .digest import DigestResult
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
    return replace(result, items=items, sections=sections, on_this_day=events), identities


def _send_email(subset: DigestResult, result: DigestResult, report_path: str, email: dict,
                address: str, *, attempts: int) -> None:
    subject, html, message = mailer.render_email(subset, email)
    attachments = None
    if email.get("attach_report", True):
        # Always attach the fully rendered report, including AI summary and
        # the geography map. A limited email body must not downgrade it.
        attachments = [report_path]
    mailer.send_with_retry(subject, html, message, {**email, "to": [address]}, attachments,
                           attempts=attempts)


def _email_error(exc: Exception) -> str:
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "SMTP 服务器拒绝该收件人，请核对收件地址。"
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "SMTP 服务器拒绝登录，请核对账号和授权码。"
    if isinstance(exc, (smtplib.SMTPDataError, smtplib.SMTPSenderRefused)):
        return "SMTP 服务器拒绝接受邮件，请检查邮件服务配置。"
    return "未能确认 SMTP 服务器接受邮件，请检查邮件配置和网络。"


def list_receipts(task_id: str) -> list[dict]:
    """Return sanitized per-destination delivery receipts for a task."""
    return delivery_receipts.list_receipts(task_id)


def retry_delivery(result: DigestResult, report_path: str, task_id: str, destination: str) -> dict:
    """Retry a failed receipt whose destination still matches the current configuration."""
    deliver_report(result, report_path, task_id=task_id, retry_destination=destination)
    for receipt in list_receipts(task_id):
        if receipt["destination"] == destination:
            return receipt
    raise ValueError("该投递回执已移除。")


def deliver_report(result: DigestResult, report_path: str, *, task_id: str | None = None,
                   retry_destination: str | None = None) -> dict:
    """Send each destination's new items and record its task-scoped delivery status."""
    retrying = retry_destination is not None
    if retrying and not task_id:
        raise ValueError("重试投递需要任务编号。")
    profile = result.config_profile
    outcomes: dict[str, str] = {}
    expected_attempts = None
    email = mailer.load_cfg()
    hooks = webhooks.load_cfg()
    targets: list[tuple[str, str, str, str]] = []
    if email.get("enabled", True):
        recipients = email.get("to") or []
        if isinstance(recipients, str):
            recipients = [recipients]
        for index, address in enumerate(dict.fromkeys(recipients), 1):
            destination = _destination("email", address.strip().casefold())
            targets.append((destination, "email", f"email {index}", address))
    for channel in ("feishu", "wecom"):
        if address := hooks.get(channel):
            targets.append((_destination(channel, address), channel, channel, address))

    if retrying:
        receipt = next((row for row in list_receipts(task_id)
                        if row["destination"] == retry_destination), None)
        if not receipt or receipt["status"] != "failed":
            raise ValueError("只能重试失败的投递目标。")
        expected_attempts = receipt["attempts"]
        targets = [target for target in targets if target[0] == retry_destination][:1]
        if not targets:
            raise ValueError("该投递目标已从当前设置中移除或变更。")
    else:
        if task_id is not None and targets:
            delivery_receipts.prepare(task_id, profile, [(destination, channel, label)
                                                       for destination, channel, label, _ in targets])
        subject, html, message = mailer.render_email(result, email)
        attachment = report_path if email.get("attach_report", True) else None
        mailer.save_last(subject, html, message, attachment)

    expected = "failed" if retrying else "pending"
    email_limits = {key: _limit(email.get("max_other"), 15) for key in result.sections}
    if (email.get("body_mode") or "summary") == "summary":
        email_limits["papers"] = _limit(email.get("summary_papers"), 12)
    else:
        email_limits["papers"] = _limit(email.get("max_papers"), 40)
    hook_cap = _limit(hooks.get("max_items"), 8)
    for destination, channel, label, address in targets:
        is_email = channel == "email"
        has_password = not is_email or bool(mailer._password(email))
        if task_id is None and not has_password:
            continue
        if task_id is not None and not delivery_receipts.transition(
            task_id, profile, destination, expected, "checking", expected_attempts=expected_attempts
        ):
            if retrying:
                raise ValueError("该投递回执已更新，请刷新后查看。")
            continue
        with history.delivery_lease(profile, destination) as acquired:
            if not acquired:
                error = "该投递目标正在处理，请稍后重试。"
                if task_id is not None:
                    delivery_receipts.transition(task_id, profile, destination, "checking", "failed",
                                                 error=error)
                    outcomes[label] = "failed"
                if retrying:
                    raise ValueError(error)
                continue
            subset, sent = _increment(result, destination, email_limits if is_email else {},
                                      None if is_email else hook_cap)
            if task_id is not None:
                status = "sending"
                error = None
                if not sent:
                    status = "no_new"
                elif not has_password:
                    status = "failed"
                    error = "请先配置 SMTP 授权码。"
                if not delivery_receipts.transition(task_id, profile, destination, "checking",
                                                    status, error=error):
                    if retrying:
                        raise ValueError("该投递回执已更新，请刷新后查看。")
                    continue
                if status == "failed":
                    outcomes[label] = "failed"
                    continue
            if not sent:
                continue

            error = None
            if is_email:
                try:
                    _send_email(subset, result, report_path, email, address,
                                attempts=1 if task_id is not None else 3)
                except Exception as exc:
                    error = _email_error(exc)
            else:
                try:
                    acknowledged = webhooks.send_all(subset, {channel: address, "max_items": hook_cap})
                    if acknowledged.get(channel) != "ok":
                        error = "推送服务未确认接收，请检查机器人配置和网络。"
                except Exception:
                    error = "推送服务未确认接收，请检查机器人配置和网络。"
            if error:
                if task_id is not None:
                    delivery_receipts.transition(task_id, profile, destination, "sending", "failed",
                                                 error=error)
                outcomes[label] = "failed"
                _LOG.warning("Delivery to %s failed", label)
            else:
                if task_id is not None:
                    delivery_receipts.transition(task_id, profile, destination, "sending", "accepted",
                                                 sent=sent)
                else:
                    history.mark_delivered(profile, destination, sent)
                outcomes[label] = "ok"
    return outcomes
