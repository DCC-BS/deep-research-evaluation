# GPT-Researcher on DRB RACE: why it is only +1.3 over no-search, and what to tune

## Summary

- GPT-Researcher (GPT-R) scores 45.5 RACE on 20 tasks. On the 10 tasks it shares with the other runs it scores 45.2, against 46.5 for NVIDIA and 43.9 for the no-search baseline. On tasks 57 and 53 it loses to the baseline.
- Length is not the main problem. NVIDIA writes shorter reports (median about 12k chars vs 21k) and still beats GPT-R on 8 of 10 shared tasks. The problem is that the report does not cover what the prompt names, and it is thin on numbers. GPT-R has 0.31 percent/dollar figures per 1k chars, NVIDIA 0.77, reference 0.47.
- Three causes in the code path, in order of impact:
  1. Query drift. Sub-researchers only see their own search query, and the recursion into depth 2 passes only "research goal + follow-up questions", never the original task. Searches wander into niche topics (task 53: EU taxonomy, US biobanks, New Mexico venture fund).
  2. The writer sees a tail-trimmed context. The final context is capped at the last 25,000 words (`trim_context_to_word_limit` keeps the newest items), and the learnings come first in the list, so they are dropped first. What survives is the deepest, most drifted branch. Writer prompts are 32k-60k tokens, so the cap is probably always hit.
  3. Writer prompt and settings. The deep prompt asks for "minimum {TOTAL_WORDS} words", which we set to 2500, and has no instruction to cover every named entity or sub-question. Tables are mentioned but never required: 0 of 20 GPT-R reports contain one (NVIDIA 0, reference 1 of 20, so tables are not what the judge rewards).
- No sign of thinking-mode breakage: all 660 requests returned 200, the largest completion is 9,211 tokens against the 16,000 limit, and the 4,000 cap on learnings extraction is never reached (about 2k used).
- Best first experiment (config only): raise `DEEP_RESEARCH_BREADTH` to 5, set `TOTAL_WORDS=6000`, `SMART_TOKEN_LIMIT=32000`. Best high-value patch: carry the original task into every sub-query and into the follow-up query, and put learnings at the end of the trimmed context.

## Evidence

### Scores by task (overall, shared tasks first)

| id | GPT-R | NVIDIA | no-search | chars GPT-R / NVIDIA / ref |
|---|---|---|---|---|
| 57 | 43.7 | 49.0 | 44.3 | 21k / 14k / 83k |
| 53 | 42.3 | 46.0 | 43.7 | 19k / 10k / 70k |
| 51 | 42.1 | 44.7 | 40.6 | 20k / 15k / 63k |
| 97 | 43.5 | 45.6 | 41.8 | 22k / 8k / 57k |
| 72 | 43.0 | 43.9 | 42.4 | 23k / 11k / 69k |
| 90 | 49.5 | 48.3 | 44.9 | 24k / 12k / 69k |

Per-criterion output is not kept: `judge.log` only holds the command line, and `raw_results.jsonl` has four dimension scores per task. So criterion-level statements below come from matching reports against `criteria.jsonl`, not from judge output.

Dimension means: comprehensiveness 42.0, insight 46.5, instruction following 45.1, readability 48.5. Comprehensiveness and instruction following are the weak ones. Tasks 93 (comp 40, IF 41), 53 (comp 36, IF 39) and 57 (comp 37) are the lowest.

### Task 57 (consulting firms, weight comp 0.35)
Prompt names "Big Four, Accenture, MBB, IBM, Capgemini" and five aspects. Criterion 1 of comprehensiveness (weight 0.2) is "Breadth and Representativeness of Consulting Firms Profiled". The report is organised by theme ("Strategic Segmentation", "Outcome-Based Pricing", "Failure Modes"), not by firm. Mentions: Capgemini 0, Bain 1, McKinsey 3, PwC 3, EY 3. NVIDIA has per-group sections ("The Big Four", "MBB", "Tech-Led Firms") and 5 to 12 mentions of each firm. The reference mentions each 7 to 78 times. Section 7.3 "The Inevitability of Outcome-Based Pricing" is opinion that does not answer the prompt.

### Task 53 (wealthiest governments, insight weight 0.39)
Prompt: "how the world's wealthiest governments invest." The report never names Norway, GIC, Temasek, ADIA, PIF, CIC, Kuwait, Qatar or Saudi Arabia (0 mentions each). The reference names them 4 to 38 times. Search log for `gpt-researcher:drb:53` shows the drift: queries include "EU sustainable finance taxonomy green investment classification", "US Bionet biobank initiatives funding models", "New Mexico Double Bottom Line co-investment". The report sections on biobanking, the EU taxonomy and New Mexico are those late branches. The same query "sovereign wealth fund asset allocation and diversification trends 2025 2026 report" was issued three times.

