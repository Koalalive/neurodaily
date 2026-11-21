"""Build a bounded keyword cloud from the items already present in a report."""

from collections import defaultdict
from html import unescape
from itertools import islice
import re
from unicodedata import normalize

from .models import Item


_MAX_TERMS = 36
_MAX_ENTRIES = 5
_TITLE_WEIGHT = 4
_HAN = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f"
_HAN_WORD = re.compile(f"[{_HAN}]+")
_WORDS = re.compile(rf"[{_HAN}]+|(?:(?![{_HAN}])[^\W_])+")
_UNITS = re.compile(r"[^.,!?;:。！？；，、：()\[\]\n]+")
_MARKUP = re.compile(r"<[^>]*>|https?://\S+", re.IGNORECASE)
_HAN_FILLER = re.compile(
    r"基于|通过|以及|及其|导致|关于|研究|结果|显示|表明|方法|目的|结论|分析|评估|患者|病例|"
    r"样本|是否|及|的|与|和|在|对|为|了|中|等|后|其|该|可"
)
_STOP_WORDS = frozenset("""
    about across acute after against age all also among analysis analyses and approach are as assessment at author authors
    based because been before between both but by can case cases compared comparison conclusion conclusions
    data design did different does during each effect effects else feasibility figure findings first follow followed following for
    from further group groups had has have high how however human including into introduction investigation involved
    last level levels low major many may method methods model models more most new next novel now number of
    off often on one only or other our outcome outcomes over paper participants patients patient pdf performed
    presents previous procedure prospective randomized related report reports reported research results result
    review reviews role same sample samples secondary several should shows significant significantly similar
    since some study studies such systematic table than that the their them then therefore there these they this those
    through time times to together trial trials two under up use used using versus via was we well were what
    when where whether which while who whose will with within without would year years 以及 以及其 观察
    автор авторы анализ были была было быть введение вывод выводы все всё для данные даже или как когда
    между менее метод методы может могут наш наши него него них они она оно оценка очень показано показали
    после поэтому при применение работе работы результат результаты среди статья также такие так только уже
    участников участники чего чем через что это этой этот являются являлись исследования исследование
    изучение применение методы пациент пациента пациентов больных больные сравнении сравнение случае случаи
    свой свои новых новая новый работы подход подходы обзор обзорный текущий первый второй значимых выявлены
""".split())
_STOP_PHRASES = {"all rights reserved", "case report", "case reports", "clinical trial", "clinical trials",
                 "female", "humans", "male", "animals", "not applicable", "review article",
                 "systematic review", "top journal", "unknown", "untitled"}
_SOURCE_TAGS = {"arxiv", "biorxiv", "clinicaltrials gov", "fda", "feed", "medrxiv", "openfda", "pubmed", "rss"}
_SHORT_TERMS = {"ai", "ct", "mr", "ии", "кт", "мр"}
_RAW_TOPIC_MARKER = re.compile(r"(?:cs|q-bio|math|stat|physics)\.[a-z-]+", re.IGNORECASE)
_ALIASES = {
    "acute respiratory distress syndrome": ("ards",),
    "acute kidney injury": ("aki",),
    "cardiopulmonary resuscitation": ("cpr",),
    "electroencephalography": ("eeg",),
    "extracorporeal membrane oxygenation": ("ecmo",),
    "intensive care unit": ("icu", "icus", "intensive care units", "i c u"),
    "mechanical ventilation": ("mechanical ventilatory support",),
    "traumatic brain injury": ("tbi", "traumatic brain injuries"),
    "重症监护": ("重症监護", "重症監護", "重症监护病房", "重症监护室"),
    "интенсивная терапия": ("интенсивной терапии",),
    "отделение реанимации и интенсивной терапии": ("орит",),
}
_CANONICAL = {variant: term for term, variants in _ALIASES.items() for variant in (term, *variants)}
_TOPICS = set(_CANONICAL) | {term.strip() for term in """
    brain computer interface|cognitive neuroscience|deep learning|drug resistant epilepsy|functional connectivity|gene expression|
    immune checkpoint|kidney transplantation|lung cancer|lung transplantation|machine learning|
    magnetic resonance imaging|mild cognitive impairment|neural decoding|neural network|organ failure|
    patient safety|precision medicine|quality of life|renal replacement therapy|respiratory failure|
    sepsis|septic shock|single cell|spinal cord injury|stem cell|stem cells|working memory|
    脓毒症|败血症|人工智能|危重症|急性肾损伤|工作记忆|机械通气|深度学习|脑卒中|脑机接口|神经可塑性|
    神经保护|认知功能|呼吸衰竭|呼吸窘迫|器官衰竭|肾脏替代治疗|肿瘤免疫|靶向治疗|耐药性|
    сепсис|септический шок|дыхательная недостаточность|искусственный интеллект|нейронная сеть|
    искусственная вентиляция лёгких|когнитивные функции|машинное обучение|почечная недостаточность
""".split("|") if term.strip()}


def _text(value: str, limit: int) -> str:
    return _MARKUP.sub(" ", normalize("NFKC", unescape(value[:limit])).casefold())


def _terms(value) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[;,，；]", value[:3000]) if part.strip()]
    if isinstance(value, (list, tuple)):
        return [term for term in value[:40] if isinstance(term, str)]
    return []


