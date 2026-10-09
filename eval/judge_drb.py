"""Score a candidate's DeepResearch Bench reports with the official judges via OpenRouter.

  uv run python -m eval.judge_drb --candidate baseline-agent [--ids 90] [--no-fact]

RACE: GPT-5.5 (cleaner GPT-5.6 Luna), unchanged DRB pipeline.
FACT: GPT-5.4-mini, unchanged except scraping (local Firecrawl) and a relevance focus step that keeps
      the judge input per page at ~16k chars (see drb_focus.py).
Each judge run records its OpenRouter spend in results/<candidate>/drb/judge/cost.jsonl.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

import httpx

from eval.common import RESULTS, ROOT, read_jsonl

DRB = ROOT / "vendor" / "deep_research_bench"
QUERY_FILE = DRB / "data" / "prompt_data" / "query.jsonl"


def openrouter_usage() -> float:
    # Account-level counter; the per-key /key usage lags by minutes.
    r = httpx.get("https://openrouter.ai/api/v1/credits", timeout=30,
                  headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})
    return float(r.json()["data"]["total_usage"])


def sh(args: list[str], log) -> None:
    env = {**os.environ, "LLM_BACKEND": "openrouter", "PYTHONPATH": str(DRB)}
    log.write(f"\n$ {' '.join(args)}\n")
    log.flush()
    subprocess.run(args, cwd=DRB, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--ids", nargs="*", type=int)
    ap.add_argument("--fact-only", action="store_true", help="rerun FACT only")
    ap.add_argument("--no-fact", action="store_true", help="skip FACT (e.g. baseline-nosearch has no citations)")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    src = RESULTS / args.candidate / "drb" / "raw.jsonl"
    reports = read_jsonl(src)
    ids = set(args.ids) if args.ids else {r["id"] for r in reports}
    reports = [r for r in reports if r["id"] in ids]
    if not reports:
        sys.exit("no reports for these ids")

    work = RESULTS / args.candidate / "drb" / "judge" / ("ids-" + "-".join(map(str, sorted(ids))))
    raw_dir, clean_dir = work / "raw", work / "cleaned"
    for d in (raw_dir, clean_dir):
        d.mkdir(parents=True, exist_ok=True)
    name = args.candidate
    (raw_dir / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in reports))
    queries = [json.dumps(q, ensure_ascii=False) for q in read_jsonl(QUERY_FILE) if q["id"] in ids]
    (work / "query.jsonl").write_text("\n".join(queries) + "\n")
    py = sys.executable
    log = (work / "judge.log").open("a")
    before, started = openrouter_usage(), time.time()

    if not args.fact_only:
      sh([py, "-u", "deepresearch_bench_race.py", name, "--raw_data_dir", str(raw_dir), "--cleaned_data_dir",
        str(clean_dir), "--query_file", str(work / "query.jsonl"), "--output_dir", str(work / "race"),
        "--max_workers", str(args.workers), "--force"], log)
    race_cost = openrouter_usage() - before

    fact_cost = 0.0
    if not args.no_fact:
        f = work / "fact"
        f.mkdir(exist_ok=True)
        q, n = str(work / "query.jsonl"), str(args.workers)
        mid = openrouter_usage()
        sh([py, "-u", "-m", "utils.extract", "--raw_data_path", str(raw_dir / f"{name}.jsonl"),
            "--output_path", str(f / "extracted.jsonl"), "--query_data_path", q, "--n_total_process", n], log)
        sh([py, "-u", "-m", "utils.deduplicate", "--raw_data_path", str(f / "extracted.jsonl"),
            "--output_path", str(f / "deduplicated.jsonl"), "--query_data_path", q, "--n_total_process", n], log)
        sh([py, "-u", str(ROOT / "eval" / "drb_scrape_firecrawl.py"), "--raw_data_path", str(f / "deduplicated.jsonl"),
            "--output_path", str(f / "scraped.jsonl"), "--n_total_process", n], log)
        sh([py, "-u", str(ROOT / "eval" / "drb_focus.py"), str(f / "scraped.jsonl"), str(f / "focused.jsonl")], log)
        sh([py, "-u", "-m", "utils.validate", "--raw_data_path", str(f / "focused.jsonl"),
            "--output_path", str(f / "validated.jsonl"), "--query_data_path", q, "--n_total_process", n], log)
        sh([py, "-u", "-m", "utils.stat", "--input_path", str(f / "validated.jsonl"),
            "--output_path", str(f / "fact_result.txt")], log)
        fact_cost = openrouter_usage() - mid

    # OpenRouter usage can lag a few seconds behind the last call.
    time.sleep(10)
    total = openrouter_usage() - before
    cost = {"ids": sorted(ids), "reports": len(reports), "race_usd": round(race_cost, 4),
            "fact_usd": round(fact_cost, 4), "total_usd": round(total, 4), "minutes": round((time.time() - started) / 60, 1)}
    with (RESULTS / args.candidate / "drb" / "judge" / "cost.jsonl").open("a") as fh:
        fh.write(json.dumps(cost) + "\n")
    print(json.dumps(cost))
    print((work / "race" / "race_result.txt").read_text())
    if not args.no_fact:
        print((work / "fact" / "fact_result.txt").read_text())


if __name__ == "__main__":
    main()
