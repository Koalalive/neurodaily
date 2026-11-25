"""Keep generated reports interactive without authorizing stored HTML as code."""
from __future__ import annotations

from functools import lru_cache
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from secrets import token_urlsafe

from .security import external_url
from .ui_translations import UI_LANGUAGES, _translation_script

_REPORT_ASSETS = {"/static/report/feedback.js"}
_DATA_SCRIPTS = {"nd-research-data", "nd-topic-data"}
_EMBEDDED = {"research_activity": "nd-research-data", "topic_map": "nd-topic-data"}
_INLINE = re.compile(r"<script>([\s\S]*?)</script>")


def _script_bytes(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


@lru_cache(maxsize=3)
def _known_scripts(language):
    from .render import TEMPLATE_DIR, _GRAPH_JS

    directory = Path(TEMPLATE_DIR)
    main = _INLINE.findall((directory / "report.html.j2").read_text(encoding="utf-8"))
    translated = tuple(_translation_script(locale).split(">", 1)[1].removesuffix("</script>")
                       for locale in UI_LANGUAGES)
    replacements = {}
    trusted = {*main, *_INLINE.findall(_GRAPH_JS), *translated}
    for template_name, data_id in _EMBEDDED.items():
        template = (directory / f"{template_name}.html.j2").read_text(encoding="utf-8")
        script, = _INLINE.findall(template)
        options = tuple(script.replace("{{ language|tojson }}", json.dumps(locale))
                        for locale in UI_LANGUAGES)
        trusted.update(options)
        replacements[data_id] = (set(options), options[UI_LANGUAGES.index(language)])
    return {_script_bytes(body) for body in trusted}, replacements


def _navigate(value):
    if url := external_url(value):
        return url
    if not value or any(char.isspace() or ord(char) < 32 or char == "\\" for char in value):
        return ""
    if value.startswith("#") or (value.startswith("/") and not value.startswith("//")):
        return value
    return ""


class _ReportHTML(HTMLParser):
    def __init__(self, nonce, trusted, trusted_assets):
        super().__init__(convert_charrefs=False)
        self.nonce = nonce
        self.trusted = trusted
        self.trusted_assets = trusted_assets
        self.chunks = []
        self.script = None
        self.data_ids = set()
        self.seen = set()

    def handle_starttag(self, tag, attrs):
        self._tag(tag, attrs, ">")

    def handle_startendtag(self, tag, attrs):
        if tag != "script":
            self._tag(tag, attrs, "/>")

    def _tag(self, tag, attrs, end):
        source = dict(attrs)
        if tag == "script":
            self.script = (source, [])
            return
        if tag == "base" or (tag == "meta" and "http-equiv" in source):
            return
        clean = []
        for name, value in attrs:
            if name.startswith("on") or name in {"nonce", "srcdoc", "srcset", "ping"}:
                continue
            if name in {"href", "xlink:href", "src", "poster"}:
                if name == "src" and tag == "img" and (value or "").startswith("data:image/"):
                    pass
                elif not (value := _navigate(value)):
                    continue
            if value is None:
                clean.append(f" {name}")
            else:
                clean.append(f' {name}="{escape(value, quote=True)}"')
        self.chunks.append(f"<{tag}{''.join(clean)}{end}")

    def handle_endtag(self, tag):
        if tag == "script":
            if self.script is not None:
                attrs, body = self.script
                self.script = None
                self._finish_script(attrs, _script_bytes("".join(body)))
            return
        if tag != "base":
            self.chunks.append(f"</{tag}>")

    def _finish_script(self, attrs, body):
        script_type = (attrs.get("type") or "").lower()
        source = attrs.get("src")
        if script_type == "application/json" and attrs.get("id") in _DATA_SCRIPTS and not source:
            identifier = attrs["id"]
            self.data_ids.add(identifier)
            self.chunks.append(f'<script type="application/json" id="{identifier}">{body}</script>')
        elif source in self.trusted_assets and not body.strip():
            self.chunks.append(f'<script nonce="{self.nonce}" src="{source}" defer></script>')
        elif not source and body in self.trusted and script_type in {"", "text/javascript"}:
            self.seen.add(body)
            self.chunks.append(f'<script nonce="{self.nonce}">{body}</script>')

    def handle_data(self, data):
        if self.script is not None:
            self.script[1].append(data)
        else:
            self.chunks.append(data)

    def handle_entityref(self, name):
        self.chunks.append(f"&{name};")

    def handle_charref(self, name):
        self.chunks.append(f"&#{name};")

    def handle_decl(self, definition):
        if definition.casefold() == "doctype html":
            self.chunks.append("<!DOCTYPE html>")


def protect_report(html: str, language: str, *, feedback: bool = False) -> tuple[str, dict[str, str]]:
    """Authorize app code by exact content and attach a per-response nonce."""
    trusted, replacements = _known_scripts(language)
    nonce = token_urlsafe(24)
    report = _ReportHTML(nonce, trusted, _REPORT_ASSETS if feedback else set())
    report.feed(html)
    report.close()
    output = "".join(report.chunks)
    # Older reports can carry map data alongside older, unrecognized code.
    # Use the current trusted renderer with their original inert JSON.
    add = "".join(f'<script nonce="{nonce}">{current}</script>'
                  for identifier, (variants, current) in replacements.items()
                  if identifier in report.data_ids and not variants.intersection(report.seen))
    if add:
        output = output.replace("</body>", add + "</body>", 1) if "</body>" in output else output + add
    policy = (f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'self' 'unsafe-inline'; "
              "img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; "
              "base-uri 'none'; object-src 'none'; form-action 'none'; frame-ancestors 'self'")
    return output, {"Content-Security-Policy": policy, "X-Content-Type-Options": "nosniff",
                    "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"}
