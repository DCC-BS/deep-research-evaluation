# Bebbi Bot Deep Research: final report

Kanton Basel-Stadt, Bebbi Bot (Open WebUI). Evaluation from 7 to 9 October 2026.

- Requirements and scoring rubric: [requirements.md](requirements.md). The published page with interview decisions and history is <https://claude.ai/artifact/UKkqGjLg8v4PLcKMTperAJ>.
- How to reproduce: [README.md](../README.md).

## Summary

We compared four ways to add deep research to Bebbi Bot, all on the production model (Gemma-4-31B NVFP4) and the production search stack (Serper, self-hosted Firecrawl, MCP):

1. GPT-Researcher.
2. NVIDIA Deep Researcher (AI-Q).
3. A simple tool-calling agent loop.
4. Our own `research-agent`, built during the evaluation from the strongest patterns of 13 engines.

**Recommendation:** run our own job service behind one Open WebUI pipe, with two engines selected by preset.

| Engine | Use | Why |
|---|---|---|
| Focus engine (bounded tool-calling loop, built in v4) | Administrative questions: law, Grosser Rat, statistics, administration | Best on the German set: 66.0% over 3 repeats, against 58.9% for the plain agent loop and 54.6% for NVIDIA, at about 60k tokens and 3 min per report |
| `research-agent` pipeline (v5 settings for `web_survey`) | Broad surveys across the web | The same report quality as GPT-Researcher and NVIDIA (20 tasks: RACE 46.0 vs 46.3 and 46.5; v5 on the 3 tuning tasks 46.4 vs NVIDIA 46.6), the best citations (80–86% accurate, two to three times as many supported citations), at a quarter to two thirds of the tokens |

Do not adopt GPT-Researcher or NVIDIA. Neither justifies its token cost on our hardware: 280k and 780–860k tokens per report.

Report quality (RACE) is limited by the model, not the framework. No approach beats Gemma without search by the planned +3 RACE points. The frameworks differ mainly in citation quality, cost and runtime, and that is where the decision should rest.

## Decisions

| Topic | Decision |
|---|---|
| Models | On-prem only. Production serves `RedHatAI/gemma-4-31B-it-NVFP4`, the same as the evaluation, so the results carry over directly. Research-specialised models (MiroThinker, Tongyi) are not needed now; revisit only if citation quality is not enough. |
| Scheduling | Deep research runs outside office hours (night window 20:00–05:00). Quick runs of the focus engine may start during office hours on the current GPUs, one at a time (decision 2026-10-09). |
| Human in the loop | Clarifying questions (at most 2) and plan approval or editing as chat turns. No steering mid-run. |
| Delivery | The report appears as a message in the Open WebUI chat. The job service writes it there with an Open WebUI admin service key (decision 2026-10-09); the pipe also returns it on the user's next message as a fallback. |
| Sources | Web (Serper, Firecrawl), Open WebUI knowledge bases and uploads, and MCP: opencaselaw (external, not under our control, accepted for production, possibly self-hosted later), plus three MCP servers we build and control (below). No SharePoint. |
| Network | The cluster reaches all MCP servers. |
| Access | Entra group restriction is optional. No per-user quota for now (decision 2026-10-09: hard to implement, not needed while daytime runs are limited to quick focus runs). |
| Judges (evaluation only) | The official DeepResearch Bench judges via OpenRouter (GPT-5.5 for RACE, GPT-5.4-mini for FACT), and GPT-5.4-mini for the German rubric. |
| Review of the German reports | The project lead reviews the German reports. A Claude Code subagent (Sonnet) compares them with Gemini and Perplexity Deep Research answers to the same questions ([comparison/README.md](../comparison/README.md)). |

MCP servers under our control:

| Server | Content | Expected value | In the engine (v4) |
|---|---|---|---|
| `https://mcp.data.bs.ch/mcp` | Open data portal (OGD) | Datasets, including Grosser Rat metadata | statistik, verwaltung_web |
| `https://mcp.statistik.bs.ch/mcp` | Statistics portal | Official figures and time series | Configured, switched off until the server works |
| `https://mcp-grosserrat.statistik.bs.ch/mcp` | Full texts of Grosser Rat business | Most useful: direct access to Geschäfte, Vorstösse and documents | grossrat, rechtsrecherche, statistik, verwaltung_web |

