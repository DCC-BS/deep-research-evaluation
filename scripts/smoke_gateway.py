#!/usr/bin/env python3
"""Smoke test for the metering gateway: aliases, thinking switch, JSON, streaming, tools, embeddings."""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("METER_URL", "http://localhost:4000/v1")


def env(key: str) -> str:
    for f in (ROOT / ".env", ROOT / ".env.example"):
        if f.exists():
            for line in f.read_text().splitlines():
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1]
    sys.exit(f"{key} not set")


KEY = f"{env('METER_API_KEY')}:smoke"


def post(path: str, body: dict, raw: bool = False):
    req = urllib.request.Request(f"{BASE}{path}", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        data = r.read().decode()
    return data if raw else json.loads(data)


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
    return ok


results = []
q = 'Antworte nur mit JSON der Form {"hauptort": "..."}: Was ist der Hauptort des Kantons Basel-Landschaft?'
for alias, expect_reasoning in (("gemma-think", True), ("gemma-fast", False)):
    d = post("/chat/completions", {"model": alias, "messages": [{"role": "user", "content": q}], "max_tokens": 1500})
    m = d["choices"][0]["message"]
    reasoning = m.get("reasoning_content") or m.get("reasoning") or ""
    content = (m.get("content") or "").strip().removeprefix("```json").removesuffix("```").strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = None
    results.append(check(f"{alias}: JSON answer", bool(parsed) and "Liestal" in str(parsed), repr(content[:80])))
    results.append(check(f"{alias}: reasoning {'present' if expect_reasoning else 'absent'}",
                         bool(reasoning) == expect_reasoning, f"{len(reasoning)} chars, usage={d['usage']}"))

s = post("/chat/completions", {"model": "gemma-fast", "stream": True, "max_tokens": 30,
                               "messages": [{"role": "user", "content": "Sag Hallo."}]}, raw=True)
lines = [line for line in s.splitlines() if line.startswith("data: ")]
results.append(check("stream ends with [DONE], usage chunk hidden", lines[-1] == "data: [DONE]"
                     and not any('"choices":[]' in line for line in lines), f"{len(lines)} events"))

d = post("/chat/completions", {
    "model": "gemma-fast", "max_tokens": 300,
    "messages": [{"role": "user", "content": "Suche im Web nach dem Budget 2026 des Kantons Basel-Stadt."}],
    "tools": [{"type": "function", "function": {"name": "web_search", "description": "Search the web",
               "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}}]})
calls = d["choices"][0]["message"].get("tool_calls") or []
results.append(check("tool call", bool(calls) and calls[0]["function"]["name"] == "web_search",
                     calls[0]["function"]["arguments"] if calls else "none"))

d = post("/embeddings", {"model": "qwen-embed", "input": ["Grosser Rat Basel-Stadt"]})
results.append(check("embeddings", len(d["data"][0]["embedding"]) > 0, f"dim={len(d['data'][0]['embedding'])}"))

try:
    urllib.request.urlopen(urllib.request.Request(f"{BASE}/chat/completions", data=b"{}", headers={
        "Authorization": "Bearer wrong:x", "Content-Type": "application/json"}))
    results.append(check("wrong key rejected", False))
except urllib.error.HTTPError as e:
    results.append(check("wrong key rejected", e.code == 401, str(e.code)))

log = ROOT / "logs" / "usage.jsonl"
tagged = [json.loads(line) for line in log.read_text().splitlines() if '"run": "smoke"' in line] if log.exists() else []
results.append(check("usage logged with run tag", len(tagged) >= 5 and all(e["prompt_tokens"] > 0 for e in tagged),
                     f"{len(tagged)} entries"))
sys.exit(0 if all(results) else 1)
