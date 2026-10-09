# German administrative set: why the plain agent loop beats GPT-Researcher and NVIDIA

## Summary

- Rubric means over 13 tasks: no-search 24.7, agent 50.0, NVIDIA 46.7, GPT-Researcher (GPT-R) 38.3. One run per task, one judge pass, so differences of a few points are noise.
- The gap to NVIDIA (3.3 points) is mostly a prompt artefact. The agent and the no-search baseline are told to write "Zusammenfassung, Hauptteil und offenen Punkten" (`REPORT_RULES` in `eval/candidates/baselines.py`). The rubric asks for exactly that structure (shared criteria 1 and 6). GPT-R and NVIDIA get no such instruction. If criteria 1 and 6 are dropped, NVIDIA is at 47.8 and the agent at 45.7. The agent no longer wins.
- The gap to GPT-R is real: 38.0 vs 45.7 without criteria 1 and 6. It comes from query drift, a writer that sees a huge, noisy context, and poor source quality, not from MCP.
- MCP is not what separates the approaches. Only 7 to 12 percent of the cited URLs in the 8 MCP tasks are MCP-derived for every approach (agent 7 of 100, GPT-R 10 of 168, NVIDIA 12 of 104). On the five web-only tasks the agent leads GPT-R by 18 points (53.9 vs 36.0); on the eight MCP tasks by 8 (47.5 vs 39.8). NVIDIA is within 2 points of the agent on web-only tasks (51.6).
- The engines do not use MCP properly, though. GPT-R runs the MCP retriever with the full unfiltered tool list, on a drifted sub-query, in one shot. NVIDIA cites MCP data as a bare tool name, which the judge treats as no source. The agent itself used MCP in only 4 of the 8 eligible tasks.
- Cost: the agent needs a median 21.9k tokens and 168 s. GPT-R needs 472k and 1,303 s (21.7 min, above the 20 min gate). NVIDIA needs 733k and 802 s.

## 1. Did the approaches use the MCP sources?

Method: the agent logs its tool trail (`artifacts.jsonl`, `trail`). For GPT-R and NVIDIA the gateway does not log MCP calls, so use is inferred from report content, GPT-R source lists and log tails. "MCP-type citation" means a URL or source naming lexfind, opencaselaw, gesetzessammlung.bs.ch, fedlex, data.bs.ch, or an `mcp_*__*` tool name. gesetzessammlung.bs.ch can also come from web search, so this is an upper bound for "MCP-derived".

8 tasks list an MCP source: DE-R1, R2, R3 (opencaselaw), DE-G1, G2, G3, ST1 (data-bs), DE-S1 (web plus data-bs).

| | Direct evidence of MCP calls | Reports with MCP-type citation (of 8) | MCP-type URLs / all URLs | Grossrat URLs (G1-G3) |
|---|---|---|---|---|
| baseline-agent | 4 of 8 tasks (trail): R1 10 opencaselaw calls, R3 7, G1 4 data_bs, ST1 7. No MCP call in R2, G2, G3, S1 | 3 (R1, R3, G2) | 7 / 100 | 19 grosserrat.bs.ch |
| gpt-researcher | R1 report cites `mcp.opencaselaw.ch/entscheid/bs_appellationsgericht_AG.2018.369` and lexfind; G3 cites data.bs.ch. Source lists hold no `mcp://` entries | 4 (R1, R2, R3, G3) | 10 / 168 | 9 |
| nvidia-dra | G2 and ST1 list `mcp_data_bs__get_records` as a source; R3 and G2 cite lexfind | 4 (R1, R3, G2, ST1) | 12 / 104 | 23 |

Examples:
- Agent, DE-R1: `opencaselaw__get_legislation {"canton":"BS","systematic_number":"153.260"}`, then cites `gesetzessammlung.bs.ch/data/153.260/de`. It is the only report whose three sources are all statutes. It still writes "SR 153.260" where Basel-Stadt uses SG numbers, and the judge gives criterion 7 a 0.
- Agent, DE-ST1: pulls dataset 100125 and 100010 with `group_by jahr`, but the report cites web pages (swissinfo, HEV, an Instagram post), not the datasets.
- NVIDIA, DE-ST1: "[4] mcp_data_bs__get_records: mcp_data_bs__get_records". Real data, no URL.
- GPT-R, DE-R1 sources include `data.bs.ch/explore/dataset/100057/table/?sort=title`, which has nothing to do with video surveillance.
- Nobody cites a Bundesgericht decision with a BGE or docket number in the 8 tasks. `bger.ch` and BGE patterns: 0 hits for all three.

