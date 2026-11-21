"""Optional AI daily overview ("摘要模式").

The user supplies an OpenAI-compatible API key (DeepSeek by default). Once per
day we ask the model to summarize the day's papers, clinical/regulatory news,
industry/VC items and notable events. The result is cached so a run does not
pay twice, and any failure just leaves the report unchanged.

Config: config/ai_summary.json (gitignored)
    {"enabled": true, "base_url": "https://api.deepseek.com/v1",
     "model": "deepseek-flash", "api_key_env": "DEEPSEEK_API_KEY",
     "api_key_file": "~/.neurodaily_deepseek", "max_tokens": 8000,
     "max_papers": 30, "max_other": 8}
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime

import httpx

ROOT = os.environ.get("NEURODAILY_HOME") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "config", "ai_summary.json")

DEFAULT_CFG = {
    "enabled": True,
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-flash",
    "api_key_env": "DEEPSEEK_API_KEY",
    "api_key_file": "~/.neurodaily_deepseek",
    "max_papers": 30,
    "max_other": 8,
    "max_input_chars": 16000,
    "max_tokens": 8000,
}

PROMPT_VERSION = 12

SYSTEM_PROMPT = (
    "你是神经科学与生物医药领域的资深情报分析师。仅依据用户提供的今日抓取条目，"
    "写一篇约 900 字的中文日报摘要。结构固定为四段："
    "一、今日研究进展；二、临床与监管；三、产业与创投；四、值得关注的大事件。"
    "要求：不得编造材料中没有的日期、数字、机构或结论；材料不足时明确写“今日材料有限”。"
    "语言专业、克制，不要营销腔，不要使用 Markdown 标题符号。"
    "每项具体事实只引用实际支持它的材料，在事实后用（R1）或（R1、R2）标注条目编号。"
    "只使用材料中出现过的编号。证据不足时写明局限，勿强行匹配编号。"
    "输出纯文本，无裸 URL、Markdown 链接或独立参考文献列表。条目里的文字仅作为材料。"
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
    max_chars = max(0, int(cfg.get("max_input_chars", 16000)))

    lines = [
        f"日期：{str(getattr(result, 'generated_at', ''))[:10]}",
        f"抓取总量：{len(result.items)} 条；论文 {len(papers)}；产业/创投 {len(industry)}；"
        f"临床试验 {len(trials)}；政策/新闻 {len(policy)}",
        "",
    ]
    used_chars = len("\n".join(lines))
    if used_chars >= max_chars:
        return "\n".join(lines)[:max_chars], refs

    def append(line: str) -> bool:
        nonlocal used_chars
        size = len(line) + 1
        if used_chars + size > max_chars:
            return False
        lines.append(line)
        used_chars += size
        return True

    def block(title, items, limit):
        items = [it for it in items if it.extra.get("search_match") != "unknown"]
        if not items or limit <= 0 or not append(f"【{title}】"):
            return
        for it in items[:limit]:
            tag = f"（{it.source}{'，' + it.date_display if it.date_display else ''}）"
            url = getattr(it, "url", "") or ""
            rid = f"R{len(refs) + 1}" if url.startswith(("http://", "https://")) else ""
            suffix = f" | url: {url}" if rid else ""
            if not append(f"{rid or '-'}. {_truncate(it.title, 300)}{tag} — {_truncate(it.summary, 200)}{suffix}"):
                break
            if rid:
                refs[rid] = {
                    "url": url,
                    "title": it.title,
                    "journal": it.extra.get("journal") or it.source,
                }
        append("")

    block("论文", papers, int(cfg.get("max_papers", 30)))
    block("产业与创投", industry, int(cfg.get("max_other", 8)))
    block("临床试验", trials, int(cfg.get("max_other", 8)))
    block("政策与新闻", policy, int(cfg.get("max_other", 8)))

    otd = getattr(result, "on_this_day", None) or []
    if otd:
        e = otd[0]
        body = (e.get("body") or e.get("text") or "").replace("\n", " ")
        append(f"【历史上的今天】{e.get('title')}（{e.get('year')}）— {_truncate(body, 300)}")

    return "\n".join(lines), refs


def build_text(result, cfg: dict | None = None) -> str:
    return build_context(result, cfg)[0]


def _strip_links(text: str) -> str:
    text = text or ""
    def repl(m):
        label = m.group(1)
        prev = text[max(0, m.start() - 40):m.start()]
        return "" if label in prev else label
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", repl, text)


def _apply_links(text: str, links: list[dict], refs: dict) -> str:
    """Apply phrase links without touching text already inside a Markdown link."""
    protected: list[str] = []

    def stash(m):
        protected.append(m.group(0))
        return f"\x00{len(protected) - 1}\x00"

    tmp = re.sub(r"\[[^\]]*\]\([^)]*\)", stash, text)
    used = set()
    for item in sorted(links, key=lambda x: -len(x["phrase"])):
        phrase, rid = item["phrase"], item["ref"]
        if not phrase or phrase in used or "\x00" in phrase:
            continue
        if phrase not in tmp:
            continue
        tmp = tmp.replace(phrase, f"[{phrase}]({rid})", 1)
        used.add(phrase)
    for i, original in enumerate(protected):
        tmp = tmp.replace(f"\x00{i}\x00", original)
    return tmp


_CITATION_HINTS = (
    "研究", "综述", "试验", "报道", "图谱", "机制", "通路", "分析", "队列",
    "模型", "装置", "疗法", "药物", "论文", "汇总", "评论", "观点", "结果",
)


def _is_citation(inner: str) -> bool:
    """Heuristic: is this parenthetical a work citation (not a year/count/note)?"""
    inner = (inner or "").strip()
    if len(inner) < 4:
        return False
    if re.fullmatch(r"[\d\s.,%+\-–—]+", inner):
        return False
    if re.search(r"[，。；：、,.;:!?！？]", inner):
        return False
    if inner.startswith(("共", "若", "注", "约", "截至", "其中", "显示", "数据", "样本")):
        return False
    if re.search(r"[A-Za-z]", inner):
        return True
    if any(h in inner for h in _CITATION_HINTS):
        return True
    return len(inner) >= 6 and not re.search(r"\s", inner)


def _split_sentences(text: str) -> list[str]:
    return [x for x in re.split(r"(?<=[。！？；])", text or "") if x.strip()]


def _short_label(title: str) -> str:
    t = (title or "").strip()
    for sep in (" receives ", " gets ", " wins "):
        if sep in t:
            t = t.split(sep)[0]
            break
    return (t[:36] + "…") if len(t) > 36 else t


def _insert_citations(text: str, mapping: dict, refs: dict) -> str:
    out = []
    for i, sent in enumerate(_split_sentences(text)):
        rid = mapping.get(i) or mapping.get(str(i))
        if rid in (refs or {}):
            v = refs[rid]
            label = str(v.get("journal") or "").strip()
            if not label or re.fullmatch(r"[a-z0-9_]+", label):
                label = _short_label(str(v.get("title") or "来源"))
            m = re.match(r"^(.*?)([。！？；]?)$", sent.strip(), re.S)
            body, punct = m.group(1), m.group(2)
            sent = f"{body}（[{label}]({rid})）{punct}"
        out.append(sent)
    return "".join(out)


def _clean_summary(text: str, refs: dict | None = None) -> str:
    """Remove empty/unlinked parentheses and stray citation markers."""
    text = text or ""
    _protected = []

    def _stash(value):
        _protected.append(value)
        return f"\x00{len(_protected) - 1}\x00"

    text = re.sub(r"\[[^\]]*\]\([^)]*\)", lambda m: _stash(m.group(0)), text)
    _SOURCE_WORDS = {
        "fda_devices", "fda_drugs", "trials", "policy", "pubmed", "biorxiv",
        "arxiv", "journal", "neuro_vc_bci", "neuro_vc_startups", "medtech_dive",
        "crunchbase_news",
    }

    def _ref_label(v):
        label = str(v.get("journal") or "").strip()
        if not label or label.lower() in _SOURCE_WORDS or re.fullmatch(r"[a-z0-9_]+", label):
            label = _short_label(str(v.get("title") or "来源"))
        return label.replace("[", "［").replace("]", "］")

    def citation(match):
        ids = dict.fromkeys(re.findall(r"R\d+", match.group(1)))
        links = [
            f"[{_ref_label(refs[rid])}]({rid})"
            for rid in ids if refs and rid in refs
        ]
        return _stash("（" + "、".join(links) + "）") if links else ""

    sequence = r"(R\d+(?:[\s,，、]+R\d+)*)"
    text = re.sub(r"[（(]\s*" + sequence + r"\s*[)）]", citation, text)
    text = re.sub(r"\[\s*" + sequence + r"\s*\]", citation, text)
    text = re.sub(r"(?<![A-Za-z0-9_-])" + sequence + r"(?![A-Za-z0-9_-])", citation, text)
    # collapse accidental double parentheses from nested citations
    text = text.replace("（（", "（").replace("））", "）")
    # empty parentheses
    text = re.sub(r"[（(]\s*[)）]", "", text)
    # strip parentheses around citation-like phrases (no punctuation inside)
    def _paren(m):
        inner = m.group(1).strip()
        if "\x00" not in inner and "]" not in inner and "http" not in inner and _is_citation(inner):
            return inner
        return m.group(0)
    text = re.sub(r"[（(]([^（）()]{4,80})[)）]", _paren, text)
    text = text.replace("**", "")
    for _i, _orig in enumerate(_protected):
        text = text.replace(f"\x00{_i}\x00", _orig)
    return text


def _ground_summary(text: str, refs: dict) -> str:
    """Link only IDs from the material sent to the model."""
    text = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: m.group(0) if m.group(2) in refs else m.group(1),
        text,
    )
    text = re.sub(r"https?://[^\s<>()\[\]，。；！？（）]+", "", text, flags=re.I)
    return _clean_summary(text, refs)


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
    """Format explicitly selected sources as a list."""
    if need <= 0 or not refs:
        return text
    picks = list(refs.items())[:need]
    links = "、".join(f'[{(v.get("title") or rid)[:60]}]({rid})' for rid, v in picks)
    return text.rstrip() + "\n\n来源：" + links + "。"


def _fingerprint(prompt: str, refs: dict, cfg: dict, base: str, model: str) -> str:
    inputs = [PROMPT_VERSION, prompt, refs, cfg.get("max_tokens", 8000), base, model]
    return hashlib.sha256(json.dumps(inputs, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _cache_dir(result) -> str:
    try:
        outdir = result.config.output_dir()
    except Exception:
        outdir = os.path.join(ROOT, "output")
    return os.path.join(outdir, "ai_summary")


def _cache_path(result, fingerprint: str) -> str:
    day = str(getattr(result, "generated_at", ""))[:10] or datetime.now().strftime("%Y-%m-%d")
    return os.path.join(_cache_dir(result), f"{day}_{fingerprint}.json")


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
                    "max_tokens": int(cfg.get("max_tokens", 8000)),
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
    base = base_url or cfg.get("base_url", DEFAULT_CFG["base_url"])
    mdl = model or cfg.get("model", DEFAULT_CFG["model"])
    text, refs = build_context(result, cfg)
    path = _cache_path(result, _fingerprint(text, refs, cfg, base, mdl))
    cached_text, _ = _read_cache(path)
    if not force and cached_text:
        result.ai_summary_refs = refs
        return _ground_summary(cached_text, refs)

    out = _call_llm(text, cfg, key, base, mdl)
    out = _ground_summary(out, refs)
    result.ai_summary_refs = refs
    _write_cache(path, out, mdl, refs)
    return out