The evaluation up to v3 only used `mcp.data.bs.ch`, which moved from `/` to `/mcp` during the run. v4 adds the Grossrat server. State and suggested server changes: [mcp-servers.md](mcp-servers.md).

## What we evaluated

**Tasks**
- **DeepResearch Bench (DRB):** 20 of 50 English tasks, chosen to be close to administrative work.
- **German administrative set:** 13 tasks across Recht, Grosser Rat, web content, strategies and statistics, with rubric criteria. All approaches get the same report contract (structure, Swiss spelling, sources with URL, SG/SR numbers, Geschäftsnummern, Stand). The set is in [testsets/de-admin.json](../testsets/de-admin.json) and still needs review by domain experts.

**Judges**
- **RACE:** report quality compared with a Gemini Deep Research reference report. 50 means on par with the reference.
- **FACT:** citation accuracy and supported citations per report.
- **German rubric:** 0–3 per criterion.

**Process**
1. Calibration.
2. Stage 1: 10 tasks for all approaches.
3. Analyses by subagents.
4. Tuning on 3 tasks, confirmed on 10.
5. Final run.

The analyses are in [docs/analysis/](analysis/). The research behind our own agent is in [docs/research/](research/).

**Judge spend:** $41.61 of the $50 OpenRouter limit.

## Results

### DRB, 20 English tasks

| Approach | RACE | Citation accuracy | Supported citations / report | Tokens median / p90 | Runtime median |
|---|---|---|---|---|---|
| Gemma without search¹ | 43.9 | n/a | n/a | 2k / 3k | 0.6 min |
| Simple agent loop¹ | 43.3 | 45.4% | 9.8 | 13k / 23k | 1.4 min |
| GPT-Researcher (default) | 45.6 | 79.2% | 27.8 | 215k / 257k | 10.6 min |
| GPT-Researcher @patched | 46.3 | 75.7% | 32.0 | 282k / 361k | 13.6 min |
| NVIDIA (default) | 46.5 | 54.8% | 20.0 | 862k / 1.06M | 14.5 min |
| NVIDIA @lean | 45.2 | 62.6% | 24.3 | 775k / 939k | 13.8 min |
| **research-agent v2** | 46.0 | **82.7%** | **60.9** | **133k / 173k** | **4.5 min** |

¹ Only the 10 stage-1 tasks.

RACE differences below about 1.5 points are within noise.

### German administrative set, 13 tasks

The run used the shared report contract and a working data.bs.ch MCP, and every report was re-judged with the current date.

| Approach | Rubric | Tokens median | Report length median |
|---|---|---|---|
| **Simple agent loop** | **55.0%** | **13–28k** | 8k characters |
| NVIDIA @lean | 54.6% | 775k | 8k |
| GPT-Researcher @patched | 49.4% | 429k | 22k |
| research-agent v2 | 48.1% | 251k | 31k |
| research-agent v3 | 46.8% | 119k | 12k |
| Gemma without search | 32.0% | 2k | 7k |

With n=13 and one run each, differences of about ±4 points are noise.

`research-agent` loses mostly on one criterion, "every claim has a fitting source": it scores 0.3 of 3, against 1.0 for the agent loop. Its section-wise pipeline writes more text than its evidence carries.

### v4: focus engine with the Grossrat MCP (2026-10-09)

v4 runs the focus engine for the administrative presets and the survey pipeline for DRB (details:
[research-agent-design.md](research-agent-design.md)). German set 3 repeats, DRB tuning tasks 2 repeats, and
the plain agent loop once more with the Grossrat server (`baseline-agent@grossrat`), all judged on the same day.

| German set | Rubric (3 repeats) | Every claim sourced (c2, 0–3) | Stand/date (c4) | Tokens median | Runtime median | Length median |
|---|---|---|---|---|---|---|
| **research-agent v4 (focus)** | **66.0%** (66.2 / 69.8 / 62.0) | **1.15** | **1.90** | 59–65k | 3.1 min | 8k characters |
| Simple agent loop with Grossrat MCP | 58.9% | 1.00 | 1.23 | 39k | 2.4 min | 7k |
| Simple agent loop (final run) | 55.0% | 0.92 | 1.08 | 28k | 2.2 min | 8k |
| research-agent v2 (final run) | 48.1% | 0.31 | 1.15 | 251k | | 31k |

