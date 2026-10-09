"""Shared helpers: paths, env, task loading, run tags, usage accounting, MCP client."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

METER_URL = os.environ.get("METER_URL", "http://localhost:4000")
FIRECRAWL_URL = os.environ.get("FIRECRAWL_URL", "http://localhost:3002")
USAGE_LOG = ROOT / "logs" / "usage.jsonl"
SEARCH_LOG = ROOT / "logs" / "search.jsonl"
RESULTS = ROOT / "results"


def read_jsonl(path: Path) -> list[dict]:
    """Read JSON Lines. Splits on "\\n" only: str.splitlines() also breaks on U+2028/U+0085,
    which occur inside JSON strings from scraped pages."""
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().split("\n") if line.strip()]


def meter_key(tag: str) -> str:
    """API key for the metering gateway; the part after ':' attributes usage to a run."""
    return f"{os.environ['METER_API_KEY']}:{tag}"


@dataclass
class Task:
    set: str
    id: str
    prompt: str
    language: str = "en"
    depth: str = "standard"
    sources: list[str] = field(default_factory=lambda: ["web"])


# Report contract for the German set, part of the task itself so every approach gets the same
# instructions. (Before, only baseline-agent's system prompt asked for summary / main part / open points,
# which mirrors two shared rubric criteria: docs/analysis/german-set.md.)
DE_REPORT_CONTRACT = (
    "\n\nAnforderungen an den Bericht: Deutsch mit Schweizer Rechtschreibung (kein ß). Gliederung: "
    "Zusammenfassung, Hauptteil, offene Punkte und Grenzen der Recherche. Belege jede Tatsachenaussage "
    "mit einer Quelle samt vollständiger URL; nenne bei Erlassen die SG- bzw. SR-Nummer, bei "
    "Grossratsgeschäften die Geschäftsnummer und bei Daten den Stand bzw. das Datum der Quelle."
)


def load_tasks(set_name: str, ids: list[str] | None = None, calibration: bool = False) -> list[Task]:
    cfg = yaml.safe_load((ROOT / "config" / "tasks.yaml").read_text())
    if set_name == "drb":
        c = cfg["drb"]
        wanted = c["calibration_ids"] if calibration else c["ids"]
        rows = read_jsonl(ROOT / c["query_file"])
        tasks = [Task("drb", str(r["id"]), r["prompt"], r["language"]) for r in rows if r["id"] in wanted]
    elif set_name == "de":
        data = json.loads((ROOT / cfg["de"]["file"]).read_text())
        tasks = [Task("de", t["id"], t["question"] + DE_REPORT_CONTRACT, "de", t["depth"], t["sources"])
                 for t in data["tasks"]]
        if calibration:
            tasks = tasks[:1]
    else:
        raise ValueError(f"unknown task set {set_name}")
    return [t for t in tasks if not ids or t.id in ids]


def load_variant(candidate: str, name: str) -> dict:
    """Tuning variant from config/variants.yaml ({} for the default configuration)."""
    if not name:
        return {}
    variants = yaml.safe_load((ROOT / "config" / "variants.yaml").read_text()) or {}
    try:
        return variants[candidate][name]
    except KeyError:
        raise ValueError(f"unknown variant {candidate}@{name}") from None


def mcp_config() -> dict:
    return yaml.safe_load((ROOT / "config" / "tasks.yaml").read_text())["mcp"]


def usage_for(tag: str, since: float = 0.0) -> dict:
    """Sum token usage and searches the gateway logged for one run tag, from `since` (epoch seconds) on,
    so a rerun of a failed task does not also count the failed attempt."""
    out = {"llm_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "embedding_tokens": 0, "searches": 0}
    for e in read_jsonl(USAGE_LOG):
        if e.get("run") != tag or e.get("ts", 0) < since:
            continue
        if e["kind"] == "embedding":
            out["embedding_tokens"] += e["prompt_tokens"]
        else:
            out["llm_calls"] += 1
            out["prompt_tokens"] += e["prompt_tokens"]
            out["completion_tokens"] += e["completion_tokens"]
    out["searches"] = sum(1 for e in read_jsonl(SEARCH_LOG) if e.get("run") == tag and e.get("ts", 0) >= since)
    out["total_tokens"] = out["prompt_tokens"] + out["completion_tokens"]
    return out


class MCPClient:
    """Minimal streamable-HTTP MCP client (initialize, tools/list, tools/call)."""

    def __init__(self, url: str, allow: list[str] | None = None, timeout: float = 120):
        self.url, self.allow = url, set(allow or [])
        self.http = httpx.Client(timeout=timeout, headers={"Accept": "application/json, text/event-stream",
                                                           "Content-Type": "application/json"})
        self.session = None
        self._id = 0
        r = self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "dr-eval", "version": "0.1"}}, raw=True)
        self.session = r.headers.get("mcp-session-id")
        if self.session:
            self.http.headers["mcp-session-id"] = self.session
        self._notify("notifications/initialized")

    def _notify(self, method: str):
        self.http.post(self.url, json={"jsonrpc": "2.0", "method": method})

    def _rpc(self, method: str, params: dict, raw: bool = False):
        self._id += 1
        r = self.http.post(self.url, json={"jsonrpc": "2.0", "id": self._id, "method": method, "params": params})
        r.raise_for_status()
        if raw:
            return r
        text = r.text
        if "text/event-stream" in r.headers.get("content-type", ""):
            text = next(line[6:] for line in reversed(text.splitlines()) if line.startswith("data: "))
        data = json.loads(text)
        if "error" in data:
            raise RuntimeError(data["error"])
        return data["result"]

    def tools(self) -> list[dict]:
        tools = self._rpc("tools/list", {})["tools"]
        return [t for t in tools if not self.allow or t["name"] in self.allow]

    def call(self, name: str, arguments: dict) -> str:
        res = self._rpc("tools/call", {"name": name, "arguments": arguments})
        return "\n".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
