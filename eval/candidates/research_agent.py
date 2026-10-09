"""Our own research-agent (research_agent/, docs/research-agent-design.md), called in-process.

Benchmark mode like the other candidates: no clarifying questions, plan auto-approved.
Preset per task: DRB -> web_survey; German set by category.
"""

import asyncio
import json
import os

from eval.common import DE_REPORT_CONTRACT, FIRECRAWL_URL, METER_URL, ROOT, Task, meter_key
from research_agent import LLM, ResearchAgent, Tools, load_config

DE_PRESETS = {"Recht": "rechtsrecherche", "Grossrat": "grossrat", "Statistik": "statistik",
              "Web-Inhalte": "verwaltung_web", "Strategien": "verwaltung_web"}
_DE_CATEGORY = {t["id"]: t["category"] for t in json.loads((ROOT / "testsets" / "de-admin.json").read_text())["tasks"]}


def preset_for(task: Task) -> str:
    return DE_PRESETS.get(_DE_CATEGORY.get(task.id, ""), "verwaltung_web") if task.set == "de" else "web_survey"


def research_agent(task: Task, tag: str, variant: dict | None = None) -> dict:
    variant = variant or {}
    cfg = load_config(ROOT / "config" / variant.get("presets_file", "presets.yaml"))
    for name, value in (variant.get("budget") or {}).items():   # budget overrides for tuning
        for b in cfg.budgets.values():
            setattr(b, name, value)
    for name, over in (variant.get("preset_overrides") or {}).items():   # preset overrides for tuning
        p = cfg.presets[name]
        for k, v in over.items():
            setattr(p, k, {**getattr(p, k), **v} if isinstance(v, dict) else v)
    llm = LLM(base_url=f"{METER_URL}/v1", api_key=meter_key(tag))
    tools = Tools(search_url=f"{METER_URL}/serper/search", search_key=meter_key(tag),
                  firecrawl_url=FIRECRAWL_URL, firecrawl_key=os.environ.get("FIRECRAWL_API_KEY", ""))
    agent = ResearchAgent(cfg, llm, tools)
    depth = variant.get("depth") or (task.depth if task.set == "de" else "standard")
    preset = variant.get("preset") or preset_for(task)
    async def go():
        try:
            # the report contract shapes the writing only; planning and research see the question
            question, requirements = task.prompt, ""
            if DE_REPORT_CONTRACT in task.prompt:
                question = task.prompt.replace(DE_REPORT_CONTRACT, "").strip()
                requirements = DE_REPORT_CONTRACT.strip()
            return await agent.run(question, preset, depth, requirements=requirements)
        finally:  # close HTTP clients inside the loop (else "Event loop is closed" noise at exit)
            await llm.client.close()
            await tools.http.aclose()

    res = asyncio.run(go())
    return {"article": res.report, "preset": preset, "depth": depth, "plan": res.plan, "stats": res.stats,
            "usage_by_step": res.usage["by_step"], "evidence": res.ledger}