Per category (v4 mean of 3 / agent loop with Grossrat MCP): Recht 68.5 / 55.6, Grossrat 57.0 / 48.1,
Web-Inhalte 73.4 / 66.9, Strategien 70.4 / 67.8, Statistik 50.0 / 50.0.

- v4 (mean of 3 runs) is ahead of the agent loop on 10 of 13 tasks, level on DE-ST1, behind on DE-W2 and DE-S1
  (web-only survey tasks, 3–4 points). The run means spread by ±4 points, as expected.
- The gain is in sourcing and dates: c2 went from 0.31 (v2) to 1.15, c4 from 1.15 to 1.90. MCP sources carry
  their own URL and Stand, and the number check re-points or removes citations in code.
- **Statistik is the weak spot** (40 / 70 / 40 on DE-ST1). In the low runs every data.bs `get_records` call
  failed: the model compared the text field `jahr` with `>=`, and the deployed data.bs server returns only
  "Error executing tool", so the model cannot correct itself. `mcp-data-bs` #7 (merged) returns the
  portal's reason; deploying it is the fix. The statistics server, once it works, is the better source for this task.
- **DE-G3** varies most (52 / 78 / 30): the model did not resolve "laufende Legislatur" to dates except in
  the 78 run, and repeated a future date from the Grossrat data (26.5406, 14.10.2026) without flagging it.
  Two prompt rules (resolve relative periods with a tool; flag source dates after today) did not help in
  3 repeats on G1 and G3 (v4.1: G3 41.9 vs 53.1, G1 58.9 vs 62.2) and were removed. The model looked the
  period up, but no tool returns it reliably, so it wrote "seit 2022". The fix belongs in the source: the
  Grossrat server should name the legislature periods (e.g. in `get_corpus_stats` or as a filter), and should
  not hold business items that start after their last document.
- Cost: about twice the tokens of the agent loop (62k vs 39k median), a quarter of v2, and 3 minutes per report.

| DRB tuning tasks (51, 57, 87) | RACE | Task 51 | Citation accuracy | Supported citations / report | Tokens median |
|---|---|---|---|---|---|
| research-agent v2 | 45.9 | 41.4 | 79.8% | 68.7 | 151k |
| research-agent v3 (sentence dropping) | 42.7 | 35.7 | 77.8% | 55.0 | 119k |
| **research-agent v4** (2 repeats) | 44.3 / 44.4 | 38.9 / 40.4 | 75.6 / 80.2% | 59.0 / 56.7 | 116–125k |

Undoing the sentence dropping recovers about 1.6 RACE points (task 51 most), but v4 is still about 1.5 below
v2 on these three tasks. That is at the edge of the noise, but tasks 51 and 57 both point the same way. The rest
of the gap comes from other v3 changes to the pipeline (query rules, shorter parts) and should be checked
before the pipeline goes into the pilot. No sentence was dropped in v4 (v3: 31 on task 51); 6 citations were
re-pointed to the card that has the number.

Where the RACE points go (RACE compares with a Gemini Deep Research reference report; 50 = on par):

| Tuning tasks 51, 57, 87 | Overall | Comprehensiveness | Insight | Instruction following | Readability | Words (task 57) |
|---|---|---|---|---|---|---|
| Gemini reference | 50 | 50 | 50 | 50 | 50 | 11,000 |
| NVIDIA (default) | 46.6 | 44.5 | 45.9 | 48.2 | 49.8 | 1,600 |
| research-agent v2 | 45.9 | 44.1 | 46.8 | 46.5 | 46.7 | 4,300 |
| GPT-Researcher @patched | 45.4 | 42.3 | 46.5 | 45.8 | 48.7 | 2,500 |
| **research-agent v5** (mean of 2) | **46.4** (47.0 / 45.8) | 44.5 | 47.7 | 47.3 | 46.5 | 5,800 |
| research-agent v4 (mean of 2) | 44.4 | 41.5 | 44.8 | 45.7 | 47.1 | 3,500 |
| research-agent v3 | 42.7 | 40.0 | 42.9 | 44.8 | 44.8 | 3,500 |
| Gemma without search | 43.7 | 40.3 | 42.4 | 46.3 | 48.6 | |

