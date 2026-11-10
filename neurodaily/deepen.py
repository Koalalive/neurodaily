"""Bulk-generate long-form 'on this day' bodies and cache them to disk.

Why: hand-writing ~900 Chinese characters for hundreds of milestones is not
practical, and inventing specifics would be dishonest. This module expands each
*verified* fact into a ~900-character essay with an LLM, forbidding fabricated
dates/numbers/names, and stores results in a JSON cache that the renderer reads.

Usage:
    neurodaily deepen --status
    neurodaily deepen --limit 50 --model gpt-4o-mini
    neurodaily deepen --backend template --limit 50   # offline fallback (generic)

Env (OpenAI-compatible):
    OPENAI_API_KEY      required for --backend llm
    OPENAI_BASE_URL     default https://api.openai.com/v1
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "onthisday_deep.json")

SYSTEM_PROMPT = (
    "你是神经科学、神经病学、精神病学与神经外科史的专业作者。"
    "只依据用户给出的事实（年份、标题、摘要）扩写成约 900 个中文字的连贯长文。"
    "结构：背景与问题 → 事件本身与机制 → 影响与后续 → 对今天的启示。"
    "严禁编造具体日期、数字、人名、试验名称或机构；不确定时用概括表述。"
    "输出纯中文正文，不要标题、不要列表、不要 Markdown 标记。"
)


def _key(year, title) -> str:
    return f"{year}|{title}"


def load_cache() -> dict:
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache: dict) -> None:
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CACHE_PATH)


def targets() -> list[dict]:
    """Milestones that still have no long-form body (reads the cache fresh)."""
    from .onthisday import EVERGREEN_ALL, EVENTS, _has_body
    cache = load_cache()
    seen, out = set(), []
    for e in list(EVERGREEN_ALL) + [x for v in EVENTS.values() for x in v]:
        k = (e.get("year"), e.get("title"))
        if k in seen:
            continue
        seen.add(k)
        if f"{k[0]}|{k[1]}" in cache or _has_body(*k):
            continue
        out.append(e)
    return out


def status() -> dict:
    from .onthisday import EVERGREEN_ALL, EVENTS
    total = len({(e.get("year"), e.get("title"))
                 for e in list(EVERGREEN_ALL) + [x for v in EVENTS.values() for x in v]})
    cache = load_cache()
    remaining = len(targets())
    return {"total": total, "cached": len(cache), "remaining": remaining,
            "cache_path": CACHE_PATH}


def _prompt_for(e: dict) -> str:
    kind = e.get("kind_label") or e.get("kind") or ""
    cat = e.get("category_label") or e.get("category") or ""
    return (
        f"年份：{e.get('year')}\n"
        f"类别：{cat} / {kind}\n"
        f"标题：{e.get('title')}\n"
        f"已知事实：{e.get('text', '')}\n\n"
        "请据此扩写约 900 个中文字，不要新增未经给出的事实细节。"
    )


def _call_llm(client, model: str, e: dict) -> str:
    import time
    last = None
    for attempt in range(4):
        try:
            resp = client.post(
                "/chat/completions",
                json={
                    "model": model,
                    "temperature": 0.6,
                    "max_tokens": 2000,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": _prompt_for(e)},
                    ],
                },
                timeout=180,
            )
            if resp.status_code == 429:
                raise RuntimeError("429 rate limited")
            resp.raise_for_status()
            data = resp.json()
            text = (data["choices"][0]["message"]["content"] or "").strip()
            if len(text) < 200:
                raise ValueError("too short")
            return text
        except Exception as exc:
            last = exc
            import random
            time.sleep(min(20, (2 ** attempt) + random.random() * 2))
    raise last


def expand_llm(limit: int | None = None, model: str | None = None,
               base_url: str | None = None, api_key: str | None = None,
               concurrency: int = 4) -> int:
    import httpx
    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise SystemExit("缺少 OPENAI_API_KEY（或传入 --api-key）。可用 --backend template 离线生成。")
    base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"

    todo = targets()
    if limit:
        todo = todo[:limit]
    if not todo:
        print("[deepen] 已完成，无需扩写。")
        return 0

    cache = load_cache()
    done = 0
    with httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {api_key}"}) as client:
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
            futs = {ex.submit(_call_llm, client, model, e): e for e in todo}
            for fut in as_completed(futs):
                e = futs[fut]
                try:
                    body = fut.result()
                    if len(body) < 200:
                        raise ValueError("too short")
                    cache[_key(e.get("year"), e.get("title"))] = body
                    done += 1
                    print(f"[deepen] {done}/{len(todo)} {e.get('year')} {e.get('title')} ({len(body)} 字)", flush=True)
                    if done % 5 == 0:
                        save_cache(cache)
                except Exception as exc:
                    _msg = str(exc) or type(exc).__name__
                    print(f"[deepen] FAILED {e.get('year')} {e.get('title')}: {_msg}", flush=True)
    save_cache(cache)
    print(f"[deepen] 写入 {done} 条 → {CACHE_PATH}")
    return done


# ---------------------------------------------------------------------------
# Offline template fallback (no LLM). Clearly generic; use only if acceptable.
# ---------------------------------------------------------------------------
_TPL = {
    "psychiatry": (
        "这一进展出现在精神病学从收容照护走向可解释、可干预的历史进程中。"
        "理解它需要同时看到三条线索：疾病概念如何被定义，治疗手段如何被验证，以及服务体系如何承接。"
    ),
    "neurology": (
        "这一进展出现在神经病学从症状描述走向机制与影像时代的进程中。"
        "理解它需要同时看到三条线索：定位与诊断手段的进步，治疗与随访体系的建立，以及患者结局的改善。"
    ),
    "neurosurgery": (
        "这一进展出现在神经外科从探索性手术走向精准与安全并重的进程中。"
        "理解它需要同时看到三条线索：解剖与定位的精细化，手术技术与器械的进步，以及围手术期管理的完善。"
    ),
    "neuroscience": (
        "这一进展出现在神经科学从结构描述走向机制、环路与计算的进程中。"
        "理解它需要同时看到三条线索：方法学的突破，理论框架的演进，以及向临床与技术的转化。"
    ),
}


def _template_body(e: dict) -> str:
    cat = e.get("category", "neuroscience")
    year = e.get("year")
    title = e.get("title", "")
    text = e.get("text", "")
    head = f"{year} 年的「{title}」是这一领域的重要节点。{text}"
    mid = _TPL.get(cat, _TPL["neuroscience"])
    tail = (
        "从方法学看，它改变了研究者与临床医生“能看见什么、能干预什么”的边界；"
        "从临床看，它为特定患者提供了新的选择，也带来了新的风险与随访要求；"
        "从历史看，它的价值不仅在于当时的成功或失败，更在于它为后来的技术、指南与制度提供了参照。"
        "对今天的从业者而言，回望这一节点，有助于理解当前实践的来路，并在面对新技术时保持审慎与开放。"
    )
    return head + "\n\n" + mid + "\n\n" + tail


def expand_template(limit: int | None = None) -> int:
    todo = targets()
    if limit:
        todo = todo[:limit]
    cache = load_cache()
    for e in todo:
        cache[_key(e.get("year"), e.get("title"))] = _template_body(e)
    save_cache(cache)
    print(f"[deepen] 模板扩写 {len(todo)} 条 → {CACHE_PATH}")
    return len(todo)


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="neurodaily deepen")
    p.add_argument("--status", action="store_true")
    p.add_argument("--backend", choices=["llm", "template"], default="llm")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--base-url", default=None)
    p.add_argument("--api-key", default=None)
    p.add_argument("--concurrency", type=int, default=4)
    args = p.parse_args(argv)

    if args.status:
        s = status()
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0
    if args.backend == "template":
        expand_template(limit=args.limit)
    else:
        expand_llm(limit=args.limit, model=args.model, base_url=args.base_url,
                   api_key=args.api_key, concurrency=args.concurrency)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
