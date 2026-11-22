"""Optional LDA + t-SNE topic landscape for a digest report.

The module is deliberately optional: the base Tauri sidecar does not need
scikit-learn. When scikit-learn is unavailable, report rendering simply omits
the section. The report embeds a small JSON payload, so the desktop WebView only
draws points and never imports Python/native ML libraries.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

from .config import DEFAULT_DIRS
from .digest import DigestResult
from .records import record_ids

_MIN_DOCS = 8
_CACHE_VERSION = 1
_STOP_EN = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were",
    "has", "have", "had", "not", "but", "its", "into", "than", "their", "they",
    "using", "study", "results", "conclusion", "conclusions", "background",
    "objective", "methods", "method", "we", "our", "these", "those", "can",
    "may", "also", "more", "between", "after", "before", "during", "within",
    "health", "healthy", "patient", "patients", "clinical", "treatment", "treatments",
    "associated", "association", "analysis", "data", "outcome", "outcomes", "risk",
    "significant", "group", "groups", "effect", "effects", "increase", "decrease",
    "higher", "lower", "compared", "versus", "using", "used", "based", "among",
    "however", "although", "further", "including", "included", "associated",
    "disease", "disorder", "disorders", "symptoms", "symptom", "participants",
    "years", "year", "new", "one", "two", "three", "first", "last", "well",
    "show", "showed", "shown", "findings", "finding", "study", "studies",
    "research", "review", "reviews", "report", "reported", "case", "cases",
    "level", "levels", "factor", "factors", "role", "roles", "care", "clinical",
    "a", "an", "as", "at", "be", "been", "by", "is", "it", "its", "of", "on", "or",
    "to", "was", "were", "who", "will", "would", "could", "should", "while", "if",
    "into", "than", "then", "there", "these", "those", "their", "them", "this",
    "we", "our", "you", "your", "he", "she", "his", "her", "i", "ci", "vs",
}
_STOP_ZH = {"的", "了", "和", "是", "在", "与", "及", "或", "对", "中", "为", "等",
            "研究", "结果", "方法", "本文", "我们", "以及", "一个", "一种", "通过", "进行",
            "患者", "临床", "治疗", "健康", "疾病", "症状", "分析", "数据", "相关", "显著",
            "增加", "降低", "比较", "使用", "发现", "报告", "病例", "水平", "因素", "作用"}


def available() -> bool:
    try:
        import sklearn  # noqa: F401
        return True
    except ImportError:
        return False


def _clean(value) -> str:
    return " ".join(str(value or "").split())


def tokenize(text: str) -> list[str]:
    """Small dependency-free tokenizer for mixed English/Chinese text."""
    low = _clean(text).casefold()
    latin = [word for word in re.findall(r"[a-z][a-z0-9-]{1,}", low)
             if word not in _STOP_EN and len(word) > 1]
    chars = re.findall(r"[\u3400-\u9fff]", low)
    cjk = []
    for char in chars:
        if char not in _STOP_ZH:
            cjk.append(char)
    cjk += [a + b for a, b in zip(chars, chars[1:])
            if a not in _STOP_ZH and b not in _STOP_ZH]
    return latin + cjk


def _record_id(item, used: set[str]) -> str:
    ids = item.extra.get("record_ids") or record_ids(item)
    rid = ids[0] if ids else (item.url or item.doi or item.title)
    if rid in used:
        rid = f"{item.kind}:{rid}"
    used.add(rid)
    return rid


def _documents(result: DigestResult) -> list[dict]:
    docs, used = [], set()
    for item in result.items:
        text = _clean(" ".join((item.title or "", item.summary or "",
                                item.extra.get("abstract") or item.extra.get("article_text") or "")))
        if len(text) < 12:
            continue
        docs.append({"id": _record_id(item, used), "text": text[:3000], "title": item.title,
                     "url": item.url, "source": item.source, "kind": item.kind,
                     "date": item.date_display,
                     "venue": (item.extra.get("journal") if item.kind == "paper" else
                               (item.extra.get("feed") or item.source)) or ""})
    return docs


def _labels(topics: list[dict], chat=None, language: str = "zh") -> None:
    """Fill topic labels from the existing OpenAI-compatible chat helper."""
    if chat is not None:
        try:
            language_name = {"zh": "Chinese", "en": "English", "ru": "Russian"}.get(language, "Chinese")
            payload = [{"id": t["id"], "terms": t["terms"][:10],
                        "examples": t["examples"]} for t in topics]
            message = chat([
                {"role": "system", "content": "Label research topics. Return a JSON array only, "
                 f"objects with id (integer) and label (short {language_name} label, max 18 chars). "
                 "Use only the supplied terms/examples; do not invent facts."},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ], 1600)
            content = _clean(message.get("content"))
            fenced = re.fullmatch(r"\x60{3}(?:json)?\s*(.*?)\s*\x60{3}", content, re.S | re.I)
            rows = json.loads(fenced[1] if fenced else content)
            labels = {int(row["id"]): _clean(row["label"])[:30]
                      for row in rows if isinstance(row, dict) and "id" in row and row.get("label")}
            for topic in topics:
                if labels.get(topic["id"]):
                    topic["label"] = labels[topic["id"]]
        except Exception:
            pass
    for topic in topics:
        topic.setdefault("label", "、".join(topic["terms"][:3]) or f"主题 {topic['id']}")


def _cache_path(payload: dict) -> Path:
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return Path(DEFAULT_DIRS["output"], "topics_cache", digest + ".json")


def build_topics(result: DigestResult, *, chat=None, force: bool = False) -> dict | None:
    """Return a serialisable LDA+t-SNE map, or None if unavailable/too small."""
    if not available():
        return None
    docs = _documents(result)
    if len(docs) < _MIN_DOCS:
        return None
    from sklearn.decomposition import LatentDirichletAllocation
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.manifold import TSNE

    corpus = [doc["text"] for doc in docs]
    cache_payload = {"v": _CACHE_VERSION, "corpus": corpus, "labeler": bool(chat)}
    cache = _cache_path(cache_payload)
    if not force and cache.is_file():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass

    vectorizer = CountVectorizer(tokenizer=tokenize, token_pattern=None, lowercase=False,
                                 max_features=5000, min_df=2, max_df=0.90)
    matrix = vectorizer.fit_transform(corpus)
    if matrix.shape[1] < 2:
        return None
    n_topics = min(30, max(2, round(math.sqrt(len(docs)))))
    lda = LatentDirichletAllocation(n_components=n_topics, random_state=42,
                                    learning_method="batch", max_iter=15,
                                    n_jobs=-1)
    doc_topic = lda.fit_transform(matrix)
    perplexity = min(30, max(5, (len(docs) - 1) // 3))
    coords = TSNE(n_components=2, perplexity=perplexity, init="pca",
                  learning_rate="auto", random_state=42, max_iter=1000).fit_transform(doc_topic)

    terms = vectorizer.get_feature_names_out()
    topic_rows = []
    for index, weights in enumerate(lda.components_):
        top = [str(terms[i]) for i in weights.argsort()[-12:][::-1]]
        members = [i for i in range(len(docs)) if int(doc_topic[i].argmax()) == index]
        examples = [docs[i]["title"] for i in sorted(members, key=lambda i: doc_topic[i][index],
                                                      reverse=True)[:3]]
        topic_rows.append({"id": index, "terms": top, "examples": examples,
                           "size": len(members),
                           "label": "、".join(top[:3]) or f"主题 {index}"})
    for language in ("zh", "en", "ru"):
        _labels(topic_rows, chat, language)
        for topic in topic_rows:
            topic.setdefault("labels", {})[language] = topic["label"]
    labels = {row["id"]: row.get("labels", {}).get("zh") or row["label"] for row in topic_rows}
    xs = [float(p[0]) for p in coords]
    ys = [float(p[1]) for p in coords]
    xmid, ymid = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    points = []
    for index, doc in enumerate(docs):
        topic = int(doc_topic[index].argmax())
        point_doc = {key: value for key, value in doc.items() if key != "text"}
        point_doc["summary"] = doc["text"][:240]
        points.append({**point_doc, "x": round(float(coords[index][0]) - xmid, 5),
                       "y": round(float(coords[index][1]) - ymid, 5),
                       "topic": topic, "label": labels.get(topic, f"主题 {topic}"),
                       "labels": next((row.get("labels", {}) for row in topic_rows if row["id"] == topic), {}),
                       "confidence": round(float(doc_topic[index][topic]), 4)})
    result_data = {"enabled": True, "method": "lda_tsne", "topics": topic_rows,
                   "points": points, "unknown": [], "n_topics": n_topics}
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        tmp.write_text(json.dumps(result_data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(cache)
    except OSError:
        pass
    return result_data


def enrich_topics(result: DigestResult, *, force: bool = False) -> bool:
    if result.skipped or not result.items:
        return False
    cfg = getattr(result, "config", None)
    output = getattr(cfg, "output", None) or {}
    if output.get("topic_map") is False:
        return False
    chat = None
    try:
        from . import ai_summary
        settings = ai_summary.load_cfg()
        key = ai_summary.api_key(settings)
        if key:
            base = ai_summary._api_base(settings["base_url"])
            model = settings["model"]
            def chat(messages, max_tokens):
                return ai_summary._chat_request(base, model, key, messages, max_tokens, 45,
                                                purpose="topic_labels",
                                                run_id=result.history_id or None,
                                                profile=result.config_profile, temperature=0)
    except Exception:
        chat = None
    result.topics = build_topics(result, chat=chat, force=force)
    return result.topics is not None
