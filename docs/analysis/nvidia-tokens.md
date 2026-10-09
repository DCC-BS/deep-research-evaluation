# Where NVIDIA DRA 2.2 spends its tokens, and how to cut them

Scope: 13 completed `nvidia-dra:drb:*` runs (ids 90, 51, 53, 57, 68, 72, 82, 87, 94, 97, 59, 66, 69) from `logs/usage.jsonl`, `logs/search.jsonl`, `results/nvidia-dra/drb/runs.jsonl`. Run 71 is incomplete (no writer phase) and excluded. Compared with 20 `gpt-researcher:drb:*` runs. Agent source read under `src/deep_researcher_agent/agents/deep_researcher/`. Read-only analysis; nothing was executed against the gateway or vLLM.

## Summary

- Median run is 862k tokens (prompt + completion) over 13 runs, range 522k–1.83M, 50 calls (40–69). Prompt tokens are 93% of the total. Only run 57 (1.83M) breaks the p90 ≤ 1.5M gate. The median already sits inside the 200k–1M target.
- The cost is structural. The agent is a loop of about 50 calls, each re-sending a conversation of 15–40k tokens. GPT-Researcher needs 33 calls with a median prompt of about 700 tokens, so it re-sends almost nothing (about 170k prompt tokens per run).
- Roughly two thirds of prompt tokens are the parallel researcher workers (about 5 per run), 22% the writer, 12% the orchestrator/router/planner start.
- The main driver is web-page text. One batched search returns up to 4 queries × 3 pages × 6000 chars (about 17k tokens). It is inlined into the researcher's message list and re-sent on every later call.
- The biggest safe levers are: shrink page text in our gateway, lower `max_source_tool_batch_size`, cap queries and researcher calls (this cuts the tail), and make the writer read its notes in one turn (prompt edit).
- Prefix caching makes most prompt tokens cheap in compute (see section 4). The scarce resource is decode (completion) tokens, mostly thinking, plus the roughly 40–50% of prompt tokens that are new each call.

## 1. Where the tokens go

### Role inference (the gateway log has no role field)

Roles are inferred from call order, prompt size and parallel start times (start = `ts - latency_s`). The same signature appears in all 13 runs:

| Phase | Signature in the log | Source in code |
|---|---|---|
| Orchestrator start | calls 0–1, prompt about 8.5k, then calls 4–5 at about 9k | `prompts/orchestrator.j2` (12 KB) plus tool schemas |
| Source router | 2 `gemma-fast` calls, 3.1k and 3.4k (the only fast calls) | `source_router_llm`, `enable_source_router: true` |
| Planner | about 7 calls, 5.8k growing to 17.9k; 2 calls with 2.4k completion are the plan emission (planner also searches) | `prompts/planner.j2` |
| Researchers | 4–6 `gemma-think` calls starting within a few seconds of each other, all 4.96k prompt (system prompt plus ResearchQuery JSON); then interleaved threads growing 5k → 17–22k → 25–40k | `tools/research.py` runs one researcher per ResearchQuery, concurrently |
| Orchestrator, after batch | 2–3 calls at 20–25k, small completions: the full notes array came back as one tool result | `run_research_batch` returns all `ResearchNotes` JSON |
| Writer | every run has a fresh call with exactly 4398 prompt tokens, then one thread growing 1.8–2k per call (4.4k → 8k → 10k → 12k → 14k ...), ending at 20–34k | `prompts/writer.j2`; sequential `read_file` of plan/notes, then `write_file /shared/output.md` |

Inference caveat: call 0..n ordering is by completion time `ts`. Threads interleave during the research phase, so exact per-thread attribution is approximate. The phase boundaries (burst start, the 4398 writer start) are robust.

### Per-run numbers (13 runs, medians in brackets)

| Phase | Calls (total / per run) | Prompt tokens | Share of prompt | Completion tokens |
|---|---|---|---|---|
| Start: orchestrator, router, planner | 151 / 11.6 | 1.37M (91k per run) | 12.6% | 96k |
| Research: 4–6 researchers plus orchestrator turns | 338 / 26 | 7.20M (554k per run) | 65.8% | 494k |
| Writer | 167 / 12.8 | 2.37M (183k per run) | 21.7% | 151k |

