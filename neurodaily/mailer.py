"""Render the daily digest as an email (summary body + full HTML attachment).

Subject template default: 神经病专家的厕所读物-{date} {weekday}
Config: config/email.json (password from ~/.neurodaily_smtp or env).
"""
from __future__ import annotations

import html as _html
import json
import os
import smtplib
import ssl
from datetime import datetime
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "config", "email.json")
LAST_PATH = os.path.join(os.path.expanduser("~"), "neurodaily", "output", "last_email.json")

_WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

DEFAULT_CFG = {
    "enabled": True,
    "smtp_host": "smtp.sjtu.edu.cn",
    "smtp_port": 587,
    "use_ssl": False,
    "smtp_timeout": 120,
    "username": "you@sjtu.edu.cn",
    "from": "you@sjtu.edu.cn",
    "from_name": "NeuroDaily",
    "to": ["you@example.com", "friend@example.com"],
    "password_env": "NEURODAILY_SMTP_PASSWORD",
    "password_file": "~/.neurodaily_smtp",
    "subject_template": "神经病专家的厕所读物-{date} {weekday}",
    "body_mode": "summary",
    "attach_report": True,
    "max_papers": 40,
    "max_other": 15,
    "summary_papers": 12,
    "summary_chars": 420,
    "attach_max_mb": 8,
}


