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
import re
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
    "max_input_chars": 16000,
}

PROMPT_VERSION = 7
MIN_SUMMARY_LINKS = 3

SYSTEM_PROMPT = (
    "你是神经科学与生物医药领域的资深情报分析师。仅依据用户提供的今日抓取条目，"
    "写一篇约 900 字的中文日报摘要。结构固定为四段："
    "一、今日研究进展；二、临床与监管；三、产业与创投；四、值得关注的大事件。"
    "要求：不得编造材料中没有的日期、数字、机构或结论；材料不足时明确写“今日材料有限”。"
    "语言专业、克制，不要营销腔，不要使用 Markdown 标题符号。"
    "材料中每个条目以 R1、R2… 编号开头；提到某条目时，用 Markdown 行内链接引用其编号："
    "[具体词句](R1)。只可使用材料中出现的编号，不得编造；没有编号的条目不链接。"
    "至少为 6 个不同条目加上这样的行内链接，链接文字要具体（如论文结论、药物名、试验名），"
    "不要只写“这篇论文”“该研究”。不要单独列出参考文献，也不要输出裸 URL。"
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


def build_context(result, cfg: dict | None = None) -> tuple[str, dict]:
    """Return (prompt text, refs) where refs maps R# -> {url,title,journal}."""
    cfg = cfg or load_cfg()
    sec = result.sections or {}
    papers = sec.get("papers", [])
    industry = sec.get("industry", [])
    trials = sec.get("trials_conferences", [])
    policy = sec.get("policy", [])
    refs: dict[str, dict] = {}
    counter = [0]

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
        for it in items[:limit]:
            tag = f"（{it.source}{'，' + it.date_display if it.date_display else ''}）"
            url = getattr(it, "url", "") or ""
            if url:
                counter[0] += 1
                rid = f"R{counter[0]}"
                extra = getattr(it, "extra", {}) or {}
                refs[rid] = {
                    "url": url,
                    "title": it.title,
                    "journal": (extra.get("journal") if isinstance(extra, dict) else "") or it.source,
                }
                prefix = rid
            else:
                prefix = "-"
            suffix = f" | url: {url}" if url else ""
            lines.append(f"{prefix}. {it.title}{tag} — {_truncate(it.summary, n)}{suffix}")
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
    max_chars = int(cfg.get("max_input_chars", 16000))
    return text[:max_chars], refs


def build_text(result, cfg: dict | None = None) -> str:
    return build_context(result, cfg)[0]


def _strip_links(text: str) -> str:
    text = text or ""
    def repl(m):
        label = m.group(1)
        prev = text[max(0, m.start() - 40):m.start()]
        return "" if label in prev else label
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", repl, text)


def _extract_links(text: str, refs: dict, cfg: dict, key: str,
                   base_url: str, model: str) -> list[dict]:
    if not refs:
        return []
    listing = "\n".join(f'{rid}. {v.get("title", "")}' for rid, v in refs.items())
    prompt = (
        "From the Text, choose 8-15 specific phrases that mention the referenced works. "
        "Each phrase MUST be an exact substring of Text (copy verbatim), 6-40 characters, "
        "and must name the work's topic, journal, drug, trial or result — not a generic word. "
        'Return ONLY a JSON array of {"phrase":"...","ref":"R1"} objects.\n\n'
        "References:\n" + listing + "\n\nText:\n" + text
    )
    r = httpx.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": model,
            "temperature": 0.1,
            "max_tokens": 1200,
            "messages": [
                {"role": "system", "content": "Return JSON only."},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=90,
    )
    r.raise_for_status()
    raw = (r.json()["choices"][0]["message"]["content"] or "").strip()
    m = re.search(r"\[[\s\S]*\]", raw)
    arr = json.loads(m.group(0)) if m else []
    out = []
    for it in arr if isinstance(arr, list) else []:
        phrase = str(it.get("phrase", "")).strip()
        rid = str(it.get("ref", "")).strip()
        if rid in refs and len(phrase) >= 4 and phrase in text:
            out.append({"phrase": phrase, "ref": rid})
    return out[:15]


def _apply_links(text: str, links: list[dict], refs: dict) -> str:
    used = set()
    for item in sorted(links, key=lambda x: -len(x["phrase"])):
        phrase, rid = item["phrase"], item["ref"]
        if phrase in used or phrase not in text:
            continue
        text = text.replace(phrase, f"[{phrase}]({rid})", 1)
        used.add(phrase)
    return text


def _clean_summary(text: str) -> str:
    """Remove empty/unlinked parentheses and stray citation markers."""
    text = text or ""
    # parentheses that only wrap a markdown link -> keep the link
    text = re.sub(r"[（(]\s*(\[[^\]]+\]\(R\d+\))\s*[)）]", r"\1", text)
    # empty parentheses
    text = re.sub(r"[（(]\s*[)）]", "", text)
    # bare citation markers
    text = re.sub(r"(?<!\])[（(]\s*R\d+\s*[)）]", "", text)
    text = re.sub(r"\[\s*R\d+\s*\]", "", text)
    # strip parentheses around citation-like phrases (no punctuation inside)
    def _paren(m):
        inner = m.group(1).strip()
        if "]" in inner or "http" in inner:
            return m.group(0)
        if len(inner) >= 4 and not re.search(r"[，。；：、,.;:!?！？]", inner):
            return inner
        return m.group(0)
    text = re.sub(r"[（(]([^（）()]{4,80})[)）]", _paren, text)
    return text.replace("**", "")


def _count_links(text: str) -> int:
    return len(re.findall(r"\]\(R\d+\)", text or ""))


_STOPWORDS = {
    "the", "with", "from", "this", "that", "study", "brain", "neural", "human",
    "mice", "mouse", "rats", "cell", "cells", "disease", "patients", "effect",
    "effects", "review", "trial", "clinical", "results", "using", "after",
}


def _entity_fallback(text: str, refs: dict, limit: int = 6) -> str:
    """Link journal names / distinctive title tokens that literally occur in the text."""
    n = 0
    for rid, v in refs.items():
        title = v.get("title", "") or ""
        cands = [v.get("journal", "") or ""]
        cands += re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", title)
        for cand in cands:
            cand = (cand or "").strip()
            if len(cand) < 4 or cand.lower() in _STOPWORDS:
                continue
            if cand in text and f"[{cand}](" not in text:
                text = text.replace(cand, f"[{cand}]({rid})", 1)
                n += 1
                break
        if n >= limit:
            break
    return text


def _append_sources(text: str, refs: dict, need: int) -> str:
    """Guarantee clickable links even when the model refuses to cooperate."""
    if need <= 0 or not refs:
        return text
    picks = list(refs.items())[:need]
    links = "、".join(f'[{(v.get("title") or rid)[:60]}]({rid})' for rid, v in picks)
    return text.rstrip() + "\n\n来源：" + links + "。"


def _journal_fallback(text: str, refs: dict) -> str:
    n = 0
    for rid, v in refs.items():
        j = (v.get("journal") or "").strip()
        if len(j) >= 4 and j in text and f"[{j}](" not in text:
            text = text.replace(j, f"[{j}]({rid})", 1)
            n += 1
            if n >= 3:
                break
    return text


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


def _read_cache(path: str) -> tuple[str, dict]:
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return (d.get("text") or "").strip(), (d.get("refs") or {})
    except Exception:
        return "", {}


def _write_cache(path: str, text: str, model: str, refs: dict | None = None) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"text": text, "model": model, "refs": refs or {},
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
    cached_text, cached_refs = _read_cache(path)
    if not force and cached_text:
        result.ai_summary_refs = cached_refs
        return cached_text

    base = base_url or cfg.get("base_url", DEFAULT_CFG["base_url"])
    mdl = model or cfg.get("model", DEFAULT_CFG["model"])
    text, refs = build_context(result, cfg)
    out = _call_llm(text, cfg, key, base, mdl)
    out = _strip_links(out)
    try:
        links = _extract_links(out, refs, cfg, key, base, mdl)
        out = _apply_links(out, links, refs)
    except Exception:
        pass
    out = _entity_fallback(out, refs)
    if _count_links(out) < MIN_SUMMARY_LINKS:
        out = _journal_fallback(out, refs)
    if _count_links(out) < MIN_SUMMARY_LINKS:
        out = _append_sources(out, refs, MIN_SUMMARY_LINKS - _count_links(out))
    out = _clean_summary(out)
    result.ai_summary_refs = refs
    _write_cache(path, out, mdl, refs)
    return out