Geschäftsnummern (pattern `NN.NNNN.NN`, tasks G1-G3): NVIDIA 6/2/2, agent 1/0/1, GPT-R 1/0/0. NVIDIA's Grossrat coverage is the best of the three, yet its G3 score is 18.5 (see section 2).

## 2. Where GPT-R and NVIDIA lose (judge.jsonl)

Mean score per criterion (0-3; 1-6 shared, 7-10 task-specific):

| criterion | no-search | agent | GPT-R | NVIDIA |
|---|---|---|---|---|
| 1 complete and structured | 1.38 | 2.00 | 1.69 | 1.85 |
| 2 every claim sourced | 0.00 | 0.92 | 0.62 | 0.69 |
| 3 primary sources first | 0.00 | 1.38 | 0.92 | 1.62 |
| 4 date/Stand named | 0.00 | 0.69 | 1.00 | 0.62 |
| 5 Swiss spelling, style | 2.00 | 2.38 | 1.77 | 2.15 |
| 6 limits stated | 1.38 | 2.00 | 0.69 | 0.69 |
| 7-10 task-specific (mean) | 0.67 | 1.39 | 1.20 | 1.61 |

- Criterion 6 (limits) is the biggest single gap: 2.00 vs 0.69 for both engines. "Offene Punkte" is a heading in 13/13 agent reports, 0/13 GPT-R and 0/13 NVIDIA reports.
- NVIDIA is ahead of the agent on primary sources (3) and on the task-specific criteria (7-10). It loses on 2, 4 and 6.
- GPT-R loses on 1, 2, 3, 5, 6 and on task-specific criteria.
- ß: 0 in all 39 reports (mechanical check passes everywhere). Swiss spelling is not the issue; the criterion 5 deductions for GPT-R are about style (ST1: "umgangssprachliche Wertungen, spekulative Formulierungen").

Largest gaps (rubric %, agent / GPT-R / NVIDIA):

| task | agent | GPT-R | NVIDIA | what the judge says |
|---|---|---|---|---|
| DE-ST1 (statistics, data-bs) | 40.0 | 16.7 | 26.7 | GPT-R: "Mehrere Zahlen wirken erfunden, inkonsistent", no dataset reference, criteria 6, 8, 10 at 0. The GPT-R report also ends in 12,231 characters of base64 junk (a URL that the writer looped on). NVIDIA: source [4] "kein konkreter URL-Nachweis"; treats 2025 (scenario value) as an actual; no method-break note |
| DE-W3 (waste fees, web) | 63.0 | 33.3 | 48.1 | GPT-R cites App Store pages and Luzerner Zeitung for fee facts, no Italian source for Lugano (criterion 8 = 0). NVIDIA: limits 0, instagram/blog sources |
| DE-S2 (digital strategies) | 56.7 | 30.0 | 56.7 | GPT-R: criterion 2 = 0, canton choice (Bern, Luzern, Zürich) not justified, secondary sources replace official ones |
| DE-G3 (digitalisation, Grosser Rat) | 33.3 | 48.1 | 18.5 | Reverse case. NVIDIA assumes "Legislatur 2025-2029" without support and lists projects, not Ratsgeschäfte (criteria 7, 8). The agent also fails the task criteria (0, 0, 0), so GPT-R's win is a fluke of weak competition |

Other cases where the agent loses: DE-R1 (36.7 vs 50.0 NVIDIA), DE-W2 (30.0 vs 40.0 GPT-R). Head to head, the agent beats GPT-R on 10 of 13 tasks and NVIDIA on 7 of 13.

By category (agent / GPT-R / NVIDIA): Recht 48.9 / 41.1 / 51.1, Grossrat 45.6 / 46.0 / 37.3, Strategien 56.7 / 35.6 / 56.7, Statistik 40.0 / 16.7 / 26.7, Web 52.1 / 37.8 / 48.3.

Invented facts: the judge flags invented or inconsistent figures in GPT-R ST1 and NVIDIA ST1/G3. The judge sees only the report text, so this is its guess from internal consistency, not a check against sources.

## 3. Why GPT-R is slow and token-heavy