def load_cfg() -> dict:
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def _password(cfg: dict) -> str:
    pw = os.environ.get(cfg.get("password_env", ""), "")
    if pw:
        return pw
    try:
        with open(os.path.expanduser(cfg.get("password_file", "")), encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _esc(s) -> str:
    return _html.escape(str(s or ""))


def _truncate(s: str, n: int) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def _date_parts(result) -> tuple[str, str]:
    raw = str(getattr(result, "generated_at", "") or "")[:10]
    try:
        d = datetime.strptime(raw, "%Y-%m-%d")
    except Exception:
        d = datetime.now()
    return d.strftime("%Y-%m-%d"), _WEEKDAYS[d.weekday()]


def subject_for(result, cfg: dict) -> str:
    date, weekday = _date_parts(result)
    tpl = cfg.get("subject_template") or DEFAULT_CFG["subject_template"]
    try:
        return tpl.format(date=date, weekday=weekday)
    except Exception:
        return f"神经病专家的厕所读物-{date} {weekday}"


def _item_html(it, accent: str, summary_len: int = 320) -> str:
    title = _esc(it.title)
    link = f'<a href="{_esc(it.url)}" style="color:{accent};text-decoration:none">{title}</a>' if it.url else title
    tags = " · ".join(x for x in [it.kind_label, it.source, it.date_display] if x)
    summary = _truncate(it.summary, summary_len)
    return (
        '<div style="padding:9px 0;border-bottom:1px solid #eeeeee">'
        f'<div style="font-weight:600;font-size:15px;line-height:1.4">{link}</div>'
        f'<div style="color:#888;font-size:12px;margin:3px 0 4px">{_esc(tags)}</div>'
        f'<div style="color:#444;font-size:13px;line-height:1.55">{_esc(summary)}</div>'
        '</div>'
    )


def render_email(result, cfg: dict | None = None) -> tuple[str, str, str]:
    cfg = cfg or load_cfg()
    accent = "#0369a1"
    sections = result.sections or {}
    papers_all = sections.get("papers", [])
    industry = sections.get("industry", [])
    trials = sections.get("trials_conferences", [])
    policy = sections.get("policy", [])
    summary_mode = (cfg.get("body_mode") or "summary") == "summary"
    n_papers = int(cfg.get("summary_papers", 12)) if summary_mode else int(cfg.get("max_papers", 40))
    papers = papers_all[:n_papers]
    date, weekday = _date_parts(result)

    parts = [
        '<div style="max-width:680px;margin:0 auto;font-family:-apple-system,Segoe UI,Roboto,'
        'Helvetica,Arial,sans-serif;background:#ffffff;color:#111">'
        '<div style="background:#0b1220;color:#fff;padding:18px 20px;border-radius:8px 8px 0 0">'
        f'<div style="font-size:20px;font-weight:700">NeuroDaily</div>'
        f'<div style="font-size:13px;color:#9fb3c8;margin-top:4px">{date} {weekday} · '
        f'{len(result.items)} 条 · {len(papers_all)} 篇论文</div></div>'
        '<div style="padding:18px 20px;border:1px solid #eeeeee;border-top:none;border-radius:0 0 8px 8px">'
    ]

    otd = getattr(result, "on_this_day", None) or []
    if otd:
        parts.append(f'<h2 style="font-size:16px;color:{accent};margin:6px 0 10px">📅 历史上的今天</h2>')
        for e in otd:
            body = (e.get("body") or e.get("text") or "").strip()
            if summary_mode:
                body = _truncate(body.split("\n\n")[0], int(cfg.get("summary_chars", 420)))
            paras = "".join(
                f'<p style="margin:0 0 8px;color:#333;font-size:13px;line-height:1.7">{_esc(p)}</p>'
                for p in body.split("\n\n") if p.strip()
            )
            parts.append(
                '<div style="padding:10px 0;border-bottom:1px solid #eeeeee">'
                f'<div style="font-weight:700;font-size:15px">{_esc(e.get("title"))}'
                f' <span style="color:#888;font-weight:400;font-size:12px">（{_esc(e.get("year"))}）</span></div>'
                f'<div style="color:#888;font-size:12px;margin:2px 0 6px">{_esc(e.get("kind_label"))} · '
                f'{_esc(e.get("category_label"))}</div>{paras}</div>'
            )

    if papers:
        hint = f"显示前 {len(papers)} 篇" + (f"（共 {len(papers_all)} 篇）" if summary_mode else "")
        parts.append(f'<h2 style="font-size:16px;color:{accent};margin:20px 0 6px">📄 最新论文</h2>'
                     f'<div style="color:#888;font-size:12px;margin-bottom:6px">{hint}</div>')
        parts.extend(_item_html(it, accent) for it in papers)

    if summary_mode:
        counts = [("💊 商业与监管", len(industry)), ("🧪 临床试验与会议", len(trials)),
                  ("🏛️ 政策与新闻", len(policy))]
        line = " · ".join(f"{name} {n} 条" for name, n in counts if n)
        if line:
            parts.append(f'<div style="margin:16px 0;color:#555;font-size:13px">{line}</div>')
    else:
        for title, items in [("💊 商业与监管", industry), ("🧪 临床试验与会议", trials),
                             ("🏛️ 政策与新闻", policy)]:
            if items:
                parts.append(f'<h2 style="font-size:16px;color:{accent};margin:22px 0 6px">{title}</h2>')
                parts.extend(_item_html(it, accent) for it in items[: int(cfg.get("max_other", 15))])

    if result.errors:
        parts.append('<div style="margin-top:16px;color:#b45309;font-size:12px">'
                     + "<br>".join(_esc(e) for e in result.errors[:5]) + "</div>")

    if cfg.get("attach_report", True):
        parts.append('<div style="margin-top:14px;color:#888;font-size:12px">'
                     "完整交互式报告见附件 HTML（若附件缺失则因体积超限）。</div>")
    parts.append(
        '<div style="margin-top:18px;padding-top:12px;border-top:1px solid #eeeeee;color:#999;font-size:11px">'
        "本邮件由 NeuroDaily 自动生成。</div></div></div>"
    )
    html = "".join(parts)

    lines = [f"NeuroDaily {date} {weekday} — {len(result.items)} 条", ""]
    if otd:
        lines.append("== 历史上的今天 ==")
        for e in otd:
            body = (e.get("body") or e.get("text") or "")
            if summary_mode:
                body = _truncate(body.split("\n\n")[0], int(cfg.get("summary_chars", 420)))
            lines += [f"{e.get('year')} {e.get('title')}", body, ""]
    if papers:
        lines.append(f"== 最新论文（前 {len(papers)} 篇，共 {len(papers_all)} 篇）==")
        for it in papers:
            lines.append(f"- {it.title} ({it.source})")
            if it.url:
                lines.append(f"  {it.url}")
        lines.append("")
    lines.append(f"商业/监管 {len(industry)} · 试验/会议 {len(trials)} · 政策/新闻 {len(policy)}")
    text = "\n".join(lines)
    return subject_for(result, cfg), html, text


def _build_message(cfg: dict, subject: str, html: str, text: str,
                   attachments: list[str] | None = None) -> MIMEMultipart:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header(cfg.get("from_name", "NeuroDaily"), "utf-8")), cfg["from"]))
    msg["To"] = ", ".join(cfg["to"])
    msg["Date"] = formatdate(localtime=True)

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(text, "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)

    max_mb = float(cfg.get("attach_max_mb", 8))
    for path in attachments or []:
        try:
            if os.path.getsize(path) > max_mb * 1024 * 1024:
                continue
            with open(path, "rb") as f:
                part = MIMEBase("text", "html")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment",
                            filename=os.path.basename(path))
            msg.attach(part)
        except Exception:
            continue
    return msg


