"""Optional AI daily overview ("摘要模式").

The user supplies an OpenAI-compatible API key (DeepSeek by default). Once per
day we ask the model to summarize the day's papers, clinical/regulatory news,
industry/VC items and notable events. The result is cached so a run does not
pay twice, and any failure just leaves the report unchanged.

Config: config/ai_summary.json (gitignored)
    {"enabled": true, "base_url": "https://api.deepseek.com/v1",
     "model": "deepseek-chat", "api_key_env": "NEURODAILY_LLM_API_KEY",
     "api_key_file": "~/.neurodaily_llm", "max_papers": 30, "max_other": 8}
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "config", "ai_summary.json")

DEFAULT_CFG = {
    "enabled": True,
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "api_key_env": "NEURODAILY_LLM_API_KEY",
    "api_key_file": "~/.neurodaily_llm",
    "max_papers": 30,
    "max_other": 8,
    "max_input_chars": 8000,
}

PROMPT_VERSION = 2

SYSTEM_PROMPT = (
    "你是神经科学与生物医药领域的资深情报分析师。仅依据用户提供的今日抓取条目，"
    "写一篇约 900 字的中文日报摘要。结构固定为四段："
    "一、今日研究进展；二、临床与监管；三、产业与创投；四、值得关注的大事件。"
    "要求：不得编造材料中没有的日期、数字、机构或结论；材料不足时明确写“今日材料有限”。"
    "语言专业、克制，不要营销腔，不要使用 Markdown 标题符号。"
)


def load_cfg() -> dict:
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def api_key(cfg: dict | None = None) -> str:
    cfg = cfg or load_cfg()
    key = os.environ.get(cfg.get("api_key_env", ""), "")
    if key:
        return key
    try:
        with open(os.path.expanduser(cfg.get("api_key_file", "")), encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _truncate(s: str, n: int) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def build_text(result, cfg: dict | None = None) -> str:
    cfg = cfg or load_cfg()
    sec = result.sections or {}
    papers = sec.get("papers", [])
    industry = sec.get("industry", [])
    trials = sec.get("trials_conferences", [])
    policy = sec.get("policy", [])

    lines = [
        f"日期：{str(getattr(result, 'generated_at', ''))[:10]}",
        f"抓取总量：{len(result.items)} 条；论文 {len(papers)}；产业/创投 {len(industry)}；"
        f"临床试验 {len(trials)}；政策/新闻 {len(policy)}",
        "",
    ]

    def block(title, items, limit, n=200):
        if not items:
            return
        lines.append(f"【{title}】")
        for i, it in enumerate(items[:limit], 1):
            tag = f"（{it.source}{'，' + it.date_display if it.date_display else ''}）"
            lines.append(f"{i}. {it.title}{tag} — {_truncate(it.summary, n)}")
        lines.append("")

    block("论文", papers, int(cfg.get("max_papers", 30)))
    block("产业与创投", industry, int(cfg.get("max_other", 8)))
    block("临床试验", trials, int(cfg.get("max_other", 8)))
    block("政策与新闻", policy, int(cfg.get("max_other", 8)))

    otd = getattr(result, "on_this_day", None) or []
    if otd:
        e = otd[0]
        body = (e.get("body") or e.get("text") or "").replace("\n", " ")
        lines.append(f"【历史上的今天】{e.get('title')}（{e.get('year')}）— {_truncate(body, 300)}")

    text = "\n".join(lines)
    max_chars = int(cfg.get("max_input_chars", 8000))
    return text[:max_chars]


def _fingerprint(result) -> str:
    parts = [f"v{PROMPT_VERSION}", str(getattr(result, "generated_at", ""))[:10]]
    for it in (getattr(result, "items", []) or []):
        parts.append(it.url or it.title)
    return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()[:12]


def _cache_dir(result) -> str:
    try:
        outdir = result.config.output_dir()
    except Exception:
        outdir = os.path.join(ROOT, "output")
    return os.path.join(outdir, "ai_summary")


def _cache_path(result) -> str:
    day = str(getattr(result, "generated_at", ""))[:10] or datetime.now().strftime("%Y-%m-%d")
    return os.path.join(_cache_dir(result), f"{day}_{_fingerprint(result)}.json")


def _read_cache(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return (json.load(f).get("text") or "").strip()
    except Exception:
        return ""


def _write_cache(path: str, text: str, model: str) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"text": text, "model": model,
                       "generated_at": datetime.now().isoformat()},
                      f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _call_llm(text: str, cfg: dict, key: str, base_url: str, model: str) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    last = None
    for attempt in range(3):
        try:
            r = httpx.post(
                url,
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": model,
                    "temperature": 0.4,
                    "max_tokens": 1600,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": text},
                    ],
                },
                timeout=120,
            )
            r.raise_for_status()
            out = (r.json()["choices"][0]["message"]["content"] or "").strip()
            if len(out) < 120:
                raise ValueError("summary too short")
            return out
        except Exception as exc:
            last = exc
            import time
            time.sleep(2 * (attempt + 1))
    raise last


def generate(result, cfg: dict | None = None, force: bool = False,
             api_key_override: str | None = None, base_url: str | None = None,
             model: str | None = None) -> str:
    cfg = cfg or load_cfg()
    if not cfg.get("enabled", True):
        return ""
    key = api_key_override or api_key(cfg)
    if not key:
        raise RuntimeError("缺少 AI API key：请写入 ~/.neurodaily_llm（chmod 600）"
                           "或设置 NEURODAILY_LLM_API_KEY。")
    path = _cache_path(result)
    if not force:
        cached = _read_cache(path)
        if cached:
            return cached

    text = build_text(result, cfg)
    out = _call_llm(text, cfg, key,
                    base_url or cfg.get("base_url", DEFAULT_CFG["base_url"]),
                    model or cfg.get("model", DEFAULT_CFG["model"]))
    _write_cache(path, out, model or cfg.get("model", DEFAULT_CFG["model"]))
    return out
