"""Build results/viewer.html: inspect tasks, reports, scores, citations and searches; compare two approaches.

  uv run python -m eval.viewer        # rebuild after new runs or judge results, then open results/viewer.html

Everything is embedded into one self-contained HTML file (marked + DOMPurify from cdnjs for Markdown).
"""

import ast
import json
from collections import defaultdict

from eval.common import RESULTS, ROOT, SEARCH_LOG, load_tasks, read_jsonl

DRB = ROOT / "vendor" / "deep_research_bench"
REFERENCE = "reference (Gemini DR)"


def jl(path):
    return read_jsonl(path)


def parse_listish(v):
    """FACT files store some fields as Python reprs ("['a', 'b']", "None")."""
    if isinstance(v, str):
        try:
            return ast.literal_eval(v)
        except (ValueError, SyntaxError):
            return v
    return v


def collect() -> dict:
    tasks = []
    for set_name in ("drb", "de"):
        for t in load_tasks(set_name):
            tasks.append({"set": set_name, "id": t.id, "prompt": t.prompt, "language": t.language,
                          "depth": t.depth, "sources": t.sources})
    de_meta = {t["id"]: t for t in json.loads((ROOT / "testsets" / "de-admin.json").read_text())["tasks"]}
    for t in tasks:
        if t["set"] == "de":
            t["category"] = de_meta[t["id"]]["category"]
            t["criteria"] = de_meta[t["id"]]["criteria"]

    searches = defaultdict(list)
    for e in jl(SEARCH_LOG):
        searches[e.get("run", "")].append({"q": e.get("q"), "n": len(e.get("results") or []),
                                           "api": e.get("api", "serper")})

    cells: dict[str, dict] = {}
    candidates = sorted(p.name for p in RESULTS.iterdir() if p.is_dir())
    for cand in candidates:
        for set_name in ("drb", "de"):
            base = RESULTS / cand / set_name
            for r in jl(base / "raw.jsonl"):
                cells.setdefault(f"{cand}|{set_name}|{r['id']}", {})["article"] = r["article"]
            for r in jl(base / "runs.jsonl"):  # latest run wins
                c = cells.setdefault(f"{cand}|{set_name}|{r['id']}", {})
                c["run"] = {k: r.get(k) for k in ("status", "runtime_s", "llm_calls", "prompt_tokens",
                                                  "completion_tokens", "total_tokens", "searches")}
                if r.get("status") == "error":
                    c["run"]["error"] = (r.get("error") or "")[:1500]
                c["searches"] = searches.get(f"{cand}:{set_name}:{r['id']}", [])
            for f in sorted((base / "judge").glob("ids-*/race/raw_results.jsonl")):
                for r in jl(f):
                    cells.setdefault(f"{cand}|{set_name}|{r['id']}", {})["race"] = {
                        k: round(100 * r[k], 1) for k in ("overall_score", "comprehensiveness", "insight",
                                                          "instruction_following", "readability") if k in r}
            for f in sorted((base / "judge").glob("ids-*/fact/validated.jsonl")):
                for d in jl(f):
                    cits, sup, chk = [], 0, 0
                    for url, c in (d.get("citations_deduped") or {}).items():
                        facts = parse_listish(c.get("facts")) or []
                        res = parse_listish(c.get("validate_res")) or []
                        verdicts = [x.get("result") for x in res] if isinstance(res, list) else []
                        for v in verdicts:
                            if v != "unknown":
                                chk += 1
                                sup += v == "supported"
                        cits.append({"url": url, "facts": facts if isinstance(facts, list) else [str(facts)],
                                     "verdicts": verdicts})
                    cells.setdefault(f"{cand}|{set_name}|{d['id']}", {})["fact"] = {
                        "accuracy": round(100 * sup / chk, 1) if chk else None, "supported": sup,
                        "checked": chk, "citations": cits}
            for r in jl(base / "judge.jsonl"):  # German rubric
                cells.setdefault(f"{cand}|{set_name}|{r['id']}", {})["rubric"] = {
                    "pct": r["rubric_pct"], "eszett": r["eszett"], "cited_urls": r["cited_urls"],
                    "verdict": r["verdict"]}

    # DRB reference reports (what RACE compares against).
    prompts = {t["prompt"]: t["id"] for t in tasks if t["set"] == "drb"}
    for r in jl(DRB / "data" / "test_data" / "cleaned_data" / "reference.jsonl"):
        if r["prompt"] in prompts:
            cells[f"{REFERENCE}|drb|{prompts[r['prompt']]}"] = {"article": r["article"]}
    return {"candidates": candidates + [REFERENCE], "tasks": tasks, "cells": cells,
            "rubric_common": json.loads((ROOT / "testsets" / "de-admin.json").read_text())["rubric_common"]}


def main() -> None:
    data = collect()
    html = (ROOT / "eval" / "viewer_template.html").read_text()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = RESULTS / "viewer.html"
    out.write_text(html.replace("/*__DATA__*/null", payload))
    n = sum(1 for k in data["cells"] if not k.startswith(REFERENCE) and "article" in data["cells"][k])
    print(f"wrote {out} ({out.stat().st_size // 1024} KiB, {n} reports, {len(data['tasks'])} tasks)")


if __name__ == "__main__":
    main()
