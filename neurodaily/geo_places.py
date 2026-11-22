"""Conservative offline city lookup using Natural Earth populated places."""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from importlib.resources import files
import json
import re
import unicodedata


_WORD = re.compile(r"[^\W_]+")
_HAN = re.compile(r"[\u3400-\u9fff]")
_HAN_NAME = re.compile(r"[\u3400-\u9fff]{2,}")
_AT_PLACE = re.compile(
    r"(?<!\w)(?:in|at|from|within|city of|en|à|dans|im|aus|в|во|из)\s+$", re.I,
)
_ORGANIZATION_PREFIX = re.compile(
    r"(?:university|college|school|hospital|laboratory|institute|center|centre|museum|bank)\s+(?:of|for|at)\s+$",
    re.I,
)
_ORGANIZATION_SUFFIX = re.compile(
    r"(?:university|college|school|hospital|laborator(?:y|ies)|lab|institute|"
    r"center|centre|press|clinic|medical|research|foundation|society|campus|bank)\b",
    re.I,
)
_HAN_ORGANIZATION = re.compile(
    r"(?:[市县縣区區]?[立属屬]?)?(?:大学|大學|学院|學院|医院|醫院|医学院|醫學院|"
    r"研究院|研究所|实验室|實驗室|公司|中心|协会|協會|校区|校區)"
)
_HAN_POSITION = ("在", "于", "於", "位于", "位於", "来自", "來自", "设于", "設於")
_POSTAL = re.compile(r"(?:[A-Z]{1,3}\d[A-Z\d]*\s+\d[A-Z]{2}|\d{4,6}(?:-\d{4})?|[A-Z]{2}\s+\d{4,6})\b")
_ADM1_ABBR = re.compile(r"[A-Z]{2}(?=[,;.)]|$)")
_ADDRESS_WORDS = {"bath", "mobile", "nice", "normal", "orange", "reading"}
_US_CITY_QUALIFIERS = {
    ("washington",): re.compile(r"D\.?\s*C(?:\.|[^\w]|$)|District of Columbia\b", re.I),
    ("new", "york"): re.compile(r"NY(?=[,;.)]|\s|$)|City\b", re.I),
}
_COUNTRY_VARIANTS = {
    "GB": ("UK", "U.K.", "Great Britain"),
    "US": ("US", "U.S.", "USA", "U.S.A.", "United States"),
    "CN": ("China", "中国", "中國"),
}


def _fold(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(char))


def _key(text: str) -> tuple[str, ...]:
    return tuple(_WORD.findall(_fold(text)))


@lru_cache(maxsize=1)
def _index():
    data = files("neurodaily").joinpath("data")
    country_rows = json.loads(data.joinpath("natural_earth_countries.json").read_text(encoding="utf-8"))
    city_rows = json.loads(data.joinpath("natural_earth_cities.json").read_text(encoding="utf-8"))["rows"]
    countries = {
        code: {_key(value) for value in (row.get("name"), row.get("zh"), row.get("ru"),
                                         *row.get("aliases", ()), *_COUNTRY_VARIANTS.get(code, ()))
               if value}
        for code, row in country_rows.items()
    }
    country_terms = set().union(*countries.values())
    lookup = defaultdict(set)
    lengths = defaultdict(set)
    han = set()
    for name, country, lat, lon, aliases in city_rows:
        for alias in (name, *aliases):
            key = _key(alias)
            if not key or key in country_terms:
                continue
            han_alias = len(key) == 1 and _HAN_NAME.fullmatch(key[0])
            if not han_alias and len("".join(key)) < 3:
                continue
            lookup[key].add((name, country, lat, lon))
            if han_alias:
                han.add(key[0])
            else:
                lengths[key[0]].add(len(key))
    han_pattern = re.compile("|".join(map(re.escape, sorted(han, key=lambda name: (-len(name), name)))))
    return countries, lookup, {word: sorted(sizes, reverse=True) for word, sizes in lengths.items()}, han_pattern