- **v4 vs v2 (−1.5):** almost all of it is comprehensiveness (−2.6) and insight (−2.0). v4's parts are 250–520
  words where v2's were 600–800, because it reads fewer pages and keeps fewer cards (task 51: 31 pages / 49 cards
  vs 35 / 64), and the writer prompt says "up to N words, fewer if the evidence is thin".
- **All engines vs the reference (−4 to −6):** comprehensiveness is the lowest dimension for every engine. The
  reference reports have 8,600–11,000 words of continuous analysis; ours have 3,000–4,300. Readability is our
  weakest dimension compared with NVIDIA (46.5–47 vs 49–50): many short sections (22–27 headings) and tables
  (13–15 rows) where the reference writes prose.
- **v5 (tested, now the `web_survey` default):** parts of about 1,100 words without "fewer if thin", 6 pages per
  sub-question instead of 4, connected paragraphs with at most two `###` headings and one table per part.
  RACE 47.0 / 45.8 (mean 46.4): +2.0 over v4 and +0.5 over v2, level with NVIDIA (46.6) on these tasks.
  Comprehensiveness +3.0 and insight +2.9 over v4; readability did not move. Citations: 85.7% / 80.2% accuracy,
  84 / 97 supported citations per report (v4: 59 / 57). Cost: 145–227k tokens (median about 190k, +60% over v4)
  and 5.5 min per report. Judge cost $2.56.
- Still open: v5 has run only on the 3 tuning tasks. A check on the 10 held-out DRB tasks would cost about $3.5
  in judge fees, more than is left ($3.41). Readability is the next lever (fewer, longer sections).

The MCP front proxy returned 503 in 85 of 232 health samples during the run (all bs.ch hosts at once). No tool
call failed for that reason: the client retries every request for up to about 45 s.

Judge spend for v4: $2.42; for v5 (below): $2.56. $3.41 is left of the $50 limit.

### v5 on the full sets (2026-10-09)

v5 = v4 plus short MCP tool descriptions in the presets (focus engine) and the longer, prose-style survey parts
(pipeline). DRB all 20 tasks once; German set v0.3 (19 tasks: 13 old plus 6 Grossrat full-text tasks DE-G4 to
DE-G9) three times; the agent loop with the Grossrat MCP once on the 6 new tasks.

| DRB, 20 tasks | RACE | Citation accuracy | Supported citations / report | Tokens median | Runtime median |
|---|---|---|---|---|---|
| **research-agent v5** | 46.1 | 82.5% | **84.0** | 169k | 6.0 min |
| research-agent v2 | 46.0 | 82.7% | 60.9 | 133k | 4.5 min |
| GPT-Researcher @patched | 46.3 | 75.7% | 32.0 | 282k | 13.6 min |
| NVIDIA @lean | 45.2 | 62.6% | 24.3 | 775k | 13.8 min |
| Gemma without search | 43.9 | | | 2k | 0.6 min |

The +2 RACE of v5 on the three tuning tasks did not carry over to all 20: v5 matches v2 and the other engines.
It keeps the citation lead: 38% more supported citations than v2 at the same accuracy, for 27% more tokens.

| German set v0.3 | 13 original tasks | 6 Grossrat full-text tasks | Tokens median (new tasks) |
|---|---|---|---|
| **research-agent v5** (3 runs) | 66.6% (65.4 / 65.5 / 69.0) | 75.2% (76.1 / 71.8 / 77.8) | 63k, 3.7 min |
| research-agent v4 (3 runs) | 66.0% | | |
| Agent loop with Grossrat MCP (1 run) | 58.9% | 79.5% | 62k, 2.4 min |

- On the original 13 tasks v5 equals v4 (within noise). DE-ST1 rose from 50.0 to 62.2 (mean of 3), with the
  data.bs hint and tool descriptions in place.
- On the full-text tasks the plain agent loop with the same Grossrat tools is as good as the focus engine
  (79.5% in one run vs 72–78% over three). These questions name the Geschäfte and dates, so a direct tool loop
  finds the documents without a plan. The focus engine scores lower on "every claim sourced" there (1.56 vs 2.0
  of 3). Worth checking before the pilot: whether the plan step or the citation re-pointing costs it on
  full-text tasks.

## Findings per approach

