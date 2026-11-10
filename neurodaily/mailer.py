"""Render the daily digest as an HTML email and send it via SMTP.

Config: config/email.json (created from config/email.example.json).
Password: env NEURODAILY_SMTP_PASSWORD, or a 0600 file (default ~/.neurodaily_smtp).

    neurodaily mail --preview /tmp/mail.html   # render only, no send
    neurodaily mail --test                     # send a tiny test message
    neurodaily mail --send                     # send today's latest digest

The daily 08:00 `neurodaily run` also calls send_digest() automatically.
"""
from __future__ import annotations

import html as _html
import json
import os
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "config", "email.json")

DEFAULT_CFG = {
    "enabled": True,
    "smtp_host": "smtp.sjtu.edu.cn",
    "smtp_port": 465,
    "use_ssl": True,
    "username": "you@sjtu.edu.cn",
    "from": "you@sjtu.edu.cn",
    "from_name": "NeuroDaily",
    "to": ["you@example.com"],
    "password_env": "NEURODAILY_SMTP_PASSWORD",
    "password_file": "~/.neurodaily_smtp",
    "max_papers": 40,
    "max_other": 15,
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
    path = os.path.expanduser(cfg.get("password_file", ""))
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _esc(s) -> str:
    return _html.escape(str(s or ""))


def _truncate(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _item_html(it, accent: str, summary_len: int = 320) -> str:
    title = _esc(it.title)
    link = f'<a href="{_esc(it.url)}" style="color:{accent};text-decoration:none">{title}</a>' if it.url else title
    tags = " · ".join(x for x in [it.kind_label, it.source, it.date_display] if x)
    summary = _truncate(it.summary, summary_len)
    return (
        '<div style="padding:10px 0;border-bottom:1px solid #eeeeee">'
        f'<div style="font-weight:600;font-size:15px;line-height:1.4">{link}</div>'
        f'<div style="color:#888;font-size:12px;margin:3px 0 5px">{_esc(tags)}</div>'
        f'<div style="color:#444;font-size:13px;line-height:1.55">{_esc(summary)}</div>'
        '</div>'
    )


def render_email(result) -> tuple[str, str, str]:
    cfg = load_cfg()
    accent = "#0369a1"
    papers = result.sections.get("papers", [])[: cfg["max_papers"]]
    industry = result.sections.get("industry", [])[: cfg["max_other"]]
    trials = result.sections.get("trials_conferences", [])[: cfg["max_other"]]
    policy = result.sections.get("policy", [])[: cfg["max_other"]]

    parts = []
    parts.append(
        '<div style="max-width:680px;margin:0 auto;font-family:-apple-system,Segoe UI,Roboto,'
        'Helvetica,Arial,sans-serif;background:#ffffff;color:#111">'
        f'<div style="background:#0b1220;color:#fff;padding:18px 20px;border-radius:8px 8px 0 0">'
        f'<div style="font-size:20px;font-weight:700">NeuroDaily</div>'
        f'<div style="font-size:13px;color:#9fb3c8;margin-top:4px">{_esc(result.generated_at[:19].replace("T", " "))}'
        f' · {len(result.items)} 条 · {len(result.sections.get("papers", []))} 篇论文</div>'
        '</div><div style="padding:18px 20px;border:1px solid #eeeeee;border-top:none;border-radius:0 0 8px 8px">'
    )

    otd = getattr(result, "on_this_day", None) or []
    if otd:
        parts.append(f'<h2 style="font-size:16px;color:{accent};margin:6px 0 10px">📅 历史上的今天</h2>')
        for e in otd:
            paras = "".join(
                f'<p style="margin:0 0 8px;color:#333;font-size:13px;line-height:1.7">{_esc(p)}</p>'
                for p in (e.get("body") or e.get("text") or "").split("\n\n") if p.strip()
            )
            parts.append(
                '<div style="padding:10px 0;border-bottom:1px solid #eeeeee">'
                f'<div style="font-weight:700;font-size:15px">{_esc(e.get("title"))}'
                f' <span style="color:#888;font-weight:400;font-size:12px">（{_esc(e.get("year"))}）</span></div>'
                f'<div style="color:#888;font-size:12px;margin:2px 0 6px">{_esc(e.get("kind_label"))} · '
                f'{_esc(e.get("category_label"))}</div>{paras}</div>'
            )

    def section(title, items, hint=""):
        if not items:
            return
        parts.append(f'<h2 style="font-size:16px;color:{accent};margin:22px 0 6px">{title}</h2>')
        if hint:
            parts.append(f'<div style="color:#888;font-size:12px;margin-bottom:6px">{hint}</div>')
        parts.extend(_item_html(it, accent) for it in items)

    section("📄 最新论文", papers, f"显示前 {len(papers)} 篇（共 {len(result.sections.get('papers', []))} 篇）")
    section("💊 商业与监管", industry)
    section("🧪 临床试验与会议", trials)
    section("🏛️ 政策与新闻", policy)

    if result.errors:
        parts.append('<div style="margin-top:18px;color:#b45309;font-size:12px">'
                     + "<br>".join(_esc(e) for e in result.errors[:5]) + "</div>")

    parts.append(
        '<div style="margin-top:24px;padding-top:12px;border-top:1px solid #eeeeee;color:#999;font-size:11px">'
        "本邮件由 NeuroDaily 自动生成。完整交互式报告见本机 output/ 目录。"
        "</div></div></div>"
    )
    html = "".join(parts)

    # plain text alternative
    lines = [f"NeuroDaily {result.generated_at[:19].replace('T', ' ')} — {len(result.items)} 条", ""]
    if otd:
        lines.append("== 历史上的今天 ==")
        for e in otd:
            lines.append(f"{e.get('year')} {e.get('title')}")
            lines.append((e.get("body") or e.get("text") or "")[:1200])
            lines.append("")
    for name, items in [("最新论文", papers), ("商业与监管", industry),
                        ("临床试验与会议", trials), ("政策与新闻", policy)]:
        if items:
            lines.append(f"== {name} ==")
            for it in items:
                lines.append(f"- {it.title} ({it.source}{', ' + it.date_display if it.date_display else ''})")
                if it.url:
                    lines.append(f"  {it.url}")
            lines.append("")
    text = "\n".join(lines)

    day = result.generated_at[:10]
    subject = f"NeuroDaily {day} · {len(result.items)} 条 · {len(result.sections.get('papers', []))} 篇论文"
    return subject, html, text


def _build_message(cfg: dict, subject: str, html: str, text: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header(cfg.get("from_name", "NeuroDaily"), "utf-8")), cfg["from"]))
    msg["To"] = ", ".join(cfg["to"])
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def send(subject: str, html: str, text: str, cfg: dict | None = None) -> None:
    cfg = cfg or load_cfg()
    pw = _password(cfg)
    if not pw:
        raise RuntimeError(
            f"缺少 SMTP 密码：请写入 {cfg.get('password_file')}（chmod 600），"
            f"或设置环境变量 {cfg.get('password_env')}。"
        )
    msg = _build_message(cfg, subject, html, text)
    host, port = cfg["smtp_host"], int(cfg["smtp_port"])
    context = ssl.create_default_context()
    if cfg.get("use_ssl"):
        server = smtplib.SMTP_SSL(host, port, timeout=30, context=context)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        server.starttls(context=context)
    try:
        server.login(cfg["username"], pw)
        server.sendmail(cfg["from"], cfg["to"], msg.as_string())
    finally:
        try:
            server.quit()
        except Exception:
            pass


def send_digest(result, cfg: dict | None = None) -> bool:
    cfg = cfg or load_cfg()
    if not cfg.get("enabled", True):
        return False
    if not _password(cfg):
        return False
    subject, html, text = render_email(result)
    send(subject, html, text, cfg)
    return True


def send_test(cfg: dict | None = None) -> None:
    cfg = cfg or load_cfg()
    subject = "NeuroDaily 邮件测试"
    html = ('<div style="font-family:-apple-system,sans-serif;padding:16px">'
            '<h2 style="color:#0369a1">NeuroDaily 邮件配置成功 ✅</h2>'
            '<p>如果你收到这封邮件，说明 SMTP 与收件人配置可用。</p></div>')
    send(subject, html, "NeuroDaily 邮件配置成功", cfg)
