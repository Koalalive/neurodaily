"""Push the daily digest to Feishu / WeCom group bots.

Config: config/webhooks.json (gitignored)
    {"feishu": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
     "wecom": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
     "max_items": 8}
"""
from __future__ import annotations

import json
import os
from urllib.parse import urlsplit

import httpx

from .security import external_url, validate_http_url
from .sources.http import _SourceTransport

ROOT = os.environ.get("NEURODAILY_HOME") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "config", "webhooks.json")

DEFAULT_CFG = {"feishu": "", "wecom": "", "max_items": 8}
_PROVIDERS = ("feishu", "wecom")
_CONNECTION = httpx.Client(transport=_SourceTransport(allow_private=False,
                                                      limits=httpx.Limits(max_keepalive_connections=0)),
                           timeout=15, follow_redirects=False, trust_env=False)


def load_cfg() -> dict:
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def public_settings(cfg: dict) -> dict:
    return {**{f"{key}_configured": bool(cfg.get(key)) for key in _PROVIDERS},
            "max_items": _item_limit(cfg)}


def _item_limit(cfg: dict) -> int:
    try:
        return max(1, min(100, int(cfg.get("max_items", DEFAULT_CFG["max_items"]))))
    except (TypeError, ValueError, OverflowError):
        return DEFAULT_CFG["max_items"]


def _url(value, *, resolve=False) -> str:
    url = external_url(value)
    if not url or urlsplit(url).scheme != "https":
        raise ValueError("Webhook 必须使用有效的 HTTPS 地址。")
    try:
        return validate_http_url(url, allow_private=False, resolve=resolve)
    except ValueError:
        raise ValueError("Webhook 地址无法解析或指向受限制的网络。") from None


def normalize_updates(incoming: dict, *, allow_clear: bool = True) -> dict:
    updates = {}
    for key in _PROVIDERS:
        value = incoming.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            raise ValueError("Webhook 地址必须为文本。")
        if value.strip():
            updates[key] = _url(value, resolve=True)
        elif allow_clear:
            updates[key] = ""
    if "max_items" in incoming:
        value = incoming["max_items"]
        if type(value) is not int or value < 1 or value > 100:
            raise ValueError("Webhook 推送条目数必须在 1 到 100 之间。")
        updates["max_items"] = value
    return updates


def _post(url: str, payload: dict) -> dict:
    try:
        response = _CONNECTION.post(_url(url), json=payload)
        response.raise_for_status()
        reply = response.json()
    except (httpx.HTTPError, httpx.InvalidURL, ValueError):
        raise ValueError("Webhook 推送失败，请检查已保存的地址和网络。") from None
    if not isinstance(reply, dict):
        raise ValueError("消息服务返回了无效的响应。")
    return reply


def build_text(result, max_items: int = 8) -> str:
    date = str(getattr(result, "generated_at", ""))[:10]
    papers = (result.sections or {}).get("papers", [])
    lines = [f"NeuroDaily {date} · {len(result.items)} 条 · {len(papers)} 篇论文"]
    otd = getattr(result, "on_this_day", None) or []
    if otd:
        e = otd[0]
        lines.append(f"◷ 历史上的今天：{e.get('title')}（{e.get('year')}）")
    if papers:
        lines.append("▤ 今日精选：")
        for i, it in enumerate(papers[:max_items], 1):
            line = f"{i}. {it.title}"
            if url := external_url(it.url):
                line += f"  {url}"
            lines.append(line)
    other = {k: len(v) for k, v in (result.sections or {}).items() if k != "papers" and v}
    if other:
        lines.append("其他：" + " · ".join(f"{k} {v}" for k, v in other.items()))
        remaining = max(0, max_items - len(papers))
        other_items = [item for key, items in (result.sections or {}).items()
                       if key != "papers" for item in items]
        for item in other_items[:remaining]:
            url = external_url(item.url)
            lines.append(f"- {item.title}" + (f"  {url}" if url else ""))
    return "\n".join(lines)


def send_feishu(url: str, text: str) -> None:
    reply = _post(url, {"msg_type": "text", "content": {"text": text}})
    if reply.get("code", reply.get("StatusCode")) != 0:
        raise ValueError("Feishu did not acknowledge delivery")


def send_wecom(url: str, text: str) -> None:
    reply = _post(url, {"msgtype": "text", "text": {"content": text}})
    if reply.get("errcode") != 0:
        raise ValueError("WeCom did not acknowledge delivery")


def send_all(result, cfg: dict | None = None) -> dict:
    cfg = load_cfg() if cfg is None else cfg
    text = build_text(result, _item_limit(cfg))
    out = {}
    if cfg.get("feishu"):
        try:
            send_feishu(cfg["feishu"], text)
            out["feishu"] = "ok"
        except ValueError:
            out["feishu"] = "failed: Webhook push failed"
    if cfg.get("wecom"):
        try:
            send_wecom(cfg["wecom"], text)
            out["wecom"] = "ok"
        except ValueError:
            out["wecom"] = "failed: Webhook push failed"
    return out


def send_test(cfg: dict | None = None) -> dict:
    cfg = load_cfg() if cfg is None else cfg
    text = "NeuroDaily webhook 测试成功 ✓"
    out = {}
    if cfg.get("feishu"):
        send_feishu(cfg["feishu"], text)
        out["feishu"] = "ok"
    if cfg.get("wecom"):
        send_wecom(cfg["wecom"], text)
        out["wecom"] = "ok"
    return out