| Approach | Strengths | Weaknesses |
|---|---|---|
| **GPT-Researcher** | Digs deep with follow-up rounds. Good citation accuracy (~76–80%). Native Serper and Firecrawl. | Search queries drift away from the task: second-level queries lose the original question. Picks primary sources poorly. Has no MCP tool filter. The writer context overflows Gemma's 128k window; this needed a code patch and a retry. 13.6 min per report. |
| **NVIDIA Deep Researcher** | The plan mirrors the task's structure (required components), so reports are well structured and follow the German contract literally. Best German result besides the agent loop. | About 0.8M tokens per report: 93% are prompt tokens, because sub-agents re-send their growing context. Stacked and paraphrased citations: 55% accuracy at default, 63% @lean. Plan approval was removed in 2.2, and there is no Serper tool (we added a Tavily shim). |
| **Simple agent loop** | Calls MCP and search directly. Concise reports. Very cheap (13–28k tokens, about 2 min). Best German result. | No plan and no explicit depth. Weak citations on broad English topics (45% accuracy, 10 supported per report). |
| **research-agent v2 (own)** | Verified quotes as evidence. Citations resolved in code, one per sentence. Presets per domain. Best citation accuracy and count. Cheap and fast. | On German administrative questions it writes too much uncited text around the evidence. v3 fixed several bugs (queries, Grossrat routing, contract leakage) but its "drop failed sentences" rule hurt DRB (−3.2 RACE on 3 tasks). |

Observed problems we fixed along the way (details in [docs/analysis/](analysis/)):
- broken quotes in search queries;
- `site:` filters too long, so a third of searches returned nothing;
- the report contract leaking into planning;
- the MCP connection given up after one transient error;
- the sentence splitter cutting at German abbreviations;
- the judge flagging 2026 sources as "future".

## Recommendations

1. **Architecture: one job service, one Open WebUI pipe, two engines.**
   - **Focus engine:** a bounded tool-calling loop with an MCP allowlist per preset. Add the code-side citation layer from `research-agent`: evidence with a verbatim quote, citations resolved in code, a source list with Stand and fetch date. Use it for the presets Recht, Grosser Rat, Statistik and Verwaltung.
   - **Survey engine:** the `research-agent` pipeline with the v5 settings for the Web preset (international and broad topics).
   - The pipe shows one model per preset ("Deep Research · Recht", …). The chat flow is clarify → plan → edit → approve. The job service already has the night queue, per-user quota and restart safety ([service/app.py](../service/app.py), [pipe/deep_research.py](../pipe/deep_research.py)).

2. **Scheduling and GPU capacity.** Keep the rule that deep research runs in the night window.
   - Offer depth levels (quick, standard, deep). Allow only **quick runs of the focus engine during office hours**, with concurrency 1 and a small per-user daily quota. A quick focus run costs about 20–30k tokens and 2–3 min, about as much as a few long chat turns.
   - Standard and deep runs, and every survey-engine run, go to the night queue. A night window of 9 hours fits roughly 100 survey reports (4.5 min each) or 200+ focus reports, sequentially, on the current GPUs.
   - Measure vLLM load during the pilot before allowing more daytime runs.

3. **MCP citations.** Every citation must point to the document the MCP server returned, never to the MCP endpoint or a tool name. MCP servers should return a stable, public URL per result (Gesetzessammlung, Fedlex, grosserrat.bs.ch document URL, dataset page). The engine keeps that URL, the title and the Stand as the evidence record. If a result has no URL, the server should provide a canonical one; the engine should not invent one.

4. **Use our own MCP servers as the lever for administrative quality.** Since we control `mcp.data.bs.ch`, `mcp.statistik.bs.ch` and `mcp-grosserrat.statistik.bs.ch`, improving them is cheaper and more effective than tuning any engine. See the optional MCP improvements in the task list.

5. **Citation discipline beats length for administrative answers.** For German presets: short parts (about 350 words), no separate synthesis part, and table cells either cited or marked "nicht belegt". Drop uncited sentences only on a reliable signal: undo the v3 number-check deletion and make the number check tolerant (decimal comma, thousands separators, years).

6. **Evaluation going forward.**
   - Keep the German set as a regression test. It needs a domain-expert review and should be extended to 25–30 tasks, including the Grossrat full-text server.
   - Run each configuration 3 times, because single runs are noisy at about ±4 rubric points.
   - The DRB subset is enough to detect regressions on broad topics.