def _content_word(word: str) -> bool:
    return (word not in _STOP_WORDS and any(letter.isalpha() for letter in word)
            and (len(word) >= 3 or word in _SHORT_TERMS))


def _clean_term(value: str) -> str:
    if len(value) > 80 or _RAW_TOPIC_MARKER.fullmatch(value.strip()):
        return ""
    words = _WORDS.findall(_text(value, 80))
    raw = " ".join(words)
    if (not 1 <= len(words) <= 8 or raw in _STOP_PHRASES or raw in _SOURCE_TAGS
            or not any(_content_word(word) or (_HAN_WORD.fullmatch(word) and len(word) >= 2)
                       for word in words)):
        return ""
    return raw


def _metadata(item: Item) -> dict[str, int]:
    excluded = {item.source.replace("_", " ").casefold(), item.kind.casefold()}
    keywords = {_clean_term(tag): 6 for tag in _terms(item.tags)}
    for field in ("keywords", "mesh_terms", "conditions", "topics"):
        keywords.update({_clean_term(term): 8 for term in _terms(item.extra.get(field))})
    return {term: weight for term, weight in keywords.items() if term and term not in excluded}


def _han_spans(words: str, topics: set[str], largest: int, *, title: bool):
    """Match named topics first. Use repeated short spans when the vocabulary is incomplete."""
    position = 0
    plain_start = 0
    while position < len(words):
        known = next((words[position:end] for end in range(min(len(words), position + largest), position + 1, -1)
                      if words[position:end] in topics), "")
        if known:
            yield from _han_fallback(words[plain_start:position], title=title)
            yield known, 7 if title else 5
            position += len(known)
            plain_start = position
        else:
            position += 1
    yield from _han_fallback(words[plain_start:], title=title)


def _han_fallback(words: str, *, title: bool):
    for part in _HAN_FILLER.split(words):
        if not part or part in _STOP_WORDS:
            continue
        if 2 <= len(part) <= 6:
            yield part, _TITLE_WEIGHT if title else 2
        elif title:
            for width in (4, 3, 2):
                for start in range(len(part) - width + 1):
                    yield part[start:start + width], 2


def _text_matches(value: str, topics: set[str], max_words: int, max_han: int, *, title: bool):
    for sentence in _UNITS.findall(_text(value, 300 if title else 1600)):
        words = _WORDS.findall(sentence)
        index = 0
        while index < len(words):
            word = words[index]
            known = next((" ".join(words[index:end])
                          for end in range(min(len(words), index + max_words), index, -1)
                          if " ".join(words[index:end]) in topics), "")
            if known:
                yield known, 7 if title else 5
                index += known.count(" ") + 1
                continue
            if _HAN_WORD.fullmatch(word):
                yield from _han_spans(word, topics, max_han, title=title)
            elif _content_word(word) and word not in _STOP_PHRASES and word not in _SOURCE_TAGS:
                yield word, _TITLE_WEIGHT if title else 1
                if title and index + 1 < len(words):
                    following = words[index + 1]
                    if not _HAN_WORD.fullmatch(following) and _content_word(following):
                        yield f"{word} {following}", 2
            index += 1


def keyword_cloud(items: dict[str, Item], config=None) -> list[dict]:
    """Return the most frequent terms with unique item counts and up to five strong matches."""
    indexed = [(item_id, item, _metadata(item)) for item_id, item in items.items()]
    topics = _TOPICS | {term for _, _, metadata in indexed for term in metadata}
    if config is not None:
        topics.update(term for value in (*config.all_keywords(), *config.all_mesh_terms())
                      if (term := _clean_term(value)))
    max_words = max(len(term.split()) for term in topics)
    max_han = max(len(term) for term in topics if _HAN_WORD.fullmatch(term))
    mentions = defaultdict(list)
    for rank, (item_id, item, metadata) in enumerate(indexed):
        evidence = {}
        abstract = item.extra.get("abstract")
        if not isinstance(abstract, str) or not abstract.strip():
            abstract = item.summary
        for terms in (
            metadata.items(),
            islice(_text_matches(item.title, topics, max_words, max_han, title=True), 180),
            islice(_text_matches(abstract, topics, max_words, max_han, title=False), 160),
        ):
            for term, weight in terms:
                canonical = _CANONICAL.get(term, term)
                evidence[canonical] = max(evidence.get(canonical, 0), weight)
        search_hits = len(_terms(item.extra.get("matched_rules")))
        for term, weight in evidence.items():
            mentions[term].append((weight, search_hits, rank, item_id))

    # An isolated weak fragment is rarely useful. Keep such terms only if they recur.
    usable_mentions = [(term, hits) for term, hits in mentions.items()
                       if len(hits) >= 2 or hits[0][0] >= _TITLE_WEIGHT]
    ranked = sorted(usable_mentions,
                    key=lambda pair: (-len(pair[1]), -sum(hit[0] for hit in pair[1]), pair[0]))
    return [{"term": term, "count": len(hits),
             "entries": [hit[3] for hit in sorted(hits, key=lambda hit: (-hit[0], -hit[1], hit[2]))[:_MAX_ENTRIES]]}
            for term, hits in ranked[:_MAX_TERMS]]
