"""Aggregate results per candidate against the pass gates of the requirements spec.

  uv run python -m eval.report [--ids 51 53 ...]   -> prints a Markdown table, writes results/summary.json
"""

import argparse
import json
import re
import statistics

from eval.common import RESULTS, read_jsonl

GATES = {"race": 43.0, "race_margin": 3.0, "citation_accuracy": 60.0, "effective_citations": 20.0,
         "tokens_median_max": 1_000_000, "tokens_p90_max": 1_500_000, "runtime_median_max_min": 20.0}


def jl(path):
    return read_jsonl(path)


def race_scores(cand: str, ids: set | None) -> dict:
    """Per-task RACE from every judge run directory (latest wins)."""
    per_task = {}
    for f in sorted((RESULTS / cand / "drb" / "judge").glob("ids-*/race/raw_results.jsonl")):
        for r in jl(f):
            per_task[r["id"]] = r
    rows = [r for i, r in per_task.items() if not ids or i in ids]
    if not rows:
        return {}
    key = "overall_score"
    return {"n": len(rows), "race": round(100 * statistics.mean(r[key] for r in rows), 1)}


def fact_scores(cand: str, ids: set | None) -> dict:
    total, valid, n = 0, 0, 0
    per_task = {}
    for f in sorted((RESULTS / cand / "drb" / "judge").glob("ids-*/fact/validated.jsonl")):
        for d in jl(f):
            per_task[d["id"]] = d
    for i, d in per_task.items():
        if ids and i not in ids:
            continue
        n += 1
        for c in (d.get("citations_deduped") or {}).values():
            if c.get("validate_error") is not None:
                continue
            for r in c.get("validate_res") or []:
                if r["result"] != "unknown":
                    total += 1
                    valid += r["result"] == "supported"
    if not n:
        return {}
    return {"citation_accuracy": round(100 * valid / total, 1) if total else None,
            "effective_citations": round(valid / n, 1)}


def run_stats(cand: str, set_name: str, ids: set | None) -> dict:
    latest = {str(r["id"]): r for r in jl(RESULTS / cand / set_name / "runs.jsonl")}  # reruns replace failures
    runs = [r for i, r in latest.items() if not ids or i in ids]
    ok = [r for r in runs if r["status"] == "ok"]
    if not runs:
        return {}
    tok = sorted(r["total_tokens"] for r in ok) or [0]
    return {"runs": len(runs), "errors": len(runs) - len(ok),
            "tokens_median": int(statistics.median(tok)), "tokens_p90": tok[min(len(tok) - 1, int(0.9 * len(tok)))],
            "runtime_median_min": round(statistics.median(r["runtime_s"] for r in ok) / 60, 1) if ok else None,
            "searches_median": int(statistics.median(r["searches"] for r in ok)) if ok else 0}


def de_scores(cand: str) -> dict:
    rows = {r["id"]: r for r in jl(RESULTS / cand / "de" / "judge.jsonl")}
    if not rows:
        return {}
    return {"de_rubric": round(statistics.mean(r["rubric_pct"] for r in rows.values()), 1),
            "de_n": len(rows), "de_eszett": sum(r["eszett"] for r in rows.values())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", help="restrict DRB metrics to these task ids")
    args = ap.parse_args()
    ids = set(args.ids) if args.ids else None
    num_ids = {int(i) for i in ids} if ids else None
    summary = {}
    for cand_dir in sorted(p for p in RESULTS.iterdir() if p.is_dir()):
        c = cand_dir.name
        summary[c] = {**race_scores(c, num_ids), **fact_scores(c, num_ids), **run_stats(c, "drb", ids), **de_scores(c)}
    base = summary.get("baseline-nosearch", {}).get("race")
    print("| Candidate | RACE | Cit. acc. % | Eff. cit. | Tokens median | Tokens p90 | Runtime min | Errors | DE rubric % |")
    print("|---|---|---|---|---|---|---|---|---|")
    for c, s in summary.items():
        race = s.get("race")
        race_ok = race is not None and race >= GATES["race"] and (base is None or c == "baseline-nosearch" or race >= base + GATES["race_margin"])
        mark = lambda ok: "" if ok is None else (" ✓" if ok else " ✗")  # noqa: E731
        acc = s.get("citation_accuracy")
        print(f"| {c} | {race if race is not None else '–'}{mark(race_ok if race is not None else None)} "
              f"| {acc if acc is not None else '–'}{mark(acc >= GATES['citation_accuracy'] if acc is not None else None)} "
              f"| {s.get('effective_citations', '–')} | {s.get('tokens_median', 0):,} | {s.get('tokens_p90', 0):,} "
              f"| {s.get('runtime_median_min', '–')} | {s.get('errors', '–')} | {s.get('de_rubric', '–')} |")
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
