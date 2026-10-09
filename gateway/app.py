"""Token-metering gateway in front of vLLM.

OpenAI-compatible proxy that
- maps role aliases (gemma-think, gemma-fast, ...) to real models plus extra
  request fields such as chat_template_kwargs, so every framework gets a
  per-role thinking switch through the model name alone;
- attributes every request to a run tag taken from the API key
  ("<METER_API_KEY>:<run-tag>") or the X-Run-Tag header;
- appends one JSON line per request to $METER_LOG with token usage and latency;
- proxies Serper (POST /serper/search) with the real key held server-side,
  drops results from blocklisted domains (benchmark leakage) and logs every
  query per run tag to $SEARCH_LOG.
"""

import json
import os
import time
from pathlib import Path

import httpx
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

CONFIG = yaml.safe_load(Path(os.environ.get("METER_CONFIG", "/config/models.yaml")).read_text())
API_KEY = os.environ["METER_API_KEY"]
LOG_PATH = Path(os.environ.get("METER_LOG", "/logs/usage.jsonl"))
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

ALIASES: dict = CONFIG["aliases"]
BACKENDS: dict = CONFIG["backends"]
SERPER_KEY = os.environ.get("SERPER_API_KEY", "")
SEARCH_LOG = Path(os.environ.get("SEARCH_LOG", "/logs/search.jsonl"))
BLOCKLIST: list[str] = CONFIG.get("search_blocklist", [])

client = httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=1800, write=60, pool=60))
app = FastAPI()