7. **Governance (decided 2026-10-09).**
   - The job service writes the report into the chat with an Open WebUI admin service key: `POST /api/v1/chats/{id}/messages/{id}` allows only the chat owner or an admin. The pipe still returns a finished report on the user's next message, in case the write fails.
   - No per-user quota (`RA_QUOTA_PER_DAY=0`). Outside the night window the service starts only quick runs of focus-engine presets, one at a time (`RA_DAY_WORKERS=1`), and queues everything else for the night.

## Task list

### Phase 0 and 1: requirements and desk research (done)
- [x] Interview, requirements spec with metrics and weights, decisions
- [x] Desk research on about 25 projects; shortlist; benchmark protocol
- [x] German administrative test set v0.2 (13 tasks, rubric)

### Phase 2 and 3: local evaluation (done)
- [x] Local stack mirroring production: vLLM Gemma-4-31B NVFP4, metering gateway, Firecrawl, MCP
- [x] Harness, DRB judge wrapper (RACE + FACT), German rubric judge, results viewer
- [x] Calibration, stage 1, analyses, tuning (GPT-Researcher @patched, NVIDIA @lean)
- [x] Own `research-agent` designed from 13 engines' patterns, built and tuned (v1–v3)
- [x] Final run: 20 DRB tasks, German set with shared contract, re-judged