### Task 51 (Japan elderly market, instruction following 0.22)
Prompt asks for consumption across "clothing, food, housing, and transportation" and a "market size analysis". The report contains 0 mentions of "clothing" and 0 of "apparel" (food 20, transport 6). NVIDIA has "clothing" 10 times, "trillion" 5 times, "market size" 11 times (GPT-R 3). Criterion "Coverage of All Specified Consumption Potential Sectors" has weight 0.25.

### Task 93 (video editing software)
Prompt names Premiere Pro, After Effects, CapCut, DaVinci Resolve, Final Cut Pro. Report: DaVinci 0, Final Cut 0, After Effects 1, CAGR 0, "billion" 1. Criterion "Inclusion and Contextualization of All Explicitly Named Products" (weight 0.25 of IF) and "Thoroughness of Market Sizing" (0.2 of comp) are both missed. Comp 40, IF 41.

### Structure check across all tasks
Tables: GPT-R 0/20, NVIDIA 0/13, reference 1/20. Median report 2,092 words against `TOTAL_WORDS=2500`, so the model already undershoots its own floor. Runtime median 633 s, 215k tokens (gate 20 min, 200k-1M). NVIDIA: 868 s, 862k tokens.

## How the report is produced (v installed: gpt_researcher 0.16.0 package metadata)

1. `run_one.py` creates `GPTResearcher(query=<full prompt>, report_type="deep")`. The original prompt is passed unchanged as `self.query`.
2. `DeepResearchSkill.run` (`skills/deep_research.py`): `generate_research_plan` makes 3 "follow-up questions" with a search on the raw query, then builds `combined_query` = task + those Q&A with the fake answer "Automatically proceeding with research".
3. `deep_research(breadth=3, depth=2)`: the strategic LLM makes 3 SERP queries with a research goal. For each one a new `GPTResearcher(query=<serp query only>, report_type="research_report")` runs. That sub-run plans `MAX_ITERATIONS=3` sub-queries, searches 5 results each (`MAX_SEARCH_RESULTS_PER_QUERY`), scrapes with Firecrawl, and filters chunks. `CONTEXT_FILTER` is unset so it resolves to `keyword` (BM25, relative threshold 0.5, at most 25 chunks, `KEYWORD_MAX_RESULTS`). That explains why embedding tokens are 0 in `runs.jsonl`.
4. Then `process_research_results` extracts learnings (max 3, `max_tokens=4000`) and follow-up questions.
5. Recursion: `if depth > 1` runs inside the `for result in results` loop, so it runs one branch at a time, each with breadth `max(2, breadth//2)=2`. The next query is only `"Previous research goal: ... Follow-up questions: ..."`. The task text is gone, which is the drift mechanism.
6. Final context = learnings (with `[Source: url]`) first, then raw per-branch context, trimmed by `trim_context_to_word_limit` to the **last** 25,000 words (`MAX_CONTEXT_WORDS`, hard-coded). Each recursion level also trims to 25k words on return.
7. `write_report` calls `generate_deep_research_prompt` (`prompts.py`). Template: context, then `Write a comprehensive research report answering the query: "<original prompt>"`, with 8 generic bullets ("Synthesize... narrative that builds from foundational to advanced insights", "Prioritize insights that emerged from deeper levels", "minimum length of {total_words} words", "determine your own concrete opinion"). `REPORT_FORMAT` is still APA. One single LLM call, `max_tokens=SMART_TOKEN_LIMIT`, temperature 0.35.
8. Length and structure are decided only by that prompt plus model behaviour. The prompt contains no coverage checklist and no instruction to follow the structure the user asked for. "Prioritize insights from deeper levels" actively pushes the writer toward the drifted branches.

Writer call per run (usage.jsonl, last request of each run): prompt 32k-60k tokens (median 48k), completion 5.6k-9.2k (median 7.5k), latency 150-350 s (task 90: 352 s). That is roughly a quarter of the run.

## Thinking mode

- All 660 requests in these runs carry alias `gemma-think` and status 200. `gemma-fast` never appears, so `FAST_LLM` is not reached in deep mode and the role mapping buys nothing.
- Largest completion 9,211 tokens (task 82), under `SMART_TOKEN_LIMIT=16000`. Learnings calls complete in 1.9k-2.3k tokens against the 4,000 cap. No truncation signs, no retry duplicates (every run has exactly 33 calls).
- Small planning calls (about 700 prompt / 600 completion) spend most completion tokens on thinking for a 3-item JSON array. Cheap, but a place to save time with `gemma-fast`.
- Caveat: I cannot see JSON parse failures. `parse_search_queries_response` has regex fallbacks, so a failed parse would silently yield fewer queries. Not observed (each run does about 46 searches).
- If the cap is raised for longer reports, the visible output can grow to about 17k tokens (69k chars); 32k leaves room for thinking.

## Ranked tuning list