Numbers from `runs.jsonl` and `logs/usage.jsonl`:

| depth | tasks | LLM calls | searches | tokens | runtime |
|---|---|---|---|---|---|
| quick (2,1) | G3, W3 | 9-19 | 11 | 71k-160k | 258-361 s |
| standard (3,2), web | W1, S2 | 33 | 46 | 170k-244k | 523-677 s |
| standard (3,2), with MCP | R1, R3, G2, ST1 | 64-69 | 46 | 372k-602k | 857-2,602 s |
| deep (4,3) | R2, G1, S1, W2, S3 | 99-199 | 141 | 472k-1.5M | 1,531-4,701 s |

1. MCP doubles the call count at standard depth. Web-only standard tasks make 33 LLM calls (as on English DRB, about 215k tokens). Standard tasks with an MCP source make 64-69. `RETRIEVER=serper,mcp` adds an LLM-driven MCP step to each nested researcher.
2. The MCP step is wasteful by construction (`gpt_researcher/retrievers/mcp/retriever.py`, `mcp/tool_selector.py`, `mcp/research.py`):
   - `run_one.py` passes `{"name", "connection_url"}` only. The allowlist from `config/tasks.yaml` (8 of 45 tools for opencaselaw) never reaches GPT-R, so the selection prompt lists every tool the server offers.
   - Step 1: an LLM picks "exactly 3" tools from the full list (gemma-think, thinking on). Step 2: one LLM call with those tools bound, one round, no follow-up call and no loop. Results get `href=mcp://<tool>`.
   - In the opencaselaw tasks the log shows calls with a constant prompt of 7.4k tokens, 1.2k-3.9k completion tokens and 30-140 s latency each: R1 19 calls (186k tokens, 40% of summed call latency), R2 56 (526k), R3 20 (188k). Tasks without opencaselaw have none or at most 3 (W2, S2, S3). This is an inference from call size, not from a log field; the 7.4k size matches a 45-tool listing.
   - For data-bs tasks the large prompt appears once (3.9k-4.7k tokens, G1, G2, G3, S1, ST1); the extra calls are about 620 tokens each (about 30 per task), consistent with the bound-tool call per nested researcher.
   - `MCP_STRATEGY` defaults to `fast`: MCP runs once per nested researcher, with that researcher's own SERP query (not the original task). `MCP_AUTO_TOOL_SELECTION` and `MCP_USE_LLM_ARGS` exist in `config/variables` but nothing in the 0.16.0 package reads them, so they cannot turn selection off.
3. Search drift. Nested researchers only see their own query (`skills/deep_research.py` line 441 onward). The first query is the raw prompt including our appended "(Bericht auf Deutsch, Schweizer Rechtschreibung ohne ß.)" (search.jsonl, first query of every run), which is noise for Serper. ST1 queries: "Basel-Stadt Wohnbevölkerung Entwicklung nach Bezirken", "Leerwohnungsziffer Basel-Stadt im Vergleich zu anderen Schweizer Grossstädten", "Paradoxon". The question never asked for districts or a city comparison. S2 issues near-duplicate queries on "Digitale Verwaltung Schweiz 2024-2027 KPIs Messgrössen" at least three times. Only 64% of GPT-R's search hits are .ch domains, against 85% for the agent. About 20% of queries per run are exact repeats (37 unique of 46).
4. Deep tasks multiply it: `DEPTHS["deep"] = (4, 3)` gives 141 searches and 197-199 calls. R2 ran 78 minutes and 1.5M tokens for 36.7%. The agent scored 50.0 on R2 with 18k tokens.
5. Scraping and writer: the writer prompt is 32k-70k tokens, with latency 100-320 s per call (R1: 70k prompt, 211 s; 58k prompt with 6.7k completion, 322 s). Context is tail-trimmed (see `docs/analysis/gpt-researcher.md`), so the final report is built from the most drifted branch. German reports average 21k characters, against 7k (agent) and 9k (NVIDIA), and have the lowest scores. GPT-R sources include App Store pages, a Saudi university PDF (`effatuniversity.edu.sa`, R1) and a forasoft.com blog. I did not see Firecrawl error logs, so I cannot quantify scrape failures. The ST1 base64 tail is the one visible case of corrupted output.

No sign of API errors: all gateway calls returned 200.

## 4. Is the judge a factor?

