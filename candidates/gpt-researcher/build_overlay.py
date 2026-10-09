"""Build a patched copy of the installed gpt_researcher package in ./overlay (used when GPTR_OVERLAY=1).

Patches address the causes found in docs/analysis/gpt-researcher.md:
  1. anchor: depth-2 follow-up queries lost the original task ("Previous research goal + follow-up
     questions" only), so searches drifted. The original task is now part of every follow-up query.
  2. context: the writer context was trimmed to the newest 25,000 words, and learnings came first, so
     the distilled learnings were cut first. Limit raised to 35,000 words and learnings are placed last
     so the trim keeps them. (45,000 words plus a 32k output budget overflowed Gemma's 128k context:
     URL-heavy text is ~1.5 tokens per word, and vLLM rejected the writer call with HTTP 400. German needs
     even more tokens per word: GPTR_MAX_CONTEXT_WORDS is set to 20000 for German tasks.)
  3. coverage: the generic deep-research writer prompt gets a coverage checklist (every entity,
     sub-question and dimension named in the task), tables for comparisons and quantitative data.
     The citation rules of the original prompt are unchanged.
  4. mcp allowlist: GPT-Researcher has no MCP tool filter, so an LLM picked from all 45 opencaselaw tools
     on every sub-query (docs/analysis/german-set.md). Tools are filtered to GPTR_MCP_ALLOW (comma list,
     same allowlist as the other candidates) before selection.
Each patch asserts that its anchor text exists, so a package upgrade fails loudly instead of silently.
"""

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = next((HERE / ".venv" / "lib").glob("python3*/site-packages"))
SRC, DST = SITE / "gpt_researcher", HERE / "overlay" / "gpt_researcher"

PATCHES = {
    "mcp/tool_selector.py": [
        ("        if not all_tools:\n            return []\n\n        if len(all_tools) < max_tools:",
         "        allow = {t for t in os.environ.get(\"GPTR_MCP_ALLOW\", \"\").split(\",\") if t}\n"
         "        if allow:\n"
         "            all_tools = [t for t in all_tools if getattr(t, \"name\", \"\").split(\"__\")[-1] in allow]\n"
         "        if not all_tools:\n            return []\n\n        if len(all_tools) < max_tools:"),
        ("\nimport ", "\nimport os\nimport "),
    ],
    "skills/deep_research.py": [
        ("\nimport asyncio\n", "\nimport asyncio\nimport os\n"),
        ("MAX_CONTEXT_WORDS = 25000", "MAX_CONTEXT_WORDS = int(os.environ.get(\"GPTR_MAX_CONTEXT_WORDS\", \"35000\"))"),
        ('''                next_query = f"""
                Previous research goal: {result['researchGoal']}
                Follow-up questions: {' '.join(result['followUpQuestions'])}
                """''',
         '''                next_query = f"""
                Original task (stay within its scope): {self.researcher.query}
                Previous research goal: {result['researchGoal']}
                Follow-up questions: {' '.join(result['followUpQuestions'])}
                """'''),
        ('''        context_with_citations = []
        for learning in results['learnings']:''',
         '''        context_with_citations = []
        # Raw context first, learnings last: the trim keeps the newest items.
        if results.get('context'):
            context_with_citations.extend(results['context'])
        for learning in results['learnings']:'''),
        ('''        # Add all research context
        if results.get('context'):
            context_with_citations.extend(results['context'])

        # Trim final context''', '''        # Trim final context'''),
    ],
    "prompts.py": [
        ('''Write a comprehensive research report answering the query: "{question}"

The report should:''',
         '''Write a comprehensive research report answering the query: "{question}"

Coverage rules (apply before anything else):
- First identify every entity, sub-question, dimension, comparison, time range and output format the query
  names explicitly. The report must address each of them in its own section, subsection or table row;
  if the research found nothing on one, say so explicitly instead of skipping it.
- Follow any structure, perspective or deliverable the query asks for exactly.
- Use Markdown tables for comparisons across entities, options or time periods.
- Prefer concrete, sourced quantitative data (figures, dates, shares, amounts) over general statements.

The report should:'''),
    ],
}


def main() -> None:
    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("__pycache__"))
    for rel, reps in PATCHES.items():
        f = DST / rel
        text = f.read_text()
        for old, new in reps:
            if old not in text:
                sys.exit(f"patch anchor not found in {rel}: {old[:60]!r}")
            text = text.replace(old, new, 1)
        f.write_text(text)
    print(f"overlay built at {DST}")


if __name__ == "__main__":
    main()
