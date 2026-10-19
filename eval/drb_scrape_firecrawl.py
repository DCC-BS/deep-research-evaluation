"""Run DeepResearch Bench's FACT scrape step with local Firecrawl instead of the Jina Reader API.

Full page text is kept (hard cap PAGE_CHARS, default 400k chars, against runaway pages);
eval/drb_focus.py then cuts each page down to the passages relevant to its cited statements.
Run with cwd = vendor/deep_research_bench.
"""

import os
import runpy
import sys

import requests

sys.path.insert(0, os.getcwd())
import utils.api  # noqa: E402  (vendor module, importable because cwd is the DRB checkout)

FIRECRAWL_URL = os.environ.get("FIRECRAWL_URL", "http://localhost:3002")
PAGE_CHARS = int(os.environ.get("PAGE_CHARS", "400000"))


def scrape_url(url: str) -> dict:
    try:
        r = requests.post(f"{FIRECRAWL_URL}/v2/scrape", timeout=120,
                          json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
                          headers={"Authorization": f"Bearer {os.environ.get('FIRECRAWL_API_KEY', '')}"})
        data = r.json().get("data") or {}
        md = data.get("markdown") or ""
        if not md:
            return {"url": url, "content": "", "error": r.json().get("error", f"HTTP {r.status_code}")}
        meta = data.get("metadata") or {}
        return {"url": url, "title": meta.get("title", ""), "description": meta.get("description", ""),
                "content": md[:PAGE_CHARS]}
    except Exception as e:
        return {"url": url, "content": "", "error": str(e)}


utils.api.scrape_url = scrape_url
runpy.run_module("utils.scrape", run_name="__main__")