Yes, in three ways, all quantified above or checked below.

1. Format match. The agent's system prompt names the three rubric sections. Criteria 1 and 6 favour it by about 4 points on average (see Summary).
2. Concise reports win. Pooled over the three search approaches, the correlation of report length with score is r = -0.37; URL count has r = 0.08 (agent), -0.18 (GPT-R), 0.23 (NVIDIA). The judge does not reward link count as such, but it penalises long reports with many generic or secondary sources: the criterion text says "Primärquellen haben Vorrang" and the prompt says an unrelated source counts for nothing.
3. It is blind to tool output. `eval/judge_de.py` shows the model only the question, the criteria and the report text. It cannot see what MCP returned. A source like `mcp_data_bs__get_records` (NVIDIA ST1) is rated "kein konkreter URL-Nachweis" and costs criterion 2 and 7. The judge runs with `reasoning_effort="low"` and no reference answers.

Spot checks of three verdicts against the reports:
- NVIDIA DE-ST1, criterion 2 = 0. Report ends with "[4] mcp_data_bs__get_records: mcp_data_bs__get_records"; the 2025 figure 210'529 is cited to the 2024 scenario page [5]. The verdict is formally right and substantively unfair: the table values are likely real data-bs output, the citation format is the failure. Plausible, but it punishes MCP use.
- GPT-R DE-W3, criterion 3 = 1 and 8 = 0. The report cites `apps.apple.com/.../draeggwaegg` five times for "Tiefbauamt Basel-Stadt, 2024" abfuhr facts, and a Luzerner Zeitung article dated "o.D." for the Lugano 310 CHF figure. The Lugano section relies on a German-language page and secondary sources. The verdict is accurate.
- Agent DE-R1, criterion 7 = 0 although the content is a real statute reading. The report writes "IDG, SR 153.260" and "IDV, SR 153.270" (SG in Basel-Stadt), and omits any date or Stand. Accurate and fair; the low 36.7 is due to missing dates (criterion 4 = 0) and SG numbers, not to the sources.
- Mildly lenient: the agent's DE-W3 (63.0, the highest of all) has fee figures for Lugano and Bern attributed to snippets (Ticino News, Berner Zeitung) and a table that says "Sehr hoch" with no data; the judge itself notes "Zahlen nicht ausreichend abgesichert" and still gives 2s on several criteria.

## 5. Ranked recommendations

Effect sizes are guesses to test on the 13 tasks, with 3 repeats per arm if budget allows (one run per cell is too noisy for 3-point differences).

### Both engines
1. Put the report contract into the task text, same for all candidates. One shared German suffix: "Gliedere in Zusammenfassung, Hauptteil, offene Punkte. Nenne bei Erlassen die SG-Nummer, bei Ratsgeschäften die Geschäftsnummer, bei Statistiken den Datensatz. Gib das Stand-Datum jeder Quelle an. Primärquellen vor Medienberichten." Then re-score. This tests whether the 3.3 and 11.7 point gaps are format. Cost: none. Without this the comparison is not fair.
2. Re-judge with two passes (temperature 0 or `reasoning_effort` medium) and report the score with and without criteria 1 and 6.

### GPT-R
3. Pass the allowlist. In `run_one.py` and `gpt_researcher.py`, add an `allow` list to each MCP config and filter `all_tools` in `MCPRetriever._get_all_tools` (patch via `build_overlay.py`). The selection prompt falls from about 7.4k to about 1.5k tokens. Expected: -20% tokens on R tasks, fewer wrong tools.
4. Skip LLM tool selection when 8 or fewer tools remain: bind them all (patch `select_relevant_tools` to return `all_tools`). Saves 19-56 thinking calls per opencaselaw task (186k-526k tokens, up to 40% of call latency). The `MCP_AUTO_TOOL_SELECTION` setting does nothing in 0.16.0.
5. Run MCP on the original task, not the SERP query. Call the MCP step once in `DeepResearchSkill.run` with the full question (and the 3 sub-questions), cache the result and inject it into the final context in the front, not the tail. With `MCP_STRATEGY=fast` as is, each nested researcher uses only its own query. Do not use `MCP_STRATEGY=deep`: it adds one MCP round per sub-query, on top of the selection calls already seen.
6. Retriever order. `serper,mcp` is fine; the problem is the cache and trimming (context is tail-trimmed to 25k words). Check where the MCP entries land in the writer context, and put them at the end or give them a reserved share.
7. Apply the drift patch from `gpt-researcher.md` (original task in every sub-query). Drop the language suffix from the search query: set `LANGUAGE=german` only and add the suffix to the writer prompt via `custom_prompt`. Deduplicate repeated queries.
8. Cap deep mode on German tasks at (3,2). R2 and S3 show no gain from (4,3) at 2-3x cost.
9. Give the writer an explicit German template (see 1), and cap the output at about 8k characters; `TOTAL_WORDS=2500` produces 21k characters of low-signal text.

