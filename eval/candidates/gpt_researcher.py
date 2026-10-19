"""GPT-Researcher (v3.7.0, Apache-2.0) in deep-research mode, run in its own venv per task."""

import json
import os
import subprocess

from eval.common import FIRECRAWL_URL, METER_URL, ROOT, Task, mcp_config, meter_key

CANDIDATE_DIR = ROOT / "candidates" / "gpt-researcher"
# Standard depth = GPT-Researcher defaults (breadth 3, depth 2); quick and deep for the depth knob (F3).
DEPTHS = {"quick": (2, 1), "standard": (3, 2), "deep": (4, 3)}


def gpt_researcher(task: Task, tag: str, variant: dict | None = None, timeout_s: int = 7200) -> dict:
    variant = variant or {}
    breadth, depth = variant.get("breadth_depth") or DEPTHS.get(task.depth, DEPTHS["standard"])
    mcp = [{"name": s[4:], "url": mcp_config()[s[4:]]["url"]} for s in task.sources if s.startswith("mcp:")]
    env = {
        **os.environ,
        "OPENAI_BASE_URL": f"{METER_URL}/v1",
        "OPENAI_API_KEY": meter_key(tag),
        # Role mapping: decisions/summaries -> fast, planning/writing -> thinking.
        "FAST_LLM": "openai:gemma-fast",
        "SMART_LLM": "openai:gemma-think",
        "STRATEGIC_LLM": "openai:gemma-think",
        "EMBEDDING": "openai:qwen-embed",
        "RETRIEVER": "serper",
        "SERPER_API_BASE": f"{METER_URL}/serper",
        "SERPER_API_KEY": meter_key(tag),
        **({"SERPER_REGION": "ch", "SERPER_LANGUAGE": "de"} if task.language == "de" else {}),
        "SCRAPER": "firecrawl",
        "FIRECRAWL_SERVER_URL": FIRECRAWL_URL,
        "FIRECRAWL_API_KEY": os.environ.get("FIRECRAWL_API_KEY", "fc-local-dev"),
        # Gemma has a 128k context; the defaults (6k/12k/8k) are sized for small GPT models.
        "FAST_TOKEN_LIMIT": "8000",
        "SMART_TOKEN_LIMIT": "16000",
        "STRATEGIC_TOKEN_LIMIT": "16000",
        "TOTAL_WORDS": "2500",
        # writer context cap of the patched overlay; German text needs more tokens per word (128k context)
        "GPTR_MAX_CONTEXT_WORDS": "20000" if task.language == "de" else "35000",
        # MCP tool allowlist (only honoured by the patched overlay, see build_overlay.py patch 4).
        "GPTR_MCP_ALLOW": ",".join(t for s in task.sources if s.startswith("mcp:")
                                   for t in mcp_config()[s[4:]].get("allow", [])),
        **{k: str(v) for k, v in (variant.get("env") or {}).items()},
    }
    job = {"report_type": variant.get("report_type", "deep"), "query": task.prompt, "language": task.language, "mcp": mcp, "breadth": breadth, "depth": depth}
    def attempt():
        return subprocess.run([str(CANDIDATE_DIR / ".venv" / "bin" / "python"), str(CANDIDATE_DIR / "run_one.py")],
                              input=json.dumps(job), capture_output=True, text=True, env=env, timeout=timeout_s)

    proc = attempt()
    if "Failed to get response from openai API" in proc.stderr and env.get("GPTR_OVERLAY") == "1":
        # writer prompt overflowed Gemma's 128k context (vLLM 400): retry once with 40% less writer context;
        # the tokens of both attempts count towards this task
        env["GPTR_MAX_CONTEXT_WORDS"] = str(int(int(env["GPTR_MAX_CONTEXT_WORDS"]) * 0.6))
        proc = attempt()
    if proc.returncode != 0:
        raise RuntimeError(f"gpt-researcher failed: {proc.stderr[-2000:]}")
    out = json.loads(proc.stdout)
    return {"article": out["article"], "sources": out.get("sources", []), "package": out.get("package"),
            "log_tail": proc.stderr[-1500:]}
