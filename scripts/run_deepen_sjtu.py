"""Run bulk LLM expansion using the local SJTU OpenAI-compatible gateway.

Reuses the apiKey/baseURL already configured for opencode; nothing is printed.

Env:
    LIMIT        optional max number of entries to expand this run
    CONCURRENCY  parallel requests (default 4)
    MODEL        default deepseek-chat
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from neurodaily.deepen import expand_llm  # noqa: E402

cfg = json.load(open(os.path.expanduser("~/.config/opencode/opencode.json"), encoding="utf-8"))
p = cfg["provider"]["sjtu"]
opts = p["options"]

expand_llm(
    limit=int(os.environ["LIMIT"]) if os.environ.get("LIMIT") else None,
    model=os.environ.get("MODEL", "deepseek-chat"),
    base_url=opts["baseURL"],
    api_key=opts["apiKey"],
    concurrency=int(os.environ.get("CONCURRENCY", "4")),
)
