"""Run one GPT-Researcher deep-research task. Reads a JSON job on stdin, writes a JSON result on stdout.

Job: {"query": str, "language": "en"|"de", "mcp": [{"name", "url"}], "breadth": int, "depth": int}
All endpoints and keys come from the environment set by eval/candidates/gpt_researcher.py.
"""

import asyncio
import contextlib
import json
import os
import sys


async def main() -> None:
    job = json.load(sys.stdin)
    os.environ["DEEP_RESEARCH_BREADTH"] = str(job.get("breadth", 3))
    os.environ["DEEP_RESEARCH_DEPTH"] = str(job.get("depth", 2))
    os.environ["LANGUAGE"] = "german" if job.get("language") == "de" else "english"
    mcp = [{"name": m["name"], "connection_url": m["url"]} for m in job.get("mcp", [])]
    if mcp:
        os.environ["RETRIEVER"] = os.environ["RETRIEVER"] + ",mcp"

    if os.environ.get("GPTR_OVERLAY") == "1":  # patched package copy, see build_overlay.py
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "overlay"))
    from gpt_researcher import GPTResearcher  # import after env is final; config reads env at init

    query = job["query"]
    if job.get("language") == "de":
        query += "\n\n(Bericht auf Deutsch, Schweizer Rechtschreibung ohne ß.)"
    researcher = GPTResearcher(query=query, report_type=job.get("report_type", "deep"), verbose=False, mcp_configs=mcp or None)
    # GPT-Researcher prints progress to stdout; keep stdout clean for the JSON result.
    with contextlib.redirect_stdout(sys.stderr):
        await researcher.conduct_research()
        report = await researcher.write_report()
    import gpt_researcher
    json.dump({"article": report, "sources": researcher.get_source_urls(),
               "package": os.path.dirname(gpt_researcher.__file__)}, sys.stdout)


if __name__ == "__main__":
    asyncio.run(main())