Prompt size distribution over 656 calls: p10 5.0k, p25 6.0k, p50 14.4k, p75 23.2k, p90 31.9k, p99 63k, max 88k (run 57). Share of all prompt tokens by call size: under 6.5k = 9%, 6.5–15k = 13%, 15–30k = 48%, 30–50k = 22%, over 50k = 8%. So 78% of prompt tokens sit in calls with 15k+ context; calls under 15k are about 22%.

Example, task 90 (52 calls, 868,731 prompt / 60,316 completion):
- calls 0–12 (start): 114k
- calls 13–38 (5 researchers plus orchestrator): 557k
- calls 39–51 (writer): 197k, growing 4.4k → 27.7k

The 5 researchers each start at 4.96k and then jump to 17–22k on the second or third call: a single batched search adds 12–17k tokens (up to 4 queries × 3 pages × about 1.4k tokens per 6000-char page). Researcher calls then run at 14–40k each.

Task 57 (1.83M): the research phase is 43 calls and 1.40M. Prompts reach 70–88k, 6 queries, 80 searches. Several researchers kept issuing batched searches with no effective stop, because `max_researcher_model_calls` defaults to 100.

### Share of tokens that are re-sent context

Each call's prompt is the previous prompt of the same thread plus a delta. I matched calls to threads greedily (the previous call of the thread finished before this one started, prompt not smaller). This gives a rough estimate:
- New tokens per call are about 40–48% of prompt tokens overall. This is an upper bound, because mismatched threads count their whole prompt as new.
- Writer phase: 15% new, 85% re-sent. This phase is sequential and the matching is reliable. The writer re-sends its entire history 13 times.
- Research phase: about 55% new (search text, etc.). Cross-check for run 90: 48 searches × about 5k tokens = 240k expected new tool text against 331k estimated new tokens. Consistent.

So 50–60% of the 868k tokens in a typical run is context re-sent on later calls. It is cheap in compute because of prefix caching, but it counts in our token budget.

### Big writer call

There is no single huge writer call. The writer is an agent loop of 7–15 calls. The largest prompt in the phase is 20–34k (median about 25k). The report itself is emitted in one or two calls with completions of 3–5k tokens (run 90: 4,923 and 3,237). Last writer call in run 90: 25.7k prompt, 2.6k completion. The writer phase costs 183k prompt tokens per run mainly because of the one-note-per-call read pattern, not because of its size.

GPT-Researcher by comparison: 33 calls, 127k–238k prompt tokens in total, a few calls at 40–60k (the report writer), the rest around 700 tokens.

### JSON-retry cost

The retry wrapper (`StructuredResponseTextFallbackMiddleware`, `custom_middleware.py` lines 157–170) re-sends `request.messages` plus a human message containing the full ResearchNotes JSON schema, with tools disabled. The failed response itself is not appended.

The log has no way to identify these calls. A pattern search found 5 candidate pairs across 13 runs (consecutive calls where call 2 starts within 1.5 s of call 1 ending, and prompt delta is +0.7k to +2.3k) totalling about 86k prompt tokens, which is under 1% of all tokens. It is negligible. Note that the console log level is WARNING and the run logs contain no stored warnings, so this cannot be confirmed from the run archive. A few runs show a single tiny-completion call (10–18 tokens) near the end of a thread; those are likely the structured-output tool call and not retries.

Also, the finalization turn (`ResearcherFinalizationMiddleware`) is only reserved when the model-call budget runs out. No sign of it in these runs, because the budget is 100.

## 2. Code: mechanisms that grow context, and the limits

### What makes the context grow

