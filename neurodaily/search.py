"""Parse advanced queries and evaluate them consistently across literature sources."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date

FIELDS = {
    "TI": "title", "AB": "abstract", "TIAB": "title or abstract",
    "TS": "topic", "AK": "author keywords", "AU": "author",
    "SO": "journal", "ISSN": "ISSN", "MH": "MeSH", "DT": "publication type",
    "CAT": "category", "PY": "publication year", "PD": "publication date",
}
QUERY_VERSION = 1
_TOKEN = re.compile(r'"(?:[^"\\]|\\["\\])*"|[^\s"()=]+|[()=]')
_OPERATORS = {"AND", "OR", "NOT"}
_WORD = re.compile(r"\w+", re.UNICODE)
_ISSN = re.compile(r"\d{4}-?\d{3}[\dXx]")


def _text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _journal_key(value: str) -> str:
    return "".join(c for c in _text(value) if c.isalnum())


def _issn_key(value: str) -> str:
    return value.replace("-", "").upper()


def _dates(field: str, value: str) -> tuple[str, str]:
    try:
        if field == "PY" and re.fullmatch(r"\d{4}(?:[-:]\d{4})?", value):
            start, end = value.replace("-", ":").split(":")[0], value[-4:]
            first, last = date(int(start), 1, 1), date(int(end), 12, 31)
        elif field == "PD":
            parts = value.split(":")
            if len(parts) > 2 or not all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", p) for p in parts):
                raise ValueError
            first, last = date.fromisoformat(parts[0]), date.fromisoformat(parts[-1])
        else:
            raise ValueError
        if first > last:
            raise ValueError
        return first.isoformat(), last.isoformat()
    except ValueError:
        raise ValueError(f"{field} 的日期范围无效（例如 PY=2024-2026 或 PD=2025-01-01:2025-12-31）") from None


@dataclass(frozen=True)
class Term:
    field: str
    value: str
    phrase: bool = False

    def label(self) -> str:
        value = json.dumps(self.value, ensure_ascii=False) if self.phrase else self.value
        return f"{self.field}={value}"


@dataclass(frozen=True)
class Group:
    operator: str
    left: Node
    right: Node


@dataclass(frozen=True)
class Exclude:
    child: Node


@dataclass(frozen=True)
class Near:
    left: Term
    right: Term
    distance: int


Node = Term | Group | Exclude | Near


def _tokens(expression: str) -> list[str]:
    if len(expression) > 1800:
        raise ValueError("每条检索式最多 1800 字符")
    tokens, end = [], 0
    for match in _TOKEN.finditer(expression):
        if expression[end:match.start()].strip():
            raise ValueError(f"第 {end + 1} 个字符附近有无效括号、引号或转义")
        tokens.append(match[0])
        end = match.end()
    if expression[end:].strip():
        raise ValueError("检索式末尾的引号或转义不完整")
    if len(tokens) > 160:
        raise ValueError("每条检索式最多 160 个词、运算符和标点")
    return tokens


class _Parser:
    def __init__(self, expression: str, resolve):
        self.tokens = _tokens(expression)
        self.index = 0
        self.resolve = resolve

    def peek(self) -> str:
        return self.tokens[self.index] if self.index < len(self.tokens) else ""

    def take(self) -> str:
        token = self.peek()
        if not token:
            raise ValueError("检索式还缺少条件")
        self.index += 1
        return token

    def parse(self) -> Node:
        node = self.disjunction("TIAB")
        if self.peek():
            raise ValueError(f"无法解析 {self.peek()}，请检查括号或添加 AND、OR")
        return node

    def disjunction(self, field: str) -> Node:
        node = self.conjunction(field)
        while self.peek().upper() == "OR":
            self.take()
            node = Group("OR", node, self.conjunction(field))
        return node

    def conjunction(self, field: str) -> Node:
        node = self.unary(field)
        while self.peek().upper() in ("AND", "NOT"):
            operator = self.take().upper()
            right = self.unary(field)
            node = Group("AND", node, Exclude(right) if operator == "NOT" else right)
        return node

    def unary(self, field: str) -> Node:
        if self.peek().upper() == "NOT":
            self.take()
            return Exclude(self.unary(field))
        left = self.atom(field)
        operator = self.peek().upper()
        if operator == "NEAR" or operator.startswith("NEAR/"):
            self.take()
            raw_distance = operator.partition("/")[2] if "/" in operator else "15"
            if not raw_distance.isdigit() or not 0 <= int(raw_distance) <= 30:
                raise ValueError("NEAR/n 的距离应在 0 到 30 之间")
            right = self.atom(field)
            if (not isinstance(left, Term) or not isinstance(right, Term)
                    or left.field != right.field or left.field not in ("TI", "AB", "TIAB", "TS")
                    or not all(_WORD.findall(term.value) for term in (left, right))):
                raise ValueError("NEAR/n 需要同一个文字字段内的两个词或短语")
            return Near(left, right, int(raw_distance))
        return left

    def atom(self, field: str) -> Node:
        token = self.take()
        if self.peek() == "=":
            self.take()
            field = token.upper()
            if field not in FIELDS:
                raise ValueError(f"不支持检索字段 {token}")
            token = self.take()
        if token == "(":
            node = self.disjunction(field)
            if self.take() != ")":
                raise ValueError("缺少右括号")
            return node
        if re.fullmatch(r"#\d+", token):
            return self.resolve(token[1:])
        if token in (")", "=") or token.upper() in _OPERATORS or token.upper().startswith("NEAR/"):
            raise ValueError(f"{token} 前后缺少检索词")
        phrase = token.startswith('"')
        value = json.loads(token) if phrase else token
        if not value.strip() or len(value) > 250:
            raise ValueError("每个检索词应包含 1 到 250 个字符")
        if field in ("PY", "PD"):
            _dates(field, value)
        if field == "ISSN" and not _ISSN.fullmatch(value):
            raise ValueError("ISSN 应为类似 1234-5678 的编号")
        return Term(field, value.strip(), phrase)


def _bounds(node: Node | None) -> tuple[str, str] | None:
    if isinstance(node, Term) and node.field in ("PY", "PD"):
        return _dates(node.field, node.value)
    if isinstance(node, Group):
        left, right = _bounds(node.left), _bounds(node.right)
        if node.operator == "OR":
            return (min(left[0], right[0]), max(left[1], right[1])) if left and right else None
        if left and right:
            return max(left[0], right[0]), min(left[1], right[1])
        return left or right
    return None


@dataclass
class Match:
    status: str
    evidence: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()


def _as_values(value) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [v for v in value if isinstance(v, str) and v.strip()]
    return []


def _fields(item, field: str) -> dict[str, list[str]]:
    extra = item.extra
    keywords = _as_values(extra.get("keywords"))
    if item.kind == "trial":
        keywords = [*keywords, *_as_values(extra.get("conditions")), *_as_values(extra.get("interventions"))]
    values = {
        "TI": item.title, "AB": extra.get("abstract") or item.summary,
        "AK": keywords, "AU": item.authors,
        "SO": [*_as_values(extra.get("journal")), *_as_values(extra.get("journal_aliases"))],
        "ISSN": [*_as_values(extra.get("issn")), *_as_values(extra.get("issns")),
                 *_as_values(extra.get("issn_l"))],
        "MH": extra.get("mesh_terms"), "DT": extra.get("publication_types"),
        "CAT": extra.get("categories") or extra.get("category"),
        "PY": item.date, "PD": item.date,
    }
    if field in ("TS", "TIAB"):
        keys = ("TI", "AB", "AK") if field == "TS" and item.kind in {"paper", "trial"} else ("TI", "AB")
        return {key: _as_values(values[key]) for key in keys}
    return {field: _as_values(values[field])}


def _literal(value: str, candidate: str) -> bool:
    value = _text(value)
    if not value:
        return False
    start = r"(?<!\w)" if value[0].isalnum() or value[0] == "_" else ""
    end = r"(?!\w)" if value[-1].isalnum() or value[-1] == "_" else ""
    return re.search(start + re.escape(value) + end, _text(candidate)) is not None


def _date_matches(term: Term, value: str) -> bool | None:
    first, last = _dates(term.field, term.value)
    if term.field == "PY" and re.match(r"^\d{4}(?:-|$)", value):
        return first[:4] <= value[:4] <= last[:4]
    try:
        return first <= date.fromisoformat(value[:10]).isoformat() <= last
    except ValueError:
        return None


def _near_matches(rule: Near, value: str) -> bool:
    words = _WORD.findall(_text(value))
    left = _WORD.findall(_text(rule.left.value))
    right = _WORD.findall(_text(rule.right.value))
    ends = [index + len(left) for index in range(len(words)) if words[index:index + len(left)] == left]
    for index in range(len(words)):
        if words[index:index + len(right)] != right:
            continue
        if any(0 <= index - end <= rule.distance or
               0 <= end - len(left) - index - len(right) <= rule.distance for end in ends):
            return True
    return False


def _merge(operator: str, left: Match, right: Match) -> Match:
    if operator == "AND":
        if "miss" in (left.status, right.status):
            return Match("miss")
        status = "unknown" if "unknown" in (left.status, right.status) else "match"
    else:
        if "match" in (left.status, right.status):
            return Match("match", tuple(dict.fromkeys(left.evidence + right.evidence)))
        status = "unknown" if "unknown" in (left.status, right.status) else "miss"
    return Match(status, tuple(dict.fromkeys(left.evidence + right.evidence)),
                 tuple(dict.fromkeys(left.missing_fields + right.missing_fields)))


@dataclass(frozen=True)
class SearchPlan:
    expression: str
    root: Node | None
    sets: dict[str, str]
    journal_mode: str
    journals: tuple[str, ...]
    sort: str
    journal_catalog: tuple = ()

    @property
    def active(self) -> bool:
        return self.root is not None or (self.journal_mode == "only" and bool(self.journals))

    @property
    def date_range(self) -> tuple[str, str] | None:
        return _bounds(self.root)

    def _journal_match(self, item, term: str) -> bool | None:
        names = {_journal_key(v) for v in _fields(item, "SO")["SO"]}
        ids = {_issn_key(v) for v in _fields(item, "ISSN")["ISSN"]}
        for journal in self.journal_catalog:
            keys = {_journal_key(v) for v in [journal.name, *journal.aliases] if v}
            known_ids = {_issn_key(v) for v in journal.issns}
            if keys & names or known_ids & ids:
                names.update(keys)
                ids.update(known_ids)
        if _ISSN.fullmatch(term):
            return _issn_key(term) in ids if ids else None
        if names:
            return _journal_key(term) in names
        return False if item.source in ("arxiv", "biorxiv", "medrxiv") else None

    def preferred_journal(self, item) -> bool:
        return any(self._journal_match(item, journal) is True for journal in self.journals)

    def match(self, item) -> Match:
        result = self._match(self.root, item) if self.root is not None else Match("match")
        if self.journal_mode != "only" or not self.journals:
            return result
        hits = [self._journal_match(item, name) for name in self.journals]
        if True in hits:
            journal = Match("match", (f"指定期刊 · {self.journals[hits.index(True)]}",))
        elif None in hits:
            journal = Match("unknown", missing_fields=("SO",))
        else:
            journal = Match("miss")
        return _merge("AND", result, journal)

    def _match(self, node: Node, item) -> Match:
        if isinstance(node, Group):
            return _merge(node.operator, self._match(node.left, item), self._match(node.right, item))
        if isinstance(node, Exclude):
            matched = self._match(node.child, item)
            if matched.status == "unknown":
                return Match("unknown", missing_fields=matched.missing_fields)
            return Match("miss" if matched.status == "match" else "match")
        if isinstance(node, Term) and node.field in ("SO", "ISSN"):
            matched = self._journal_match(item, node.value)
            return (Match("match", (node.label(),)) if matched else Match("miss") if matched is False
                    else Match("unknown", missing_fields=(node.field,)))
        field = node.left.field if isinstance(node, Near) else node.field
        missing = []
        for key, values in _fields(item, field).items():
            if not values:
                missing.append(key)
                continue
            if isinstance(node, Near):
                if any(_near_matches(node, v) for v in values):
                    return Match("match", (f'{key}=({node.left.value} NEAR/{node.distance} {node.right.value})',))
            else:
                if key in ("PY", "PD"):
                    matches = [_date_matches(node, value) for value in values]
                    if None in matches:
                        missing.append(key)
                elif key in ("AK", "MH", "DT", "CAT"):
                    matches = [_text(node.value) == _text(v) for v in values]
                else:
                    matches = [_literal(node.value, v) for v in values]
                if True in matches:
                    return Match("match", (Term(key, node.value, node.phrase).label(),))
        return Match("unknown", missing_fields=tuple(missing)) if missing else Match("miss")

    def remote_query(self, source: str) -> str:
        """Only push necessary candidate conditions. Exact matching happens locally."""
        return _remote(self.root, source)


def _remote(node: Node | None, source: str) -> str:
    if isinstance(node, Group):
        left, right = _remote(node.left, source), _remote(node.right, source)
        if left and right:
            return f"({left} {node.operator} {right})"
        return (left or right) if node.operator == "AND" else ""
    if isinstance(node, Near):
        return _remote(Group("AND", node.left, node.right), source)
    if not isinstance(node, Term):
        return ""
    if source == "arxiv" and node.field == "CAT" and re.fullmatch(r"[\w.\-]+", node.value):
        return f"cat:{node.value}"
    # A multiword phrase, punctuation, exact journal identity and negation
    # can have different indexing rules upstream. Keep them local; use single
    # Unicode word tokens as mandatory candidate hints where supported.
    words = _WORD.findall(node.value)
    if not words or not re.fullmatch(r"[\w\s]+", node.value):
        return ""
    if source == "pubmed":
        field = {"TI": "ti", "AB": "tiab", "TIAB": "tiab", "AK": "tiab", "TS": "tiab"}.get(node.field)
        if node.field == "MH":
            return f'"{node.value}"[mh:noexp]'
        return "(" + " AND ".join(f"{word}[{field}]" for word in words) + ")" if field else ""
    if source == "arxiv":
        field = {"TI": ("ti",), "AB": ("abs",), "TIAB": ("ti", "abs")}.get(node.field)
        if field:
            return "(" + " AND ".join(
                "(" + " OR ".join(f'{f}:"{word}"' for f in field) + ")" for word in words
            ) + ")"
    if source == "trials" and node.field in {"TS", "TIAB", "TI", "AB", "AK"}:
        return "(" + " AND ".join(f'"{word}"' for word in words) + ")"
    return ""


SCOPED_KINDS = ("news", "policy", "trial")


def compile_scoped_search(search: dict | None) -> dict[str, SearchPlan]:
    search = search or {}
    return {kind: compile_search({"query": query, "sets": search.get("sets", {})})
            for kind, query in (search.get("rules") or {}).items() if query.strip()}


def compile_search(search: dict | None, journal_catalog=()) -> SearchPlan:
    spec = search or {}
    expression = spec.get("query", "").strip()
    sets = {key.lstrip("#"): value.strip() for key, value in spec.get("sets", {}).items()}
    if len(sets) != len(spec.get("sets", {})):
        raise ValueError("编号集合重复")
    resolving: set[str] = set()
    resolved: dict[str, Node] = {}
    if len(sets) > 12 or any(not re.fullmatch(r"[1-9]\d{0,2}", key) for key in sets):
        raise ValueError("最多保存 12 个编号集合，集合编号应在 #1 至 #999 之间")
    if sum(len(value) for value in sets.values()) > 3600:
        raise ValueError("保存的检索集合总长度不能超过 3600 字符")

    def resolve(key: str) -> Node:
        if key in resolving:
            raise ValueError(f"检索集合 #{key} 循环引用")
        if key not in sets:
            raise ValueError(f"找不到检索集合 #{key}")
        if key not in resolved:
            resolving.add(key)
            resolved[key] = _Parser(sets[key], resolve).parse()
            resolving.remove(key)
        return resolved[key]

    try:
        for key in sets:
            resolve(key)
        root = _Parser(expression, resolve).parse() if expression else None
    except RecursionError:
        raise ValueError("检索条件或编号集合嵌套过深") from None

    sizes: dict[int, int] = {}

    def size(node: Node) -> int:
        if id(node) not in sizes:
            if isinstance(node, Group):
                count = 1 + size(node.left) + size(node.right)
            elif isinstance(node, Exclude):
                count = 1 + size(node.child)
            else:
                count = 1
            if count > 350:
                raise ValueError("展开编号集合后的检索条件过多")
            sizes[id(node)] = count
        return sizes[id(node)]

    if root is not None:
        size(root)
    mode = spec.get("journal_mode", "any")
    journals = tuple(dict.fromkeys(name.strip() for name in spec.get("journals", []) if name.strip()))
    if mode != "any" and not journals:
        raise ValueError("选择限制或优先期刊时，至少填写一个期刊名或 ISSN")
    return SearchPlan(expression, root, sets, mode, journals, spec.get("sort", "default"),
                      tuple(journal_catalog))
