"""Export a DigestResult to JSON / BibTeX (data portability)."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime


def to_dict(result) -> dict:
    return {
        "generated_at": getattr(result, "generated_at", ""),
        "profile": getattr(result, "config_profile", ""),
        "counts": {
            "items": len(getattr(result, "items", []) or []),
            "sections": {k: len(v) for k, v in (getattr(result, "sections", {}) or {}).items()},
        },
        "on_this_day": getattr(result, "on_this_day", []) or [],
        "sections": {
            k: [it.to_dict() for it in v]
            for k, v in (getattr(result, "sections", {}) or {}).items()
        },
    }


def write_json(result, path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_dict(result), f, ensure_ascii=False, indent=1)
    return path


def _key(it, year: str, idx: int) -> str:
    author = (it.authors[0].split()[-1] if it.authors and it.authors[0].strip() else "anon")
    word = re.sub(r"[^A-Za-z0-9]", "", (it.title or "untitled").split()[0])[:12] or "paper"
    base = f"{author}{year}{word}"
    base = re.sub(r"[^A-Za-z0-9]", "", base)
    return f"{base or 'neurodaily'}{idx}"


def _esc(s: str) -> str:
    return (s or "").replace("{", "\\{").replace("}", "\\}").replace("&", "\\&")


def to_bibtex(result) -> str:
    entries = []
    seen = set()
    idx = 0
    for it in getattr(result, "items", []) or []:
        if it.kind != "paper":
            continue
        if it.url and it.url in seen:
            continue
        seen.add(it.url or it.title)
        year = (it.date or str(datetime.now().year))[:4]
        key = _key(it, year, idx)
        idx += 1
        journal = (it.extra or {}).get("journal") or it.source
        fields = [
            f"  title = {{{_esc(it.title)}}}",
            f"  author = {{{_esc(' and '.join(it.authors))}}}",
            f"  journal = {{{_esc(journal)}}}",
            f"  year = {{{year}}}",
        ]
        if it.doi:
            fields.append(f"  doi = {{{_esc(it.doi)}}}")
        if it.url:
            fields.append(f"  url = {{{_esc(it.url)}}}")
        fields.append(f"  note = {{{_esc(it.source)}}}")
        entries.append("@article{" + key + ",\n" + ",\n".join(fields) + "\n}")
    return "\n\n".join(entries) + ("\n" if entries else "")


def write_bibtex(result, path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_bibtex(result))
    return path