1. **Per-researcher message history is kept.** `tools/research.py` invokes the researcher with `{"messages": [HumanMessage(query)]}`, and `create_agent` appends every AI and tool message. Nothing is dropped between calls inside a worker. Each worker is stateless relative to others, so researchers do not inherit each other's context (good).
2. **Tool results are inlined in full.** Our Tavily-compatible gateway returns 3 results × 6000 chars of Firecrawl page text (`gateway/app.py` line 123). Researcher tools are wrapped by `tools/source_tool_batching.py` and accept batches of up to 4 inputs; the batch comes back as one tool result of up to about 17k tokens.
3. **Tool-result pruning is effectively inert.** `ToolResultPruningMiddleware(keep_last_n=10, max_chars=2000)` (`factory.py` lines 248 and 282) only truncates tool results older than the last 10. A researcher has 2–4 tool results, the orchestrator fewer than 10, so nothing is truncated.
4. **Summarization middleware never fires.** `create_summarization_middleware(researcher_model, backend)` (`factory.py` line 396) uses deepagents defaults: trigger at 85% of `max_input_tokens` if the model profile has it, otherwise `("tokens", 170000)`. With a 128k context and an OpenAI-compatible Gemma profile, 170k is never reached. The maximum observed prompt is 88k.
5. **Notes are carried three times.** Each query's `ResearchNotes` (2–4k completion tokens, thinking included) is (a) returned to the orchestrator as part of one tool-result array (about 15–20k tokens in the orchestrator context for its 2–3 follow-up calls), (b) persisted to `/shared/research_note_*.json`, and (c) re-read by the writer via `read_file`, one note per call, so the writer thread grows about 2k per call and re-sends the lot.
6. **Todos and plan.** `plan.json` is read by every researcher (about 1–2k tokens) and by the writer. Orchestrator todo state is small (limits below).
7. **Planner searches.** The planner does its own discovery searches (two 16–18k calls per run, about 5% of tokens).
8. **Citation verification is not an LLM pass.** `verify_citations` and `sanitize_report` in `common/citation_verification.py` are string/registry operations run after the writer (`agent.py` lines 376–430). There are no extra model calls and no tokens. Disabling it saves nothing.

### Limits and defaults

Config keys under `functions.deep_research_agent` (`register.py` lines 64–125):

| Key | Default | Notes |
|---|---|---|
| `max_research_concurrency` | 6 (`agent.py` line 62) | Queries per `run_research_batch` call, also parallelism. Orchestrator prompt says: all queries in one call if they fit, otherwise fewest batches. Observed batches are 4–6 queries, so it did not bind. |
| `max_researcher_model_calls` | 100 (`agent.py` line 63) | Normal model turns per researcher, plus 1 reserved tools-disabled finalization turn. Effectively unlimited. Observed researchers use about 4–5, outliers many more. |
| `max_concurrent_source_tool_calls` | 5 | Concurrent source-tool calls across researchers. |
| `max_source_tool_batch_size` | 4 | Inputs per batched search. Matches the 12–17k jump. |
| `enable_source_router` | true | 2 `gemma-fast` calls, 6.6k tokens (under 1%). |
| `enable_citation_verification` | true | Zero token cost. |
| `resource_limits.*` | see below | Can only be lowered: every field is `le=<default>`. |

`DeepResearchResourceLimits` defaults (`resource_limits.py`): `max_input_chars` 32,768; `max_execution_seconds` 3600; `max_plan_bytes` 1 MiB; `max_source_routing_bytes` 1 MiB; `max_final_report_bytes` 2 MiB; `max_state_file_count` 64; `max_total_state_bytes` 24 MiB; `max_research_queries` 20; `max_total_query_chars` 10,000; `max_research_note_bytes` 512 KiB; `max_total_research_note_bytes` 10 MiB; `max_source_tool_calls` 100; `max_consecutive_source_tool_failures` 8; `max_todo_items` 20; `max_todo_item_chars` 2048; `max_total_todo_chars` 10,000. The ones that bite on tokens are `max_research_queries` and `max_source_tool_calls` (observed 22–80 searches per run, so the cap of 100 never binds) and `max_research_note_bytes`.

