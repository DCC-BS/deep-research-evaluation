"""Rubric judge for the German administrative test set (requirement Q5).

  uv run python -m eval.judge_de --candidate gpt-researcher [--ids DE-R1 DE-G1]

Each report is scored 0-3 on the shared criteria and the task-specific criteria of
testsets/de-admin.json by GPT-5.4-mini via OpenRouter (~$0.02 per report), plus mechanical
checks (ß, number of cited URLs). Results: results/<candidate>/de/judge.jsonl and a summary line.
"""

import argparse
import json
import os
import re
import time

from openai import OpenAI

from eval.common import RESULTS, ROOT, read_jsonl

JUDGE_MODEL = os.environ.get("DE_JUDGE_MODEL", "openai/gpt-5.4-mini")

PROMPT = """Du bewertest einen Recherchebericht für die kantonale Verwaltung Basel-Stadt. Heute ist der {today};
Quellen und Daten bis zu diesem Datum sind nicht "zukünftig".

Rechercheauftrag:
{question}

Bewerte den Bericht für jedes Kriterium mit 0 (nicht erfüllt), 1 (ansatzweise), 2 (weitgehend) oder 3 (vollständig erfüllt).
Prüfe Belege kritisch: Eine Quelle zählt nur, wenn sie zur Aussage passt und plausibel abrufbar ist (konkrete URL).
Erfundene oder unbelegte Zahlen, Paragraphen oder Geschäftsnummern führen beim betroffenen Kriterium zu höchstens 1 Punkt.

Kriterien:
{criteria}

Antworte nur mit JSON: {{"scores": [{{"criterion": <Nummer>, "score": <0-3>, "reason": "<ein Satz>"}}], "summary": "<zwei Sätze>"}}

Bericht:
<<<
{report}
>>>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--ids", nargs="*")
    args = ap.parse_args()

    testset = {t["id"]: t for t in json.loads((ROOT / "testsets" / "de-admin.json").read_text())["tasks"]}
    common = json.loads((ROOT / "testsets" / "de-admin.json").read_text())["rubric_common"]
    src = RESULTS / args.candidate / "de" / "raw.jsonl"
    reports = read_jsonl(src)
    reports = [r for r in reports if not args.ids or r["id"] in args.ids]

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
    out_path = RESULTS / args.candidate / "de" / "judge.jsonl"
    rows = []
    for r in reports:
        task = testset[r["id"]]
        criteria = common + task["criteria"]
        resp = client.chat.completions.create(
            model=JUDGE_MODEL, reasoning_effort="low", response_format={"type": "json_object"},
            messages=[{"role": "user", "content": PROMPT.format(today=time.strftime("%d.%m.%Y"),
                question=task["question"], report=r["article"],
                criteria="\n".join(f"{i + 1}. {c}" for i, c in enumerate(criteria)))}])
        verdict = json.loads(resp.choices[0].message.content)
        scores = [s["score"] for s in verdict["scores"]]
        row = {"id": r["id"], "category": task["category"],
               "rubric_pct": round(100 * sum(scores) / (3 * len(criteria)), 1),
               "eszett": r["article"].count("ß"),
               "cited_urls": len(set(re.findall(r"https?://[^\s)\]>]+", r["article"]))),
               "chars": len(r["article"]), "verdict": verdict}
        rows.append(row)
        with out_path.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"{r['id']}: {row['rubric_pct']}%  ß={row['eszett']}  urls={row['cited_urls']}", flush=True)
    if rows:
        print(f"mean rubric {sum(x['rubric_pct'] for x in rows) / len(rows):.1f}% over {len(rows)} reports")


if __name__ == "__main__":
    main()
