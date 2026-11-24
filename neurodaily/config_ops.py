"""Agent-friendly configuration operations.

Design goal: a non-technical user can ask an agent to "make me an oncology
digest"; the agent only needs deterministic, non-interactive commands:

    neurodaily config schema                  # machine-readable JSON Schema
    neurodaily config apply patch.json --dry-run   # preview + validate
    neurodaily config apply patch.json        # write if valid
    neurodaily run --profile oncology         # use that profile

Everything returns plain text + exit codes so an agent can loop until green.
"""
from __future__ import annotations

import copy
import difflib
import json
import os
from contextlib import nullcontext

from .config import Config, DEFAULT_CONFIG, config_lock_path, write_config
from .file_lock import file_lock
from .schema import ConfigModel, validate


def config_dir() -> str:
    return os.path.dirname(Config.default_path())


def profiles_dir() -> str:
    return os.path.join(config_dir(), "profiles")


def profile_path(name: str) -> str:
    return os.path.join(profiles_dir(), f"{name}.json")


def deep_merge(base, patch):
    """RFC-7386-like merge: dicts merge, lists/scalars replace, null deletes."""
    if isinstance(patch, dict):
        out = copy.deepcopy(base) if isinstance(base, dict) else {}
        for k, v in patch.items():
            if v is None:
                out.pop(k, None)
            else:
                out[k] = deep_merge(out.get(k), v)
        return out
    return copy.deepcopy(patch)


def _diff(before: dict, after: dict) -> str:
    a = json.dumps(before, ensure_ascii=False, indent=2).splitlines()
    b = json.dumps(after, ensure_ascii=False, indent=2).splitlines()
    return "\n".join(difflib.unified_diff(a, b, fromfile="before", tofile="after", lineterm=""))


def apply_patch(path: str, patch: dict, dry_run: bool = False) -> tuple[bool, list[str], str]:
    """Merge `patch` into the config at `path`. Returns (ok, errors, diff)."""
    if not isinstance(patch, dict):
        return False, ["patch must be a JSON object"], ""
    lock = nullcontext() if dry_run else file_lock(config_lock_path(path))
    with lock:
        return _apply_patch(path, patch, dry_run)


def _apply_patch(path, patch, dry_run):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                base = json.load(f)
        except json.JSONDecodeError as exc:
            return False, [f"existing config is not valid JSON: {exc}"], ""
    else:
        base = DEFAULT_CONFIG().to_dict()

    merged = deep_merge(base, patch)
    errs = validate(merged)
    diff = _diff(base, merged)
    if errs:
        return False, errs, diff
    if not dry_run:
        write_config(path, merged)
    return True, [], diff


def list_profiles() -> list[str]:
    d = profiles_dir()
    if not os.path.isdir(d):
        return []
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))


def new_profile(name: str, from_path: str | None = None) -> str:
    src = from_path or Config.default_path()
    if os.path.exists(src):
        with open(src, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = DEFAULT_CONFIG().to_dict()
    path = profile_path(name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "x", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def schema_json() -> dict:
    return ConfigModel.model_json_schema()


def describe() -> dict:
    """Compact, agent-readable capability map."""
    return {
        "commands": [
            "neurodaily config schema [--out PATH]",
            "neurodaily config apply PATCH.json [--dry-run] [--profile NAME]",
            "neurodaily config validate [--profile NAME]",
            "neurodaily profile list|new NAME|path NAME|show NAME",
            "neurodaily profile export [NAME] [-o PATH]",
            "neurodaily profile import PATH [--name NAME] [--mode merge|replace] [--dry-run]",
            "neurodaily profile validate PATH [--json]",
            "neurodaily profile doctor NAME [--json]",
            "neurodaily run --profile NAME [--demo]",
        ],
        "patch_semantics": "dicts merge, lists replace, null deletes",
        "required": ["disciplines (>=1, each needs keywords/mesh/arxiv/bio when enabled)"],
        "optional": ["global_keywords", "search", "sources", "journals", "policy_feeds",
                     "output", "scheduled", "profile"],
        "search": {"query": "paper expression", "sets": "shared numbered sets",
                   "rules": {"news": "expression", "policy": "expression", "trial": "expression"}},
        "sources": {
            "builtin": ["journal", "arxiv", "pubmed", "biorxiv",
                        "fda_drugs", "fda_devices", "trials", "policy"],
            "opt_in": ["europe_pmc", "openalex", "gdelt", "nih_brain", "crossref"],
            "source_query": ["trials", "europe_pmc", "openalex", "gdelt", "nih_brain"],
            "policy_feed_kinds": "sources.policy.feed_kinds maps policy feed URLs to content kinds",
            "generic": {
                "type": "rss | json_api",
                "rss_keys": ["url", "kind", "max_results", "lookback_days"],
                "json_keys": ["url", "items_path", "map", "kind"],
            },
        },
        "kinds": ["paper", "drug", "device", "trial", "news", "policy", "conference", "funding"],
    }
