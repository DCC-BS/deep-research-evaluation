"""Generate reports for one candidate and one task set.

  uv run python -m eval.run --candidate baseline-agent --set drb [--calibration] [--ids 90 51] [--concurrency 2]
                            [--window 20:00-05:00]

Writes results/<candidate>/<set>/raw.jsonl ({"id","prompt","article"}, DeepResearch Bench format)
and runs.jsonl (runtime, tokens, searches, errors). Tasks already in raw.jsonl are skipped (resume).
"""

import argparse
import json
import re
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from eval.candidates.baselines import baseline_agent, baseline_nosearch
from eval.candidates.gpt_researcher import gpt_researcher
from eval.candidates.nvidia_dra import nvidia_dra
from eval.candidates.research_agent import research_agent
from eval.common import RESULTS, Task, load_tasks, load_variant, read_jsonl, usage_for

CANDIDATES = {
    "baseline-nosearch": baseline_nosearch,
    "baseline-agent": baseline_agent,
    "gpt-researcher": gpt_researcher,
    "nvidia-dra": nvidia_dra,
    "research-agent": research_agent,
}
_lock = threading.Lock()


_DATA_URI = re.compile(r"data:[a-zA-Z0-9.+/-]+;base64,[A-Za-z0-9+/=]+")
_B64_RUN = re.compile(r"[A-Za-z0-9+/=]{300,}")


def sanitize(article: str) -> tuple[str, int]:
    """Strip embedded data URIs and long base64 runs (GPT-Researcher DE-ST1 ended in 12k chars of base64).
    Returns the cleaned text and the number of characters removed, recorded per run."""
    cleaned = _B64_RUN.sub("[binary data removed]", _DATA_URI.sub("[embedded data removed]", article))
    return cleaned, len(article) - len(cleaned)


def in_window(window: str | None) -> bool:
    if not window:
        return True
    start, end = (datetime.strptime(x, "%H:%M").time() for x in window.split("-"))
    now = datetime.now().time()
    return start <= now or now < end if start > end else start <= now < end


def append(path, row: dict) -> None:
    with _lock, path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_task(candidate: str, task: Task, out_dir, window: str | None) -> None:
    while not in_window(window):
        time.sleep(60)
    tag = f"{candidate}:{task.set}:{task.id}"
    started = time.time()
    meta = {"id": task.id, "candidate": candidate, "set": task.set, "started": started}
    try:
        base, _, variant = candidate.partition("@")
        result = CANDIDATES[base](task, tag, variant=load_variant(base, variant))
        if len((result.get("article") or "").strip()) < 500:
            raise RuntimeError(f"empty or truncated report ({len(result.get('article') or '')} chars): "
                               f"{(result.get('log_tail') or '')[-800:]}")
        result["article"], meta["sanitized_chars"] = sanitize(result["article"])
        meta["status"] = "ok"
        append(out_dir / "raw.jsonl", {"id": int(task.id) if task.id.isdigit() else task.id,
                                       "prompt": task.prompt, "article": result["article"]})
        extra = {k: v for k, v in result.items() if k != "article"}
        if extra:
            append(out_dir / "artifacts.jsonl", {"id": task.id, **extra})
    except Exception as e:
        meta["status"] = "error"
        meta["error"] = f"{e}\n{traceback.format_exc()[-1500:]}"
    meta["runtime_s"] = round(time.time() - started, 1)
    meta.update(usage_for(tag, since=started))
    append(out_dir / "runs.jsonl", meta)
    print(f"[{candidate}] {task.set}:{task.id} {meta['status']} {meta['runtime_s']}s "
          f"{meta['total_tokens']:,} tok {meta['searches']} searches", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True, help=f"one of {sorted(CANDIDATES)}, optionally @<variant> from config/variants.yaml")
    ap.add_argument("--set", required=True, choices=["drb", "de"])
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--calibration", action="store_true")
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--window", help="only start tasks inside this local time window, e.g. 20:00-05:00")
    args = ap.parse_args()

    if args.candidate.partition("@")[0] not in CANDIDATES:
        ap.error(f"unknown candidate {args.candidate}")
    out_dir = RESULTS / args.candidate / args.set
    out_dir.mkdir(parents=True, exist_ok=True)
    done = set()
    if (out_dir / "raw.jsonl").exists():
        done = {str(r["id"]) for r in read_jsonl(out_dir / "raw.jsonl")}
    tasks = [t for t in load_tasks(args.set, args.ids, args.calibration) if t.id not in done]
    print(f"{len(tasks)} tasks to run ({len(done)} already done)", flush=True)
    with ThreadPoolExecutor(args.concurrency) as pool:
        for t in tasks:
            pool.submit(run_task, args.candidate, t, out_dir, args.window)


if __name__ == "__main__":
    main()
