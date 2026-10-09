"""Export our German-set reports for the comparison with Gemini and Perplexity Deep Research.

  uv run python scripts/export_comparison.py [--candidate research-agent@v4] [--ids DE-R1 DE-G1]

Writes comparison/tasks/<id>/question.md (question, report contract, criteria) and ours.md (our report).
Existing gemini.* and perplexity.* files are never touched. See comparison/README.md.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eval.common import DE_REPORT_CONTRACT, read_jsonl  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default="research-agent@v4")
    ap.add_argument("--ids", nargs="*")
    args = ap.parse_args()
    data = json.loads((ROOT / "testsets" / "de-admin.json").read_text())
    reports = {r["id"]: r["article"] for r in read_jsonl(ROOT / "results" / args.candidate / "de" / "raw.jsonl")}
    runs = {r["id"]: r for r in read_jsonl(ROOT / "results" / args.candidate / "de" / "runs.jsonl") if r.get("status") == "ok"}
    for t in data["tasks"]:
        if args.ids and t["id"] not in args.ids:
            continue
        d = ROOT / "comparison" / "tasks" / t["id"]
        d.mkdir(parents=True, exist_ok=True)
        criteria = "\n".join(f"- {c}" for c in data["rubric_common"] + t["criteria"])
        (d / "question.md").write_text(
            f"# {t['id']} ({t['category']})\n\n## Frage (so an alle Systeme gegeben)\n\n{t['question']}{DE_REPORT_CONTRACT}\n\n"
            f"## Bewertungskriterien\n\n{criteria}\n")
        if t["id"] in reports:
            run = runs.get(t["id"], {})
            meta = (f"<!-- {args.candidate}; {run.get('total_tokens', '?')} tokens; "
                    f"{round(run.get('runtime_s', 0) / 60, 1)} min -->\n\n")
            (d / "ours.md").write_text(meta + reports[t["id"]])
        missing = [n for n in ("gemini", "perplexity") if not list(d.glob(f"{n}.*"))]
        print(f"{t['id']}: ours={'yes' if t['id'] in reports else 'MISSING'}; still to add: {', '.join(missing) or '-'}")


if __name__ == "__main__":
    main()
