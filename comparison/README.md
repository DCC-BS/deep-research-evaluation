# Comparison with Gemini and Perplexity Deep Research

Our reports on the German administrative set, side by side with Gemini Deep Research and Perplexity Deep Research
on the same questions. The comparison is done by a Claude Code subagent (Sonnet) defined in
[.claude/agents/report-comparison.md](../.claude/agents/report-comparison.md).

## Layout

```
comparison/
  tasks/<task-id>/
    question.md        exported: the question exactly as our engine got it, plus the criteria
    ours.md            exported: our report (first line: engine, tokens, runtime)
    gemini.md|.pdf     you add: the Gemini Deep Research answer
    perplexity.md|.pdf you add: the Perplexity Deep Research answer
  results/
    <task-id>.md       written by the agent: scores, citation spot checks, differences, verdict
    summary.md         written by the agent: means, patterns, improvement list for our engine
```

## Steps

1. **Export our reports** (after you have reviewed them):

   ```bash
   uv run python scripts/export_comparison.py --candidate research-agent@v4
   ```

   It prints which tasks still miss a Gemini or Perplexity answer. Re-running it overwrites only
   `question.md` and `ours.md`.

2. **Run the questions in Gemini and Perplexity.** Copy the text under "Frage" in `question.md`, including
   the paragraph "Anforderungen an den Bericht", unchanged. Use Deep Research mode in both. Save the answer
   in the task folder:
   - `gemini.md` or `perplexity.md`: copy the answer as Markdown. Keep the source list with full URLs.
   - or a PDF export: `gemini.pdf`, `perplexity.pdf`.
   - Write the date of the run in the first line, e.g. `<!-- Gemini Deep Research, 2026-10-12 -->`.

   Not every task needs both systems. The agent compares what is there.

3. **Start the comparison** in Claude Code in this repository, e.g.:

   > Use the report-comparison agent to compare DE-R1, DE-G1 and DE-ST1.

   or "for all tasks in comparison/tasks". The agent runs on Sonnet. Per task it reads the three reports,
   checks up to 12 cited URLs, and writes `comparison/results/<task-id>.md`. After the last task it writes
   `summary.md`.

## Notes

- The agent knows which report is ours. It must score every report against the criteria with a quote
  before it compares them, and it must not give ours the benefit of the doubt.
- Its scores use the same 0–3 rubric as `eval/judge_de.py`, so they are roughly comparable with the
  automatic judge, but they are a second opinion, not a replacement for your review.
- Gemini and Perplexity search the open web only; they cannot query the Grossrat, data.bs.ch or opencaselaw
  MCP servers. Differences on Grossrat and statistics tasks partly measure that access.