Expectations are guesses to test, not measurements. Test on the 10 shared tasks first (57, 53, 51, 93, 97, 72, 68, 82, 87, 94), 3 tasks as a smoke test.

| # | Change | Type | Expected effect | Cost and risk |
|---|---|---|---|---|
| 1 | Patch `deep_research.py`: prefix every sub-query and the follow-up `next_query` with the original task ("Overall task: <prompt>. Sub-question: ...") and tell `generate_search_queries` to cover every entity and aspect the task names. | patch | Biggest. Fixes drift and missing entities. Comprehensiveness and IF up, maybe +1.5 to +3 overall. | No extra tokens. Low citation risk. |
| 2 | Patch the context order and trim: put raw context before learnings, or raise `MAX_CONTEXT_WORDS` to about 45,000 and trim from the middle of the list, not the front. Our gateway context is 128k tokens; a 48k prompt leaves room for 45k words (about 65k tokens). | patch | Comprehensiveness and insight up. Writer sees the broad level-1 evidence. | Prompt about +40 percent, writer slower (about +60 s). Low risk. |
| 3 | Replace the deep prompt via a small patch or a `custom_prompt` passed to `write_report(custom_prompt=...)`. Content: original task verbatim, then "Cover every named entity/aspect as its own subsection", "Use a table for comparisons across entities", "State numbers with units and year", "answer each explicit instruction", drop "prioritize deeper levels". Note `custom_prompt` bypasses the template, so append the citation and references rules from `generate_deep_research_prompt` yourself. | patch (or `custom_prompt` argument in `run_one.py`) | IF and readability up. Directly targets tasks 57, 51, 93. | Keep the in-text citation sentences, or FACT accuracy falls. Low if copied. |
| 4 | `TOTAL_WORDS=6000` and `SMART_TOKEN_LIMIT=32000`. | config | Longer output, comprehensiveness up if it follows. Gemma undershot 2500 already (median 2,092 words), so expect about 3,500-4,500 words at best. | Writer +100-200 s. Risk to citation accuracy is small, but longer reports dilute citation density; watch effective citations. Do together with 3, alone it is likely weak. |
| 5 | `DEEP_RESEARCH_BREADTH=5`, `DEEP_RESEARCH_DEPTH=2` (task `depth: "deep"` currently maps to 4/3). | config (edit `DEPTHS`) | More entity coverage. Only useful with #1 and #2, else more drift. | Searches about 46 to about 80, tokens about 215k to about 350k, runtime about 633 s to about 1,000 s. Inside the gates. |
| 6 | Two-stage writing (the repo's `detailed_report` flow): outline with `construct_subtopics`, one `subtopic_report` per subtopic with its own context slice, then intro and conclusion. The orchestrator class is not in the pip package; it has to be reimplemented in `run_one.py` from `write_report_introduction`, `write_conclusion` and the subtopic prompt. | patch (larger) | Reaches the 8k-10k word range that the reference has; comprehensiveness is the dimension most tied to length. Likely the single largest lever if #1-#3 are not enough. | Tokens +100-150k, runtime +5-10 min, risk of repeated paragraphs and duplicate references. Citation accuracy should hold since each section is grounded in a smaller context. |
| 7 | `KEYWORD_MAX_RESULTS=40` and `KEYWORD_RELATIVE_THRESHOLD=0.35` (env read by `context/select.py`), or `CONTEXT_FILTER=embeddings` (we have `qwen-embed`). | config | More evidence per sub-query, more numbers. Modest. | Context grows; with the 25k-word cap this only helps together with #2. `embeddings` mode needs checking against the gateway. |
| 8 | Cut dead calls: `STRATEGIC_LLM=openai:gemma-fast` for query planning; use `REASONING_EFFORT=low`. | config | Runtime and tokens down. Quality effect neutral to slightly negative. | Only do it if #4-#6 push runtime past 20 min. |
| 9 | `REPORT_FORMAT` from `APA` to `markdown` (or a short free-text format string). | config | Marginal. APA wording pushes "author, year" style references. Possible small readability change. | Check that hyperlink citations stay in the same form (`[text](url)`), or FACT extraction may change. |
| 10 | `CURATE_SOURCES=True`. | config | Probably neutral or negative: adds an LLM call per sub-query and the curation prompt does not target the missing-entity problem. | Tokens up. Try last. |
| 11 | Dedupe repeated queries (task 53 repeats one three times): skip any SERP query already issued. | patch | Saves about 5 searches per run, frees budget for new angles. | None. |

## Suggested experiment order

1. Baseline re-run is not needed. Apply #1, #2, #3 together, run the 10 shared tasks, compare per-dimension scores to the current ones.
2. Add #4 and #5 as a second arm.
3. If comprehensiveness stays below 45, try #6.
4. Track per arm: RACE four dimensions, report chars, numbers per 1k chars, named-entity coverage for the task prompt, FACT citation accuracy and effective citations, tokens, runtime.