def _matches(text: str, lookup, lengths, han_pattern):
    tokens = list(_WORD.finditer(text))
    keys = [_fold(token.group()) for token in tokens]
    index = 0
    while index < len(tokens):
        for size in lengths.get(keys[index], ()):
            end = index + size
            key = tuple(keys[index:end])
            if end <= len(tokens) and key in lookup and _connected_words(text, tokens, index, end, key):
                yield tokens[index].start(), tokens[end - 1].end(), key
                index = end
                break
        else:
            index += 1
    if _HAN.search(text) and han_pattern.pattern:
        for match in han_pattern.finditer(text):
            yield match.start(), match.end(), (match.group(),)


def _connected_words(text, tokens, start, end, key):
    for i in range(start, end - 1):
        gap = text[tokens[i].end():tokens[i + 1].start()]
        if any(symbol in gap for symbol in "\n\r;；:!?/"):
            return False
        if "." in gap and len(tokens[i].group()) > 2:
            return False
        if "," in gap and key != ("washington", "d", "c"):
            return False
    return True


def _location(text: str, start: int, end: int, country_terms, key) -> bool:
    left, right = text[:start], text[end:].lstrip()
    raw = text[start:end]
    address_start = not left.strip() or left.rstrip().endswith((",", "，", ";", "；", "(", "（", ":"))
    address_end = not right or right[0] in ",，;；)）"
    if _HAN_NAME.fullmatch(raw):
        if right.startswith(("省", "自治区", "自治區")) or _HAN_ORGANIZATION.match(right):
            return False
        return (address_start and address_end or left.rstrip().endswith(_HAN_POSITION)
                or raw.endswith(("市", "县", "縣")) or right.startswith(("市", "县", "縣", "区", "區")))
    if not any(letter.isupper() for letter in raw):
        return False
    if raw in ("USA", "U.S.", "UK") or right.startswith(("'", "’")):
        return False
    if _ORGANIZATION_PREFIX.search(left) or _ORGANIZATION_SUFFIX.match(right):
        return False
    after = _key(right)
    qualified = bool(_POSTAL.match(right) or _ADM1_ABBR.match(right)
                     or any(after[:len(name)] == name for name in country_terms))
    anchored = bool(_AT_PLACE.search(left))
    if " ".join(key) in _ADDRESS_WORDS:
        return (address_start or anchored) and (qualified or (address_end and bool(right)))
    if address_start and (address_end or qualified):
        return True
    # The following capitalised word can be part of an institution or a
    # different place name. Accept it only when it qualifies the location.
    return anchored and (qualified or not right or not right[0].isupper())


def city_candidates(evidence: str, country: str | None = None, *, city: str | None = None) -> list[dict]:
    """Return unambiguous city points explicitly named as places in the evidence."""
    if not isinstance(evidence, str) or not evidence.strip() or len(evidence) > 8192:
        return []
    countries, lookup, lengths, han_pattern = _index()
    country = country.strip().upper() if isinstance(country, str) else None
    if country is not None and country not in countries:
        return []
    requested = lookup.get(_key(city), ()) if isinstance(city, str) else None
    if requested is not None and not requested:
        return []

    evidence = unicodedata.normalize("NFC", evidence.strip())
    matches = sorted(_matches(evidence, lookup, lengths, han_pattern))
    seen = set()
    candidates = []
    for start, end, key in matches:
        hits = {row for row in lookup[key] if country is None or row[1] == country}
        if len(hits) != 1 or not _location(evidence, start, end, countries.get(country, ()), key):
            continue
        place, = hits
        if place in seen or (requested is not None and place not in requested):
            continue
        name, code, lat, lon = place
        qualifier = _US_CITY_QUALIFIERS.get(key) if code == "US" else None
        if qualifier and not qualifier.match(evidence[end:].lstrip(" ,")):
            continue
        seen.add(place)
        candidates.append({"name": name, "country": code, "lat": lat, "lon": lon})
    return candidates
