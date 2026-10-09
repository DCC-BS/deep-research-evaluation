"""Patch the NVIDIA Deep Researcher 2.2 prompts (extracted from the image into prompts/orig/) into prompts/cite/.

Based on docs/analysis/nvidia-quality.md: 59% of cited claims carry 2+ URLs (valid 46% vs 67% for single
citations), 37% of cited URLs support none of their claims (citations attached to the writer's own
analysis, swapped URLs), and the writer never sees page text, only paraphrased ResearchNotes evidence.

  writer.j2:     one citation per claim (no stacking), no citations on synthesis/inference/recommendations,
                 a number may only be cited to a source whose evidence states that exact number.
  researcher.j2: each finding carries one source and a short verbatim quote supporting it.

Mounted over /app/src/aiq_agent/agents/deep_researcher/prompts/ by variants with prompts: cite.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIG, OUT = HERE / "prompts" / "orig", HERE / "prompts" / "cite"

PATCHES = {
    "writer.j2": [
        ("- For claims supported by multiple sources, use adjacent citations like `[1][2]`, with each number pointing to its own source line.",
         "- Cite each claim with exactly one source: the one whose ResearchNotes evidence states that specific fact most directly. "
         "Do not stack citations like `[1][2]`; if several sources say the same thing, pick the most direct one.\n"
         "- Cite a number, date, name or quote only to a source whose ResearchNotes evidence contains that exact value. "
         "If no note states it exactly, drop the value or describe it as an approximation without a citation.\n"
         "- Do not attach citations to your own synthesis, comparisons, inferences, assessments or recommendations. "
         "Write them as analysis (e.g. \"This suggests ...\") without a citation number."),
    ],
    "researcher.j2": [
        ("- Put short exact quotes, if needed, inside `evidence`; do not create separate quote fields.",
         "- Each finding must rest on one source: give exactly one `source_ids` entry per finding and include a short "
         "verbatim quote from that source (the sentence that states the fact, with its numbers) inside `evidence`. "
         "Split findings that combine facts from different sources. Do not create separate quote fields."),
    ],
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, reps in PATCHES.items():
        text = (ORIG / name).read_text()
        for old, new in reps:
            if old not in text:
                sys.exit(f"patch anchor not found in {name}: {old[:60]!r}")
            text = text.replace(old, new, 1)
        (OUT / name).write_text(text)
    print(f"patched prompts written to {OUT}")


if __name__ == "__main__":
    main()