def run_tag(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    key, _, tag = token.partition(":")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid meter key")
    return request.headers.get("x-run-tag") or tag or "untagged"


def resolve(model: str) -> tuple[dict, dict]:
    """Return (backend, alias) for a requested model name."""
    alias = ALIASES.get(model)
    if alias is None:
        raise HTTPException(status_code=404, detail=f"unknown model {model!r}; known: {sorted(ALIASES)}")
    return BACKENDS[alias["backend"]], alias


def merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in extra.items():
        out[k] = merge(out.get(k) or {}, v) if isinstance(v, dict) else v
    return out


def log(entry: dict, path: Path = LOG_PATH) -> None:
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def blocked(link: str) -> bool:
    return any(b in link for b in BLOCKLIST)


@app.post("/serper/search")
async def serper_search(request: Request):
    """Serper-compatible search. Clients send X-API-KEY: <METER_API_KEY>:<run-tag>."""
    key, _, tag = request.headers.get("x-api-key", "").partition(":")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid meter key")
    body = await request.json()
    started = time.time()
    r = await client.post("https://google.serper.dev/search", json=body,
                          headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"})
    data = r.json()
    organic = data.get("organic") or []
    kept = [o for o in organic if not blocked(o.get("link", ""))]
    data["organic"] = kept
    log({"ts": started, "run": tag or "untagged", "q": body.get("q"), "status": r.status_code,
         "results": [o.get("link") for o in kept], "dropped": len(organic) - len(kept)}, SEARCH_LOG)
    return JSONResponse(data, status_code=r.status_code)


FIRECRAWL_URL = os.environ.get("FIRECRAWL_URL", "http://firecrawl-api:3002")


async def _firecrawl(url: str, max_chars: int) -> str:
    try:
        r = await client.post(f"{FIRECRAWL_URL}/v2/scrape", timeout=90,
                              json={"url": url, "formats": ["markdown"], "onlyMainContent": True})
        return ((r.json().get("data") or {}).get("markdown") or "")[:max_chars]
    except (httpx.HTTPError, ValueError):
        return ""


@app.post("/tavily/search")
async def tavily_search(request: Request):
    """Tavily-compatible search backed by Serper (+ Firecrawl page text for search_depth=advanced),
    so engines that only ship a Tavily tool (NVIDIA Deep Researcher) use the same search stack."""
    key, _, tag = request.headers.get("authorization", "").removeprefix("Bearer ").partition(":")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid meter key")
    body = await request.json()
    query, n = body.get("query", ""), int(body.get("max_results") or 5)
    advanced = body.get("search_depth") == "advanced"
    started = time.time()
    r = await client.post("https://google.serper.dev/search", json={"q": query, "num": max(n, 5)},
                          headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"})
    organic = r.json().get("organic") or []
    kept = [o for o in organic if not blocked(o.get("link", ""))][:n]
    results = []
    for o in kept:
        content = o.get("snippet", "")
        if advanced:
            content = await _firecrawl(o["link"], 6000) or content
        results.append({"title": o.get("title", ""), "url": o.get("link", ""), "content": content,
                        "score": 1.0 - 0.05 * len(results), "raw_content": None})
    log({"ts": started, "run": tag or "untagged", "q": query, "status": r.status_code, "api": "tavily",
         "advanced": advanced, "results": [x["url"] for x in results], "dropped": len(organic) - len(kept)},
        SEARCH_LOG)
    return {"query": query, "answer": None, "images": [], "results": results,
            "response_time": round(time.time() - started, 2)}


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/v1/models")
async def models():
    return {"object": "list", "data": [{"id": name, "object": "model", "owned_by": "meter"} for name in ALIASES]}


@app.post("/v1/embeddings")
async def embeddings(request: Request):
    tag = run_tag(request)
    body = await request.json()
    backend, alias = resolve(body.get("model", ""))
    body["model"] = alias["model"]
    started = time.time()
    r = await client.post(f"{backend['base_url']}/embeddings", json=body)
    usage = r.json().get("usage", {}) if r.status_code == 200 else {}
    log({"ts": started, "run": tag, "kind": "embedding", "alias": alias["name"], "status": r.status_code,
         "prompt_tokens": usage.get("prompt_tokens", 0), "completion_tokens": 0,
         "latency_s": round(time.time() - started, 3)})
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/v1/chat/completions")
async def chat(request: Request):
    tag = run_tag(request)
    body = await request.json()
    backend, alias = resolve(body.get("model", ""))
    body["model"] = alias["model"]
    body = merge(body, alias.get("extra_body", {}))
    stream = bool(body.get("stream"))
    client_wants_usage = bool((body.get("stream_options") or {}).get("include_usage"))
    if stream:
        body["stream_options"] = {**(body.get("stream_options") or {}), "include_usage": True}
    started = time.time()
    url = f"{backend['base_url']}/chat/completions"
    meta = {"ts": started, "run": tag, "kind": "chat", "alias": alias["name"], "stream": stream}

    if not stream:
        r = await client.post(url, json=body)
        data = r.json()
        usage = data.get("usage") or {}
        log({**meta, "status": r.status_code, "prompt_tokens": usage.get("prompt_tokens", 0),
             "completion_tokens": usage.get("completion_tokens", 0), "latency_s": round(time.time() - started, 3)})
        return JSONResponse(data, status_code=r.status_code)

    async def relay():
        usage, status, first_token = {}, 200, None
        try:
            async with client.stream("POST", url, json=body) as r:
                status = r.status_code
                async for line in r.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            chunk = json.loads(line[6:])
                        except json.JSONDecodeError:
                            chunk = {}
                        if chunk.get("usage"):
                            usage = chunk["usage"]
                            # Drop the usage-only chunk if the client never asked for it;
                            # some clients choke on a chunk with empty choices.
                            if not chunk.get("choices") and not client_wants_usage:
                                continue
                        elif first_token is None and chunk.get("choices"):
                            first_token = time.time()
                    yield line + "\n"
        finally:
            log({**meta, "status": status, "prompt_tokens": usage.get("prompt_tokens", 0),
                 "completion_tokens": usage.get("completion_tokens", 0),
                 "ttft_s": round(first_token - started, 3) if first_token else None,
                 "latency_s": round(time.time() - started, 3)})

    return StreamingResponse(relay(), media_type="text/event-stream")
