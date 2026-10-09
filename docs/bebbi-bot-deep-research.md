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
| Focus engine (bounded tool-calling loop) | Administrative questions: law, Grosser Rat, statistics, administration | As good as the best engine on the German set (55.0% vs 54.6% for NVIDIA) at about 3% of its tokens |
| `research-agent` pipeline | Broad surveys across the web | The same report quality as GPT-Researcher and NVIDIA (RACE 46.0 vs 46.3 and 46.5), the best citations (83% accurate, twice as many supported citations), at half to a seventh of the tokens |

Do not adopt GPT-Researcher or NVIDIA. Neither justifies its token cost on our hardware: 280k and 780–860k tokens per report.

Report quality (RACE) is limited by the model, not the framework. No approach beats Gemma without search by the planned +3 RACE points. The frameworks differ mainly in citation quality, cost and runtime, and that is where the decision should rest.

## Decisions

| Topic | Decision |
|---|---|
| Models | On-prem only. Production serves `RedHatAI/gemma-4-31B-it-NVFP4`, the same as the evaluation, so the results carry over directly. Research-specialised models (MiroThinker, Tongyi) are not needed now; revisit only if citation quality is not enough. |
| Scheduling | All deep research runs outside office hours (night window 20:00–05:00). See the recommendation below for quick runs. |
| Human in the loop | Clarifying questions (at most 2) and plan approval or editing as chat turns. No steering mid-run. |
| Delivery | The report appears as a message in the Open WebUI chat. |
| Sources | Web (Serper, Firecrawl), Open WebUI knowledge bases and uploads, and MCP: opencaselaw (external, accepted for production, possibly self-hosted later), plus three MCP servers we build and control (below). No SharePoint. |
| Network | The cluster reaches all MCP servers. |
| Access | Entra group restriction is optional. Per-user quotas are required. |
| Judges (evaluation only) | The official DeepResearch Bench judges via OpenRouter (GPT-5.5 for RACE, GPT-5.4-mini for FACT), and GPT-5.4-mini for the German rubric. |

MCP servers under our control:

| Server | Content | Expected value |
|---|---|---|
| `https://mcp.data.bs.ch/mcp` | Open data portal (OGD) | Datasets, including Grosser Rat metadata |
| `https://mcp.statistik.bs.ch/mcp` | Statistics portal | Official figures and time series |
| `https://mcp-grosserrat.statistik.bs.ch/mcp` | Full texts of Grosser Rat business | Most useful: direct access to Geschäfte, Vorstösse and documents |

The evaluation only used `mcp.data.bs.ch`, which moved from `/` to `/mcp` during the run. The statistics and Grossrat servers were not part of the evaluation.

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
   - **Survey engine:** the `research-agent` v2 pipeline for the Web preset (international and broad topics).
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

7. **Governance.**
   - Writing the report into the chat after a night run needs an Open WebUI admin service key: `POST /api/v1/chats/{id}/messages/{id}` allows only the chat owner or an admin.
   - The alternative is that the pipe fetches the finished report on the user's next message.
   - Decide which one to use before the pilot.

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
- [ ] Focus engine: bounded tool-calling loop as a `research-agent` mode for the administrative presets, with evidence records, code-resolved citations and a source list with Stand
- [ ] Undo v3 sentence dropping; make the number check tolerant; re-test DRB tuning tasks and the German set (3 repeats)
- [ ] **MCP citation workflow:** cite the source URL the MCP result returns (document, law, Geschäft, dataset), never "MCP" or the server endpoint. Keep title, URL and Stand per result as an evidence record. Fall back to a canonical URL provided by the server.
- [ ] Add `mcp.statistik.bs.ch/mcp` and `mcp-grosserrat.statistik.bs.ch/mcp` to the presets (Statistik, Grosser Rat) with tool allowlists
- [ ] SG/SR normalisation for Basel-Stadt law: writer rule, plus a fix at the source where possible
- [ ] Extend the German test set with Grossrat full-text tasks; domain-expert review of tasks and criteria

### Phase 4b: optional improvements to our own MCP servers
- [ ] Return a stable, public source URL, a title and a date or Stand with every result (Geschäft or document URL on grosserrat.bs.ch, dataset page on data.bs.ch, table page on statistik.bs.ch)
- [ ] Grossrat server: search by topic, Vorstoss type, date range and status; get a Geschäft with its documents, Vorgänge and Regierungsrat answers as full text; Geschäftsnummer lookup
- [ ] Statistics server: search series by topic; return values with unit, Stichtag, source table and methodological notes (breaks)
- [ ] data.bs.ch server: keep the endpoint stable (it moved from `/` to `/mcp` during the evaluation); clearer tool descriptions; compact result formats (fewer tokens per call)
- [ ] All servers: short, precise tool descriptions written for a 31B model; paginated, size-limited results; health endpoint and monitoring

### Phase 5: integration and pilot
- [ ] Test the pipe in a real Open WebUI on the test cluster (state marker rendering, status events, delivery)
- [ ] Decide report delivery: admin service key vs. fetching on the next message
- [ ] Helm templates for the job service in `ki-app-openweb-ui` (Postgres instead of SQLite, restricted PSS, proxy); seeder entries for the preset models
- [ ] Night window and quota configuration (quick focus runs during office hours with concurrency 1)
- [ ] Pilot with one user group on UAT; measure vLLM load and user feedback; go/no-go for production

### Later
- [ ] Self-host opencaselaw from its CC0 dataset and MIT code
- [ ] Revisit research-specialised open models if citation quality on real use falls short
- [ ] Sandboxed analysis (charts, data processing) once Agent Sandboxes are available

## Next steps

1. Build the focus engine and fix the v3 regressions (Phase 4, first two items). Re-test with 3 repeats on the German set and the 3 DRB tuning tasks. About $3 in judge costs.
2. Add the statistics and Grossrat MCP servers, and fix the MCP citation workflow together with the server-side URL improvements.
3. Test the pipe in a real Open WebUI on the test cluster. Decide report delivery.
4. Deploy the job service via Helm and run a UAT pilot with one group in the night window, with quick focus runs allowed during the day.

## Open questions

- Report delivery after night runs: an admin service key for the Open WebUI API, or fetching the report on the next message?
- Quota per user and day, and whether quick focus runs during office hours are acceptable for GPU load. To be measured in the pilot.
- Who reviews the German test set (Recht, Parlamentsdienst, Statistik, Strategie)?