Not exposed in config (hard-coded, code change): the pruning middleware constants, summarization thresholds, prompt text (budgets such as "one primary call plus at most one fallback" in `researcher.j2` are advice the model ignores 8–9 times per query), the writer's read pattern.

Observed vs prompt advice: `researcher.j2` says "one primary source-tool call, plus at most one fallback", yet runs average 44 searches for about 5 queries, because each batched call counts as up to 4 searches (a batch is a list of search angles).

## 3. Ranked changes

Token numbers are estimates against the median 862k run unless noted. They are derived from the phase shares above, not measured; combined savings are not additive.

| # | Change | Where | Type | Est. reduction | Quality impact |
|---|---|---|---|---|---|
| 1 | Cut page text per result from 6000 to 2500–3000 chars (about 1.4k → 0.65k tokens per page) | `gateway/app.py` line 123, `_firecrawl(o["link"], 6000)` | Our gateway, no agent change | 20–30% (research phase is 66% and its new tokens are mostly page text; lower context also shrinks each re-send). Median to about 620k. | Moderate: less text per source, citations still verified against the registry. Quality of numeric details may drop. Test on 5 tasks. |
| 2 | `max_source_tool_batch_size: 2` (from 4) | `config_eval.yml`, `functions.deep_research_agent` | Config only | 10–15%. Caps one search call at 6 pages instead of 12 (about 8k vs 17k tokens), searches per run 44 → about 28. | Mild to moderate: fewer angles per researcher. |
| 3 | Cap queries: `resource_limits: {max_research_queries: 5}` | same | Config only | 8–12% typical, up to 20% on runs that plan 6+ queries. Each query costs about 110k tokens (its worker plus re-sent notes). | Moderate: loses one lane on broad tasks. Planner may need a hint, otherwise the batch tool errors and the orchestrator retries (small waste). |
| 4 | `max_researcher_model_calls: 6` (from 100) | same | Config only | Little at the median (workers use 4–5 calls), but caps the tail: run 57 (1.83M, 43 research calls, prompts to 88k) should fall under 1.2M. Helps the p90 ≤ 1.5M gate. | Low. A worker that hits the cap gets one finalization turn, or empty notes with a gap if that fails. |
| 5 | Writer reads all notes in one turn: instruct "issue all `read_file` calls in a single response" | `prompts/writer.j2` | Prompt edit, no Python | About 10–15%: writer phase 183k per run, about 14 calls → about 5, dropping to roughly 60k. | None expected. Same evidence, fewer turns. |
| 6 | Shorter notes: ask researchers for compact notes (smaller `max_research_note_bytes`, e.g. 24 KiB, plus prompt wording) | `resource_limits.max_research_note_bytes`, `researcher.j2` | Config plus prompt | 3–8%: note text is carried in the orchestrator result, files and writer. | Moderate: the report is built from these notes. Keep evidence fields. |
| 7 | Prune older tool results: `ToolResultPruningMiddleware(keep_last_n=2, max_chars=1500)` for researchers and the orchestrator | `factory.py` lines 248, 282 | Code change | 3–6%. Matters mainly on long researcher threads like run 57. Truncates the orchestrator's copy of the notes array after later turns. | Low to moderate: researcher loses old page text on follow-up reasoning. |
| 8 | Reduce planner discovery searches (budget text) | `planner.j2` ("discovery budget") | Prompt edit | 3–5% (two 16–18k calls). | Low to moderate: a poorer plan. |
| 9 | `researcher_llm: gemma_fast` (no thinking) | `config_eval.yml` | Config only | Small in tokens: completions are 7% of total, thinking is a minority of that, about 2–3% of tokens. Large in runtime and decode load: about 35% of decode. | High risk for note quality (notes need synthesis). Try only on researcher, not orchestrator or writer. |
| 10 | `enable_source_router: false` | same | Config only | Under 1% (6.6k tokens). | Low: the router is advisory, planner falls back to its own tool list. |
| 11 | `enable_citation_verification: false` | same | Config only | 0 tokens, no change. | Harmful: unverified citations. Do not. |
| 12 | Lower the summarization trigger (e.g. `("tokens", 40000)`) | `factory.py` line 396 | Code change | Negligible at median, helps outliers (75–88k). Costs an LLM call per summary. | Moderate. Prefer change 4. |

