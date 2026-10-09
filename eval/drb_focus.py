"""Shrink scraped pages to the passages relevant to the cited statements before FACT validation.

Official FACT sends the full page to the judge. To keep judge cost low without cutting off the
evidence (a plain prefix cap marked most long PDFs "unsupported"), each page longer than BUDGET is
split into chunks, chunks are ranked by embedding similarity to the page's cited statements
(local Qwen3-Embedding via the gateway), and the best chunks are kept in document order.

  python eval/drb_focus.py <scraped.jsonl> <focused.jsonl>
"""

import json
import math
import os
import sys

import httpx

METER = os.environ.get("METER_URL", "http://localhost:4000")
KEY = f"{os.environ['METER_API_KEY']}:judge-focus"
BUDGET = int(os.environ.get("FOCUS_CHARS", "16000"))
CHUNK, OVERLAP = 1500, 200


def embed(texts: list[str]) -> list[list[float]]:
    out = []
    for i in range(0, len(texts), 32):
        r = httpx.post(f"{METER}/v1/embeddings", timeout=120, headers={"Authorization": f"Bearer {KEY}"},
                       json={"model": "qwen-embed", "input": [t[:6000] for t in texts[i:i + 32]]})
        r.raise_for_status()
        out += [d["embedding"] for d in r.json()["data"]]
    return out


def cos(a, b) -> float:
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) or 1)


def focus(content: str, facts: list[str]) -> str:
    if len(content) <= BUDGET or not facts:
        return content
    chunks = [content[i:i + CHUNK] for i in range(0, len(content), CHUNK - OVERLAP)]
    vecs = embed(facts + chunks)
    fvec, cvec = vecs[:len(facts)], vecs[len(facts):]
    score = [max(cos(c, f) for f in fvec) for c in cvec]
    keep, used = [], 0
    for i in sorted(range(len(chunks)), key=lambda i: -score[i]):
        if used + len(chunks[i]) > BUDGET:
            break
        keep.append(i)
        used += len(chunks[i])
    head = content[:600]  # title/description context
    return head + "\n\n[...]\n\n" + "\n\n[...]\n\n".join(chunks[i] for i in sorted(keep))


def main(src: str, dst: str) -> None:
    with open(src) as fin, open(dst, "w") as fout:
        for line in fin:
            d = json.loads(line)
            for c in (d.get("citations_deduped") or {}).values():
                text = c.get("url_content") or ""
                if text and not text.startswith("scrape failed"):
                    c["url_content"] = focus(text, c.get("facts") or [])
            fout.write(json.dumps(d, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
