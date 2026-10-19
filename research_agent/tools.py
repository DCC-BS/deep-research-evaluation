"""Search (Serper-compatible endpoint), fetch (Firecrawl), passage focus (embeddings) and MCP access."""

import asyncio
import json
import math
from urllib.parse import urlparse

import httpx


def domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def domain_match(url: str, domains: list[str]) -> bool:
    d = domain(url)
    return any(d == x or d.endswith("." + x) for x in domains)


class Tools:
    def __init__(self, search_url: str, search_key: str, firecrawl_url: str, firecrawl_key: str = ""):
        self.search_url, self.search_key = search_url, search_key
        self.firecrawl_url, self.firecrawl_key = firecrawl_url, firecrawl_key
        self.http = httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=150, write=30, pool=60))

    async def search(self, q: str, lang: str = "de", num: int = 8) -> list[dict]:
        body = {"q": q, "num": num, "gl": "ch", "hl": lang if lang in ("de", "fr", "it", "en") else "de"}
        try:
            r = await self.http.post(self.search_url, json=body, headers={"X-API-KEY": self.search_key})
            return [{"title": o.get("title", ""), "url": o.get("link", ""), "snippet": o.get("snippet", "")}
                    for o in (r.json().get("organic") or []) if o.get("link")]
        except (httpx.HTTPError, ValueError):
            return []

    async def fetch(self, url: str) -> tuple[str, str]:
        """Returns (title, markdown); empty markdown if the page could not be fetched."""
        try:
            r = await self.http.post(f"{self.firecrawl_url}/v2/scrape",
                                     json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
                                     headers={"Authorization": f"Bearer {self.firecrawl_key}"})
            data = r.json().get("data") or {}
            return (data.get("metadata") or {}).get("title", ""), data.get("markdown") or ""
        except (httpx.HTTPError, ValueError):
            return "", ""


async def focus(llm, text: str, queries: list[str], budget_chars: int = 8000, chunk: int = 1200) -> str:
    """Keep the passages most similar to the queries (document order), so long pages are not cut at the head."""
    if len(text) <= budget_chars:
        return text
    chunks = [text[i:i + chunk] for i in range(0, len(text), chunk - 150)]
    vecs = await llm.embed(queries + chunks)
    qv, cv = vecs[:len(queries)], vecs[len(queries):]

    def cos(a, b):
        return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a) * sum(y * y for y in b)) or 1)

    score = [max(cos(c, q) for q in qv) for c in cv]
    keep, used = [], 0
    for i in sorted(range(len(chunks)), key=lambda i: -score[i]):
        if used + len(chunks[i]) > budget_chars:
            break
        keep.append(i)
        used += len(chunks[i])
    return "\n[...]\n".join(chunks[i] for i in sorted(keep))


class MCPClient:
    """Minimal streamable-HTTP MCP client (initialize, tools/list, tools/call), sync httpx in a thread."""

    def __init__(self, url: str, allow: list[str] | None = None, timeout: float = 120):
        self.url, self.allow = url, set(allow or [])
        self.http = httpx.Client(timeout=timeout, headers={"Accept": "application/json, text/event-stream",
                                                           "Content-Type": "application/json"})
        self._id = 0
        r = self._post("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                      "clientInfo": {"name": "research-agent", "version": "0.1"}})
        if sid := r.headers.get("mcp-session-id"):
            self.http.headers["mcp-session-id"] = sid
        self.http.post(self.url, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        self._tools = None

    def _post(self, method: str, params: dict):
        self._id += 1
        r = self.http.post(self.url, json={"jsonrpc": "2.0", "id": self._id, "method": method, "params": params})
        r.raise_for_status()
        return r

    def _rpc(self, method: str, params: dict):
        r = self._post(method, params)
        text = r.text
        if "text/event-stream" in r.headers.get("content-type", ""):
            text = next(line[6:] for line in reversed(text.splitlines()) if line.startswith("data: "))
        data = json.loads(text)
        if "error" in data:
            raise RuntimeError(data["error"])
        return data["result"]

    def tools(self) -> list[dict]:
        if self._tools is None:
            self._tools = [t for t in self._rpc("tools/list", {})["tools"] if not self.allow or t["name"] in self.allow]
        return self._tools

    def call(self, name: str, arguments: dict) -> str:
        res = self._rpc("tools/call", {"name": name, "arguments": arguments})
        return "\n".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")

    async def acall(self, name: str, arguments: dict) -> str:
        return await asyncio.to_thread(self.call, name, arguments)