Suggested first package (config plus gateway plus one prompt line, no Python): changes 1, 2, 4, 5 and a conservative 3. Expected: median about 400–480k, p90 about 700–850k, with the number of sources per report lower by about a third, so check citation counts (gate is 20 effective citations per task) before locking it in. Start with change 1 at 3000 chars; if effective citations fall under 20, restore the page text and take changes 2 and 4 only.

## 4. Does prefix caching make this cheap?

Mostly yes, for compute. Evidence from `latency_s` (no `ttft_s` is logged for non-streaming calls):

- Calls with a tiny completion (10 tokens) and a 23–26k-token prompt finish in 0.34–0.36 s (6 sequential calls, all in the writer phase). Prefilling 24k fresh tokens on 2×4090 with a Marlin 4-bit kernel takes seconds, not 0.35 s. So the prefix was served from cache. These are the final writer verification calls in the same thread.
- The one cold-looking call in the sample, 20.3k prompt with 18 completion tokens, took 9.7 s, which implies cold prefill on the order of 2 k tokens/s (single observation, possibly under concurrent decode load). Treat 2–3k tok/s as a rough order of magnitude.
- Decode speed on sequential calls is 40–55 tok/s per stream (16 calls with more than 1.5k completion tokens; 24–57 tok/s, falling to about 31 tok/s at a 60k prompt). A least-squares fit over the 36 non-overlapping calls puts latency mainly on completion tokens (about 0.018 s per completion token, about 55 tok/s) and shows no stable cost per prompt token, which is consistent with caching (the fit is rough because the intercept is poorly determined).
- Run 90: 60k completion tokens at about 50 tok/s is about 1200 s of single-stream decode against a 1168 s wall clock; summed call latency is 2845 s, i.e. average concurrency 2.4. Wall time follows decode.

What each metric means for capacity planning:

| Metric | Run 90 (rough) | What it costs |
|---|---|---|
| Prompt tokens (our budget metric) | 869k | Nearly free where cached. Costs KV-cache memory (5 parallel threads × 20–40k tokens each) and prefix-cache eviction risk. |
| Uncached (new) prompt tokens | about 350–410k (estimate, see section 1) | Prefill compute, about 2–3k tok/s, so about 150–200 s of GPU time per run |
| Completion/decode tokens (includes thinking) | 60k | About 50 tok/s per stream, about 1200 s of stream time; the dominant wall-clock cost and what limits concurrency |

For GPU capacity planning, decode tokens per run and new prompt tokens per run are the metrics that matter, in that order, plus KV-cache footprint (peak concurrent context). The prompt token total only matters as the spec's token budget and for any pay-per-token comparison. Decode is roughly 20–50× slower per token than prefill here, so one completion token costs about as much GPU time as 20–50 new prompt tokens.

Caveats:
- Cache hits depend on vLLM block eviction under 5 parallel researchers plus other candidates' load; the sequential writer thread is almost fully warm, the research phase less certain.
- The 5 parallel researchers share only the first 4.96k tokens (system prompt) unless their ResearchQuery text matches. After that each has its own suffix, so growth beyond that prefix is not shared.
- The prefix cache cannot be confirmed without vLLM's `prefix_cache_hit_rate`. Enabling that metric in the next run would give the actual cached share; the numbers above are inferred.

Conclusion for the report: to compare against GPT-Researcher on tokens, state both numbers. NVIDIA DRA is about 5× more prompt tokens but only about 1.6–2× the decode tokens (50–60k vs 35–40k completion), so its real compute and runtime gap is much smaller than the token gap suggests. Decode tokens are the number to cut for runtime (thinking budget on researcher and writer, `max_tokens`), the page-text and batch changes are the ones that cut both the budget gate and the new prompt tokens.
