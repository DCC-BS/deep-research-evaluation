"""Baselines.

baseline-nosearch: Gemma answers from its own knowledge (lower bound; RACE must beat it by >= 3 points).
baseline-agent:    single tool-calling loop with web search, page fetch and MCP tools, close to what
                   Open WebUI's native agentic web search does today (Bebbi Bot "web-suche").
"""

import json
import os

import httpx
from openai import OpenAI

from eval.common import FIRECRAWL_URL, METER_URL, MCPClient, Task, mcp_config, meter_key

REPORT_RULES = {
    "en": "Write a thorough, well-structured research report in English that fully answers the request. ",
    # Structure and spelling for German tasks come from the task's report contract (eval/common.py).
    "de": "Schreibe einen gründlichen, gut strukturierten Recherchebericht auf Deutsch. ",
}
CITE_RULES = {
    "en": ("Support every factual statement with a numbered citation like [1] and end with a 'References' "
           "section listing each number with its full URL."),
    "de": ("Belege jede Tatsachenaussage mit einer nummerierten Quelle wie [1] und schliesse mit einem "
           "Abschnitt 'Quellen', der jede Nummer mit der vollständigen URL auflistet."),
}


def _client(tag: str) -> OpenAI:
    return OpenAI(base_url=f"{METER_URL}/v1", api_key=meter_key(tag), timeout=1800)


def baseline_nosearch(task: Task, tag: str, variant: dict | None = None) -> dict:
    lang = "de" if task.language == "de" else "en"
    rules = REPORT_RULES[lang] + "You have no tools; answer from your own knowledge."
    r = _client(tag).chat.completions.create(
        model="gemma-think", max_tokens=16000,
        messages=[{"role": "system", "content": rules}, {"role": "user", "content": task.prompt}])
    return {"article": r.choices[0].message.content or ""}


WEB_TOOLS = [
    {"type": "function", "function": {
        "name": "web_search", "description": "Search the web. Returns titles, URLs and snippets.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "fetch_page", "description": "Fetch a web page as Markdown (truncated).",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
]


def _web_search(query: str, tag: str, lang: str) -> str:
    body = {"q": query, "num": 8, **({"gl": "ch", "hl": "de"} if lang == "de" else {})}
    r = httpx.post(f"{METER_URL}/serper/search", json=body, timeout=30, headers={"X-API-KEY": meter_key(tag)})
    hits = r.json().get("organic", [])
    return "\n\n".join(f"- {h.get('title')}\n  {h.get('link')}\n  {h.get('snippet', '')}" for h in hits) or "no results"


def _fetch(url: str, max_chars: int = 12000) -> str:
    try:
        r = httpx.post(f"{FIRECRAWL_URL}/v2/scrape", timeout=120,
                       json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
                       headers={"Authorization": f"Bearer {os.environ.get('FIRECRAWL_API_KEY', '')}"})
        md = (r.json().get("data") or {}).get("markdown") or ""
        return md[:max_chars] or f"could not fetch {url}"
    except httpx.HTTPError as e:
        return f"fetch failed: {e}"


def baseline_agent(task: Task, tag: str, variant: dict | None = None, max_steps: int = 16) -> dict:
    lang = "de" if task.language == "de" else "en"
    tools = list(WEB_TOOLS)
    mcp: dict[str, MCPClient] = {}
    for src in task.sources:
        if src.startswith("mcp:"):
            name = src[4:]
            conf = mcp_config()[name]
            client = MCPClient(conf["url"], conf.get("allow"))
            for t in client.tools():
                fname = f"{name.replace('-', '_')}__{t['name']}"
                mcp[fname] = (client, t["name"])
                tools.append({"type": "function", "function": {
                    "name": fname, "description": (t.get("description") or "")[:900],
                    "parameters": t.get("inputSchema") or {"type": "object", "properties": {}}}})

    llm = _client(tag)
    system = ("You are a research agent. Use the tools to search, read sources and collect evidence, "
              f"then write the final report. You can make up to {max_steps} tool calls. "
              + REPORT_RULES[lang] + CITE_RULES[lang])
    messages = [{"role": "system", "content": system}, {"role": "user", "content": task.prompt}]
    steps, trail = 0, []
    while True:
        r = llm.chat.completions.create(model="gemma-think", messages=messages, max_tokens=16000,
                                        tools=tools if steps < max_steps else None)
        msg = r.choices[0].message
        if not msg.tool_calls:
            return {"article": msg.content or "", "trail": trail}
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            steps += 1
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            name = tc.function.name
            try:
                if name == "web_search":
                    out = _web_search(args.get("query", ""), tag, lang)
                elif name == "fetch_page":
                    out = _fetch(args.get("url", ""))
                elif name in mcp:
                    client, tool = mcp[name]
                    out = client.call(tool, args)[:12000]
                else:
                    out = f"unknown tool {name}"
            except Exception as e:  # tool errors go back to the model
                out = f"tool error: {e}"
            trail.append({"tool": name, "args": args})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": out})
        if steps >= max_steps:
            messages.append({"role": "user", "content": "Tool budget used up. Write the final report now."})