def send(subject: str, html: str, text: str, cfg: dict | None = None,
         attachments: list[str] | None = None) -> None:
    cfg = cfg or load_cfg()
    pw = _password(cfg)
    if not pw:
        raise RuntimeError(
            f"缺少 SMTP 密码：请写入 {cfg.get('password_file')}（chmod 600），"
            f"或设置环境变量 {cfg.get('password_env')}。"
        )
    msg = _build_message(cfg, subject, html, text, attachments)
    host, port = cfg["smtp_host"], int(cfg["smtp_port"])
    timeout = int(cfg.get("smtp_timeout", 120))
    context = ssl.create_default_context()
    if cfg.get("use_ssl"):
        server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
    else:
        server = smtplib.SMTP(host, port, timeout=timeout)
        server.starttls(context=context)
    try:
        server.login(cfg["username"], pw)
        server.sendmail(cfg["from"], cfg["to"], msg.as_string())
    finally:
        try:
            server.quit()
        except Exception:
            pass


def send_with_retry(subject: str, html: str, text: str, cfg: dict | None = None,
                    attachments: list[str] | None = None, attempts: int = 3) -> None:
    import time
    cfg = cfg or load_cfg()
    last = None
    for i in range(attempts):
        try:
            send(subject, html, text, cfg, attachments)
            return
        except Exception as exc:
            last = exc
            if i < attempts - 1:
                time.sleep(3 * (i + 1))
    raise last


def send_digest(result, cfg: dict | None = None,
                attachments: list[str] | None = None) -> bool:
    cfg = cfg or load_cfg()
    if not cfg.get("enabled", True) or not _password(cfg):
        return False
    subject, html, text = render_email(result, cfg)
    send_with_retry(subject, html, text, cfg, attachments)
    return True


def send_test(cfg: dict | None = None) -> None:
    cfg = cfg or load_cfg()
    subject = "NeuroDaily 邮件测试"
    html = ('<div style="font-family:-apple-system,sans-serif;padding:16px">'
            '<h2 style="color:#0369a1">NeuroDaily 邮件配置成功 ✅</h2>'
            '<p>如果你收到这封邮件，说明 SMTP 与收件人配置可用。</p></div>')
    send_with_retry(subject, html, "NeuroDaily 邮件配置成功", cfg)


def save_last(subject: str, html: str, text: str, attachment: str | None = None) -> None:
    """Remember the last rendered email so `mail --send-latest` can resend it."""
    try:
        os.makedirs(os.path.dirname(LAST_PATH), exist_ok=True)
        with open(LAST_PATH, "w", encoding="utf-8") as f:
            json.dump({"subject": subject, "html": html, "text": text,
                       "attachment": attachment or ""}, f, ensure_ascii=False)
    except Exception:
        pass


def load_last() -> dict | None:
    try:
        with open(LAST_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