### Phase 4: engine work before the pilot
- [x] Focus engine: bounded tool-calling loop as a `research-agent` mode for the administrative presets, with evidence records, code-resolved citations and a source list with Stand ([research_agent/focus.py](../research_agent/focus.py), design: [research-agent-design.md](research-agent-design.md))
- [x] Undo v3 sentence dropping; make the number check tolerant ([research_agent/text.py](../research_agent/text.py), unit tests in `tests/`)
- [x] Re-test: German set 3 repeats, DRB tuning tasks 2 repeats (`scripts/v4eval.sh`; results in "v4" above): German set 66.0% (agent loop 58.9%), DRB 44.3 (v2 45.9, v3 42.7)
- [ ] Deploy `mcp-data-bs` main (#7: error reasons reach the model); re-test DE-ST1
- [x] DRB gap of the survey pipeline: v5 (longer parts, more pages, more prose for `web_survey`) reaches RACE 46.4 on the tuning tasks (v4 44.4, v2 45.9)
- [x] v5 on all 20 DRB tasks: RACE 46.1 (v2 46.0), supported citations 84 per report (v2 61)
- [x] **MCP citation workflow:** every MCP result item with a URL becomes its own source (Geschäft, document, law, decision, dataset); never "MCP" or the server endpoint. Title, URL and Stand per source ([research_agent/sources.py](../research_agent/sources.py))
- [x] Add `mcp-grosserrat.statistik.bs.ch/mcp` to the presets with tool allowlists; `mcp.statistik.bs.ch/mcp` configured but switched off until the server works
- [x] SG/SR normalisation: writer rule, opencaselaw labels rewritten in the engine, "SR <nr>" fixed in the report when the evidence shows a cantonal number
- [x] Extend the German test set with Grossrat full-text tasks: DE-G4 to DE-G9, set v0.3 with 19 tasks (reviewer notes: `testsets/de-admin-g-notes.md`); v5 75.2%, agent loop 79.5% on them
- [x] Check why the focus engine trails the agent loop on the full-text tasks. Found and fixed (v6): the citation repair
  moved citations to unrelated documents when only a year matched (e.g. a 2022 vote cited to a letter on e-mobility);
  now only distinctive numbers decide, code adds citations only from sources the report already cites, and every change
  is logged. Result on DE-G4..G9: v6 76.1% (2 runs), without the plan step 77.4% (2 runs), v5 75.2%, agent loop 79.4%
  (3 runs). All within noise; v6 stays, the plan step stays on.
- [ ] Remaining gap to the agent loop on full-text tasks (about 3 points): the focus engine writes more claims
  (30–80 citations per report vs 15–44). Next lever to test: a shorter report target for the grossrat preset
- [ ] Review of the German reports (project lead) and comparison with Gemini and Perplexity Deep Research (prepared: [comparison/README.md](../comparison/README.md))

### Phase 4b: optional improvements to our own MCP servers (details: [mcp-servers.md](mcp-servers.md))
- [ ] Shared front proxy: bursts of 503 on all MCP hosts at once; check the backend pool and monitor `/healthz`
- [x] data.bs.ch: API error messages to the model, dataset URL per result, short list descriptions (merged: #7; export URL encoding: #5). Deploy pending
- [ ] Statistics server: error messages to the model (merged: #3); get the server working
- [ ] Return a stable, public source URL, a title and a date or Stand with every result (Geschäft or document URL on grosserrat.bs.ch, dataset page on data.bs.ch, table page on statistik.bs.ch). Grossrat and statistics already do; data.bs.ch with #7
- [ ] Grossrat server: search by topic, Vorstoss type, date range and status; get a Geschäft with its documents, Vorgänge and Regierungsrat answers as full text; Geschäftsnummer lookup
- [ ] Statistics server: search series by topic; return values with unit, Stichtag, source table and methodological notes (breaks)
- [ ] data.bs.ch server: keep the endpoint stable (it moved from `/` to `/mcp` during the evaluation); clearer tool descriptions; compact result formats (fewer tokens per call)
- [ ] All servers: short, precise tool descriptions written for a 31B model; paginated, size-limited results; health endpoint and monitoring

### Phase 5: integration and pilot
Deliverable: the repository `bebbi-deep-research` (engine v6, job service on Postgres, Open WebUI pipe and download
action, Docker image, Helm chart, seeder assets, docs, 119 tests). Local only so far; push it to the team's Git host.
- [x] Test the pipe in a real Open WebUI (local, v0.11.4): day run, night run delivered with the admin key, fallback
  on the next message, error messages, service restart mid-job. Fixed on the way: models invisible to users
  (`access_control: null`), delivered reports hidden behind `output`, background tasks starting research turns,
  visible state marker
- [x] Native Open WebUI citations (clickable badges, source list under the message) and a Word file per report,
  attached to the message for the user; `GET /jobs/{id}/report.docx` for n8n
- [x] Own sources (requirement A4): files uploaded in the chat (text via Docling) and knowledge bases, checked against
  the user's rights at approval; preset setting `own_sources` and preset "Eigene Dokumente"; verified day and night
- [x] Upgrade checklist for Open WebUI internals the integration depends on, added to `kdkp-open-web-ui/README.md`
- [ ] Repeat the end-to-end test on the test cluster (proxy, NetworkPolicy, real Entra users)
- [x] Decide report delivery: admin service key (fallback: the report on the next message)
- [x] Helm chart for the job service (Postgres, restricted PSS, proxy settings) and seeder assets for the preset models,
  in `bebbi-deep-research/deploy/`; to be wired into the GitOps repository
- [x] Night window and daytime rule in the service: no quota, quick focus runs during office hours with concurrency 1
- [ ] Pilot with one user group on UAT; measure vLLM load and user feedback; go/no-go for production

### Later
- [ ] Self-host opencaselaw from its CC0 dataset and MIT code
- [ ] A small decision model (e.g. Liquid AI or a diffusion-based classifier) for the yes/no steps that are now regex or a Gemma call: triage of search hits, "does the quote support the sentence", "is this a primary source". Sentence splitting could move to spaCy's trained German parser
- [ ] Revisit research-specialised open models if citation quality on real use falls short
- [ ] Sandboxed analysis (charts, data processing) once Agent Sandboxes are available

## Next steps

1. Review and merge the MCP pull requests (mcp-data-bs #8, mcp-statistikportal #4) and deploy them; fix the egress of the
   statistics container, then switch `statistik` on in the presets.
2. Push `bebbi-deep-research`, build the image in CI, wire the Helm chart and seeder assets into the GitOps repository,
   and repeat the end-to-end test on the test cluster.
3. Domain review of the German test set v0.3 (19 tasks) and the comparison with Gemini and Perplexity Deep Research.
4. UAT pilot with one user group: night window, quick focus runs during the day; measure vLLM load and feedback.

## Open questions

Answered on 2026-10-09:
- Report delivery: admin service key for the Open WebUI API.
- Quota: none for now; quick focus runs during office hours are acceptable on the current GPUs.
- Review of the German reports: the project lead, plus a comparison with Gemini and Perplexity Deep Research.

Still open:
- When will the statistics MCP server work again?
- Domain review of the German test set criteria (Recht, Parlamentsdienst, Statistik, Strategie).