### NVIDIA
10. Make MCP citations URL-shaped. The researcher prompt says "For URL-less structured tool sources, set `source_type` to `tool` and `locator` to the raw tool name". Patch `researcher.j2` (mount via `variant["prompts"]`) to require a stable locator for MCP results: the lexfind/gesetzessammlung URL for laws, `https://data.bs.ch/explore/dataset/<id>/` for datasets, the grosserrat.bs.ch document link for business numbers. Expected: removes a systematic criterion 2 and 7 loss on ST1 and G2.
11. Source router and tool descriptions. The router (`gemma_fast`, 2 calls of about 3k tokens) decides `preferred_tools` per query; the researcher prompt then allows "one primary source-tool call plus at most one fallback". Add to the router/orchestrator prompts a line per tool: `mcp_opencaselaw`: use first for any Erlass, SG-Nummer, Gerichtsentscheid of Basel-Stadt or the Bund; `mcp_data_bs`: use first for any statistic, Grossrat Geschäft or dataset. If the image supports `tool_overrides` for description text, set them there (not verified in 2.2.0; the repo has no copy of the image config schema). Otherwise mount-patch the prompt as in item 10. Raise the source budget to two MCP calls per query for these tasks.
12. `max_results: 3` for the web search tool limits the web evidence per call; try 5. NVIDIA cites 4 URLs in ST1 and 5 in R3, the lowest source counts in the set.
13. Leave the model-call budget and the router on (cost under 1% of tokens, see `nvidia-tokens.md`).

### Agent loop
14. The 16-call cap never bound (calls per task: 5-12). More steps will not help. What does help: force at least one MCP call when the task lists an MCP source (R2, G2, G3, S1 had none), and a second pass: "list SG numbers/Geschäftsnummern/datasets you used; check that each claim has a URL; add Stand dates". Expected +5 points on criteria 2-4 at about +10k tokens.
15. Add a final-answer rule that every MCP-derived claim cites the MCP result's own URL (the opencaselaw responses carry lexfind and gesetzessammlung links). ST1 shows the agent got the data from `data_bs` but cited swissinfo.

## 6. What it means for production

- For the internal-source use case (law, Grossrat, statistics) the fitting architecture is a bounded tool-calling agent: allowlisted MCP tools exposed as functions with their full descriptions, web search and fetch as fallback, a fixed report contract, a verification pass. It matches or beats the deep engines at about 5% of GPT-R's tokens and 13% of its runtime, and each MCP call is visible and loggable.
- The deep engines add breadth on open web survey tasks only (GPT-R wins DE-W2 and DE-G3 against a weak agent; NVIDIA wins DE-R1). Neither needs 500k-1M tokens for questions that one statute or one dataset answers. A hybrid is reasonable: route "internal source" questions to the agent and keep an NVIDIA-style engine for broad surveys, once its MCP citations and source routing are fixed.
- Untested: the agent has not been run on the English DRB tasks with these tools, nothing here measures correctness against ground truth (needs the Fachpersonen review mentioned in `testsets/de-admin.json`), and 13 tasks with one run each cannot separate agent and NVIDIA.

## Files and queries used

`results/<c>/de/{raw,judge,runs,artifacts}.jsonl`, `logs/usage.jsonl`, `logs/search.jsonl`, `eval/judge_de.py`, `eval/candidates/{baselines,gpt_researcher,nvidia_dra}.py`, `candidates/gpt-researcher/run_one.py`, `candidates/nvidia-dra/{config_eval.yml,prompts/orig/researcher.j2,generated/*.yml}`, GPT-R package files under `candidates/gpt-researcher/.venv/lib/python3.13/site-packages/gpt_researcher/{retrievers/mcp,mcp,skills}`. No gateway, MCP, or LLM calls were made.
