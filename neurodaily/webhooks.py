"""Push the daily digest to Feishu / WeCom group bots.

Config: config/webhooks.json (gitignored)
    {"feishu": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
     "wecom": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
     "max_items": 8}
"""
from __future__ import annotations

import json
import os

import httpx

ROOT = os.environ.get("NEURODAILY_HOME") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "config", "webhooks.json")

DEFAULT_CFG = {"feishu": "", "wecom": "", "max_items": 8}


def load_cfg() -> dict:
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def build_text(result, max_items: int = 8) -> str:
    date = str(getattr(result, "generated_at", ""))[:10]
    papers = (result.sections or {}).get("papers", [])
    lines = [f"NeuroDaily {date} · {len(result.items)} 条 · {len(papers)} 篇论文"]
    otd = getattr(result, "on_this_day", None) or []
    if otd:
        e = otd[0]
        lines.append(f"📅 历史上的今天：{e.get('title')}（{e.get('year')}）")
    if papers:
        lines.append("📄 今日精选：")
        for i, it in enumerate(papers[:max_items], 1):
            line = f"{i}. {it.title}"
            if it.url:
                line += f"  {it.url}"
            lines.append(line)
    other = {k: len(v) for k, v in (result.sections or {}).items() if k != "papers" and v}
    if other:
        lines.append("其他：" + " · ".join(f"{k} {v}" for k, v in other.items()))
    return "\n".join(lines)


def send_feishu(url: str, text: str) -> None:
    r = httpx.post(url, json={"msg_type": "text", "content": {"text": text}}, timeout=15)
    r.raise_for_status()


def send_wecom(url: str, text: str) -> None:
    r = httpx.post(url, json={"msgtype": "text", "text": {"content": text}}, timeout=15)
    r.raise_for_status()


def send_all(result, cfg: dict | None = None) -> dict:
    cfg = cfg or load_cfg()
    text = build_text(result, int(cfg.get("max_items", 8)))
    out = {}
    if cfg.get("feishu"):
        try:
            send_feishu(cfg["feishu"], text)
            out["feishu"] = "ok"
        except Exception as exc:
            out["feishu"] = f"failed: {exc}"
    if cfg.get("wecom"):
        try:
            send_wecom(cfg["wecom"], text)
            out["wecom"] = "ok"
        except Exception as exc:
            out["wecom"] = f"failed: {exc}"
    return out


def send_test(cfg: dict | None = None) -> dict:
    cfg = cfg or load_cfg()
    text = "NeuroDaily webhook 测试成功 ✅"
    out = {}
    if cfg.get("feishu"):
        send_feishu(cfg["feishu"], text)
        out["feishu"] = "ok"
    if cfg.get("wecom"):
        send_wecom(cfg["wecom"], text)
        out["wecom"] = "ok"
    return out
