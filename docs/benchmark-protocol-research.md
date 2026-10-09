# Deep Research Evaluation: Benchmarks, Published Scores, Token Budgets, and Protocol

Scope: the evidence base for the Q (result quality) and E (efficiency) criteria in `requirements.md`. Only on-prem open-weight LLMs are allowed in production (Gemma-4-31B main, Qwen3.5-4B task model). Research date: 7 Oct 2026.

Conventions: **[E]** marks my estimate (not a published number). Every other number has a source link in the row or a footnote. RACE scores from different judges (legacy Gemini-2.5-Pro and GPT-5.5 since May 2026) **cannot be compared with each other**. RACE is relative to a reference report, so 50 means parity with the reference.

---

## TL;DR

- **The only benchmark that fits our use case (long-form cited reports) and has broad published coverage is DeepResearch Bench (DRB): RACE for report quality and FACT for citation accuracy.** DRB II, LiveResearchBench, ResearchRubrics and DeepResearchGym also fit, but they have few or no open-model entries. BrowseComp, GAIA, HLE and xbench measure short-answer search, which is useful for Q3 only.
- **There is no public German deep-research benchmark** (searched; none found). DRB is EN/ZH only.
- **No published DRB result exists for Gemma-4-31B.** The nearest evidence is Qwen3-32B, Qwen3-30B-A3B, Qwen3.5-27B and gpt-oss-120b inside several frameworks (tables below). For Gemma-4-31B we only have SimpleQA (90.3 % in Local Deep Research), HLE-with-search 26.5 % and τ2 76.9 %.
- **Framework or model, which matters more?**
  - *RACE (report quality):* comparable effects. With Qwen3-32B fixed, reasonable frameworks cluster within about 3 points (41.0 to 44.7). STORM is an outlier at 32.8, and a no-search prompt gets 39.5. Swapping Qwen3-32B for a frontier model inside the same framework adds about 7 to 10 points.
  - *FACT (citation accuracy):* model and framework both matter a lot, and ~30B instruct models are the weak spot. WebWeaver on Qwen3-30B-A3B reaches 25 % citation accuracy against 93 % on Claude Sonnet 4. Evidence-bound citation designs (VeriTrace with Qwen3.5-27B: 68 %; ScaffoldAgent with Qwen3-32B: 54 %) recover much of the gap. **Q2 is the real risk with on-prem models, and framework choice is the main lever on it.**
- **Tokens per standard run vary by 100×** across published systems: about 26k (ScaffoldAgent/Qwen3-32B), about 0.58M (LangChain ODR/GPT-4.1 defaults), about 2.7M (VeriTrace/Qwen3.5-27B, 57 min). Our 200k to 1M window (E1) is plausible for ODR-, GPT-Researcher- and DeerFlow-style pipelines with capped knobs.

---

## 1. Benchmark catalogue

| Benchmark | What it measures | Tasks / languages | Judge (official) | Cost / effort to run ourselves | Fit for "cited long-form reports for public administration" |
|---|---|---|---|---|---|
| **DeepResearch Bench (DRB v1)** [1][2] | RACE: comprehensiveness, insight, instruction following, readability, scored against an expert reference report. FACT: citation accuracy and effective (supported) citations per task. | 100 PhD-level tasks, 22 domains; 50 EN + 50 ZH | Since 11 May 2026: RACE judge GPT-5.5, cleaner GPT-5.6 Luna (since 22 Sep 2026), FACT judge GPT-5.4-mini. Before that: Gemini-2.5-Pro [1] | Agent side: "~$20–100" for 100 tasks with cloud models [3]. Judge cost not published; **[E]** a few hundred USD for about 180 reports. Harness is open source. FACT must re-fetch every cited URL. | **High.** The only report benchmark with many open-framework entries and a citation metric. Gaps: no German tasks, PhD/industry topics instead of administration topics. |
| **DeepResearch Bench II** [4][5] | 9,430 binary expert-derived rubrics in 3 dimensions: info recall, analysis, presentation. No citation verification. | 132 tasks (66 EN / 66 ZH), 22 domains | Gemini-2.5-Pro in the paper [5]; the leaderboard also has a newer-judge board [6] | Judge about **$0.25 per task** (paper ablation) [5]. Cheap. | **High** as a diagnostic. Few open entries; harder than v1 (best systems satisfy under 50 % of rubrics) [4]. |
| **DeepResearchGym** [7] | KPR/KPC (key-point recall/contradiction), citation precision/recall, clarity, insight | 1,000 Researchy Questions (EN) for the main eval; free search API over ClueWeb22/FineWeb | GPT-4.1-mini [7] | Low: free search API and a cheap judge. Runs against CMU's hosted API, which is an external service. | **Medium-high.** A reproducible retrieval setup and a good citation metric. Topics are generic web questions. |
| **LiveResearchBench** (ICLR 2026) [8][9] | DeepEval, 6 dimensions: presentation, factual consistency, coverage, analysis depth, citation association, citation accuracy (web-verified) | 100 expert tasks, 7 domains (daily life, enterprise, academia); language not stated (EN) | Gemini-2.5-Pro + GPT-5 ensemble [9] | High: multi-judge and web verification | **High** in spirit (includes enterprise tasks); few open-backbone entries |
| **ResearchRubrics** (Scale AI, ICLR 2026) [10] | Weighted expert rubrics: factual grounding, reasoning, clarity | 101 prompts, 2,593 rubrics, 9 domains (EN) | LLM judge, binary grading (Macro-F1 0.72–0.76 against humans) [10] | Medium | **Medium-high.** Only closed DR systems published (Gemini DR 67.7 %, Perplexity 56.6 %) [10] |
| **ReportBench** (ByteDance) [11] | Citation precision/recall against reference surveys; statement faithfulness | 100 tasks derived from arXiv surveys (EN) | GPT-4o + Gemini-2.5-Pro/Flash web voting [11] | Medium | **Low-medium.** Academic literature-survey focus |
| **DeepConsult** [12] | Pairwise win rate against OpenAI DR reference reports (business/consulting) | 102 queries (EN) | Gemini-2.5-Pro [12] | Low-medium | **Medium.** Policy/consulting-style reports, pairwise only |
| **Mind2Web 2** (NeurIPS 2025) [13] | Long-horizon agentic search; answer correctness and source attribution via agent-as-a-judge tree rubrics | 130 tasks (EN), live web, time-varying | Task-specific judge agents [13] | High (live web, judge agents) | **Medium.** Attribution matters, but these are not reports |
| **DR³-Eval** (2026) [14] | Multimodal, multi-file report generation inside a static per-task sandbox corpus; recall, factual accuracy, citation coverage, instruction following, depth | Not stated in abstract | Human-validated LLM metrics [14] | Unknown | **Medium.** Static corpus means reproducible and on-prem-capable. Immature. |
| **BrowseComp** [15] | Hard-to-find short-answer facts on the open web | 1,266 questions (EN) | Simple LLM grader | Medium (long agent runs) | **Low** for reports; Q3 only |
| **BrowseComp-Plus** [16] | BrowseComp over a **fixed corpus** of 100,195 docs; separates retriever from agent | 830 queries (EN) | GPT-4.1 [16] | Low-medium; **can run fully on-prem** (local corpus + Qwen3-Embedding retriever) | **Low-medium** (Q3). Best reproducible search-agent test |
| **BrowseComp-ZH** [17] | Chinese BrowseComp | 289 questions (ZH) | LLM grader | Medium | **Low** (Chinese) |
| **GAIA** | General assistant tasks, exact-match answers | 466 (165 val / 300 test) | Exact match | Medium | **Low** |
| **HLE** (with tools) | Expert-level QA | about 2,500 | Exact match / LLM grader | Medium | **Low** |
| **xbench-DeepSearch** | Deep search, short answers | 100 (ZH) per run as used in [18] | LLM grader | Low | **Low** (Chinese, short answer) |
| **SimpleQA** | Short factual QA | 4,326 (LDR uses 300 to 500 subsets) [18] | LLM grader | Low | **Low.** Saturated (~90–95 %) and contamination risk [18] |
| German / Swiss admin DR benchmark | none found | n/a | n/a | n/a | **Gap.** Needs our own tasks (see §4) |

Cross-cutting caveat: **search-time contamination**. Agents can find benchmark questions or answers online, which inflates scores by "up to 4 %" across six public benchmarks [19]. Block benchmark host domains in search during our runs.

---

## 2. Published scores (framework / backbone / benchmark)

### 2a. DeepResearch Bench v1, legacy judge (Gemini-2.5-Pro). Source: leaderboard CSV [20] unless noted

| System | Backbone | RACE overall | Comp / Insight / Instr / Read | FACT cit. acc. | Eff. cit. / task | Note |
|---|---|---|---|---|---|---|
| Gemini-2.5-Pro Deep Research | Gemini 2.5 Pro (closed) | 49.71 | 49.51 / 49.45 / 50.12 / 50.00 | 78.30 % | 165.34 | commercial reference |
| LangChain open_deep_research | GPT-5 | 49.33 | 49.80 / 47.34 / 51.05 / 48.99 | 34.74 % | 22.44 | README says 0.4943 [3] |
| OpenAI Deep Research | o3-deep-research (closed) | 46.45 | 46.46 / 43.73 / 49.39 / 47.22 | 75.01 % | 39.79 | commercial reference |
| DR Tulu-8B | DR-Tulu-8B (Qwen3-8B-based, open) | 45.49 | 44.08 / 44.65 / 49.56 / 42.30 | – | – | paper reports 45.4 [21] |
| Claude Research | Claude (closed) | 45.00 | | – | – | |
| Kimi-Researcher | Kimi (Moonshot) | 44.64 | | – | – | |
| Doubao DR | (closed) | 44.34 | | 52.86 % | 52.62 | |
| LangChain open_deep_research (DRB submission) | default config uses GPT-4.1 [3]; the exact submission mix is not stated | 43.44 | 42.97 / 39.17 / 48.09 / 45.22 | 49.10 % | 29.49 | README: GPT-4.1 defaults = 43.09, Claude Sonnet 4 = 44.01 [3] |
| NVIDIA AIQ research assistant | Nemotron (per name; not verified) | 40.52 | | – | – | |
| **Tongyi DeepResearch 30B-A3B** | own 30B-A3B (Qwen3-30B-A3B base, open, Apache-2.0) | **40.46** | 39.46 / 34.44 / 46.22 / 44.27 | – | – | open 30B-class reference |
| Perplexity Research | (closed) | 40.46 | 39.10 / 35.65 / 46.11 / 43.08 | 82.63 % | 31.20 | |
| gpt-4o-search-preview | GPT-4o | 30.74 | | 86.63 % | 5.05 | |
| Top of board (Oct 2026) | mostly closed / unknown (e.g. qianfan 58.03, ZTE Nebula 57.27) | 55–58 | | – | – | |
| Mixed: NVIDIA AIQ | Nemotron + GPT-5.2 | 55.95 | | – | – | |
| Mixed: ms_deepresearch | GPT-5.2 mixed with Qwen3.5 | 55.31 | | – | – | |

Self-reported on the legacy judge (papers, not the leaderboard):

| System | Backbone | RACE | Cit. acc. | Eff. cit. | Source |
|---|---|---|---|---|---|
| WebWeaver | Claude Sonnet 4 | 50.58 | 93.37 % | 200.75 | [22] |
| WebWeaver | Qwen3-235B-A22B-Instruct-2507 | 50.62 | 78.25 % | 166.73 | [22] |
| **WebWeaver** | **gpt-oss-120b** | **48.11** | **66.14 %** | **64.88** | [22] |
| **WebWeaver** | **Qwen3-30B-A3B-Instruct-2507** | **46.77** | **25.00 %** | **26.74** | [22] |
| WebWeaver, fine-tuned 30B (WebWeaver-3k SFT) | Qwen3-30B-A3B SFT | – | 85.90 % | – | [22] |
| **VeriTrace (Config-27B)** | **Qwen3.5-27B** (planner/writer) + Qwen3.5-35B-A3B (reader) | **52.60 ±0.31** (3 runs) | **68.46 %** | **134.20** | [23] |
| VeriTrace (Config-3B) | Qwen3.5-35B-A3B for all roles | 51.96 | – | – | [23] |
| VeriTrace (Config-DeepSeek) | DeepSeek-V4-Pro/Flash | 55.77 | 73.28 % | 235.66 | [23] |
| FS-Researcher | Claude Sonnet 4.5 | 53.94 | 76.17 % | 139.91 | [23] |
| Controlled, **shared Qwen3.5-27B**: WebWeaver / Enterprise-DR / FS-Researcher / VeriTrace | Qwen3.5-27B | 50.77 / 49.16 / 48.03 / 52.60 | – | – | [23] Table 3 |
| DR Tulu-8B / Tongyi DR-30B / WebExplorer-8B / WebThinker-32B-DPO | open | 45.4 / 40.6 / 36.7 / 23.3 | – | – | [21] |
| OpenAI DR / GPT-5+Search / Gemini 3 Pro+Search / Perplexity DR | closed | 46.9 / 50.7 / 46.3 / 42.3 | – | – | [21] |

Data-quality note: VeriTrace's Table 2 [23] lists "LangChain-ODR(GPT-5)" as 50.60 with FACT 34.74/22.44. On the leaderboard CSV [20], 50.60 belongs to `gensee-search-gpt-5`, and ODR-GPT-5 has 49.33. Use the CSV.

### 2b. DeepResearch Bench v1, current GPT-5.5 judge

| System | Backbone | RACE | Cit. acc. | Eff. cit. | Source |
|---|---|---|---|---|---|
| Gemini-2.5-Pro DR | closed | 49.98 | – | – | [24] |
| OpenAI DR | closed | 47.84 | – | – | [24] |
| Perplexity Research | closed | 43.05 | – | – | [24] |
| Grok Deeper Search | closed | 41.22 | – | – | [24] |
| Best entries (ATH-Voicepica, cellcog-max) | unknown / closed | 55.99 / 55.78 | – | – | [24] |
| **Same backbone Qwen3-32B**, frameworks: Prompt-only (no search) / RAG / ReAct / IRCoT / STORM / WebWeaver / EDR / StackPlanner / ScaffoldAgent | **Qwen3-32B** | **39.54 / 36.68 / 42.21 / 42.46 / 32.81 / 41.28 / 40.99 / 41.55 / 44.70** | – / 10.86 / 23.78 / 40.04 / 36.90 / 32.72 / 23.70 / 26.50 / 54.32 % | – / 2.93 / 4.69 / 15.77 / 15.18 / 8.42 / 18.78 / 9.63 / 30.42 | [25] Table 1 |
| Same frameworks on DeepSeek-V3.2: ReAct / STORM / WebWeaver / StackPlanner / ScaffoldAgent | DeepSeek-V3.2 | 43.26 / 39.07 / 44.91 / 46.75 / 48.27 | 17.83 / 38.59 / 88.35 / 50.40 / 62.20 % | | [25] Table 1 |
| Backbone sweep, StackPlanner: Qwen3-32B → GPT-5.4-mini → DeepSeek-V4-Pro → GPT-5.4 (20-query pilot) | various | 41.55 → 50.66 → 49.83 → 52.18 | 26.50 → 64.58 → 59.82 → 76.90 % | | [25] Table 10 |
| Backbone sweep, ScaffoldAgent: Qwen3-32B → GPT-5.4-mini → DeepSeek-V4-Pro → GPT-5.4 (pilot) | various | 44.70 → 51.35 → 51.61 → 53.82 | 54.32 → 72.43 → 69.21 → 82.35 % | | [25] Table 10 |
| Search backend sweep, ScaffoldAgent / Qwen3-32B: original API → Bing → Wikipedia | Qwen3-32B | 44.70 / 46.12 / 42.61 | 54.32 / 63.37 / 58.21 % | | [25] Table 10 |

### 2c. DRB II (rubric pass rate, %). Source: leaderboard CSVs [6]

| System | Backbone | Total | Info recall / Analysis / Presentation |
|---|---|---|---|
| AI21-DeepResearch (best) | closed | 64.38 | 60.35 / 71.00 / 92.89 |
| NVIDIA AIQ (open source) | Nemotron 3 + Claude Opus 4.6 | 54.50 | 49.23 / 61.55 / 93.15 |
| Hermes Agent (open source) | not stated | 51.88 | |
| OpenAI o3 DR | closed | 45.40 | |
| Gemini-2.5-Pro DR | closed | 41.98 | |
| Perplexity Research | closed | 38.58 | |
| **Tongyi DeepResearch** (open, 30B-A3B) | own | **29.89** | 22.95 / 35.89 / 86.13 |

Board judged by Gemini-2.5-Pro (`leaderboard_gemini25.csv`). The newer board (`leaderboard.csv`) has only closed systems (o3 DR 43.00).

### 2d. Other report benchmarks

| Benchmark | System | Backbone | Score | Source |
|---|---|---|---|---|
| DeepResearchGym (commercial search API) | GPT-Researcher | not disclosed in paper | KPR 60.61, cit. precision 89.11, recall 94.29, clarity 86.37, insight 81.52 | [7] |
| DeepResearchGym | OpenDeepSearch | not disclosed | KPR 32.92, prec 85.86, rec 97.78 | [7] |
| DeepResearchGym | HF smolagents DeepSearch | not disclosed | KPR 33.00, prec 0.35, rec 0.29 (near-zero citations by design) | [7] |
| DeepResearchGym | Perplexity sonar-deep-research | closed | KPR 72.50, prec 55.65, rec 99.22 | [7] |
| DeepResearchGym | ScaffoldAgent / WebWeaver / STORM / ReAct, avg. of 6 dims | Qwen3-32B | 75.83 / 69.72 / 57.50 / 67.73 | [25] Table 2 |
| LiveResearchBench | Open Deep Research (LangChain) | GPT-5 | presentation 81.0, consistency 71.3, coverage 65.3, citation association 76.9 (best multi-agent) | [9] |
| LiveResearchBench | DeerFlow+ | GPT-5 | evaluated; per-dimension numbers not extracted | [9] |
| DeepConsult (win % vs OpenAI DR) | VeriTrace / WebWeaver / FS-Researcher / Enterprise-DR | Qwen3.5-27B | 81.1 / 75.2 / 72.8 / 64.7 | [23] |
| SQAv2 / HealthBench / ResearchQA | DR Tulu-8B | open 8B | 88.3 / 52.8 / 75.7 | [21] |
| ResearchRubrics | Gemini DR / Perplexity DR | closed | 67.7 % / 56.6 % compliance | [10] |

### 2e. Agentic-search benchmarks (Q3): open models and frameworks

| System / framework | Backbone | BrowseComp | BC-ZH | GAIA | HLE | xbench-DS | Other | Source |
|---|---|---|---|---|---|---|---|---|
| Tongyi DeepResearch (ReAct) | 30B-A3B (open) | 43.4 | 46.7 | 70.9 | 32.9 | 75.0 | FRAMES 90.6, WebWalkerQA 72.2 | [26] |
| Tongyi DeepResearch (Heavy) | 30B-A3B | 58.3 | 58.1 | – | 38.3 | – | | [26] |
| MiroThinker-1.7-mini | 30B (open, Apache-2.0) | 72.3 | 72.3 | – | – | – | 256k ctx, ≤300 tool calls | [27] |
| MiroThinker-v1.5 | 30B | 69.8 | 71.5 | 80.8 (val-165) | 39.2 (text) | – | | [27] |
| Qwen3.5-27B (own search agent, context folding) | Qwen3.5-27B | 61.0 | 62.1 | – | 48.5 (w/ tool) | – | WideSearch 61.1, τ2 79.0, BFCL-V4 68.5 | [28] |
| Qwen3.5-4B (our task model) | Qwen3.5-4B | n/p | n/p | – | – | – | τ2 79.9, BFCL-V4 50.3 | [29] |
| **Gemma-4-31B-it** (our main model) | Gemma-4-31B | **n/p** | – | – | **26.5 (w/ search)**, 19.5 (no tools) | – | τ2 76.9, MMMLU 88.4, 256k ctx | [30] |
| Local Deep Research (langgraph-agent, Serper) | **Gemma4:31b** | – | – | – | – | – | **SimpleQA 90.3 % (n=300), 6m25s/question** | [31] |
| Local Deep Research | Qwen3.6-27B | – | – | – | – | 77 % (n=100) | SimpleQA 95.7 % (n=300) | [18][31] |
| Local Deep Research | Qwen3.5-9B / gpt-oss-20B | – | – | – | – | 59 % / – | SimpleQA 91.2 % / 85.4 % | [18] |
| BrowseComp-Plus (fixed corpus) | gpt-oss-120B-high + Qwen3-Embedding-8B retriever | 42.89 (BC-Plus) | | | | | recall 52.6 %, 18.4 searches | [16] |
| BrowseComp-Plus | Qwen3-32B + BM25 | 3.49 (BC-Plus) | | | | | 0.92 searches (barely uses the tool) | [16] |
| BrowseComp-Plus | GPT-5 + Qwen3-Embedding-8B | 70.12 (BC-Plus) | | | | | | [16] |
| HF smolagents Open Deep Research (CodeAgent) | not stated in blog | – | – | 55.15 (val) | – | – | JSON-action agent: 33 % | [32] |
| OpenAI Deep Research | closed | 51.5 | – | ~67 (val) | 26.6 | – | | [15][32][26] |

n/p = not published.

### 2f. What this means for Q4 (how much do we lose on-prem?)

- **Report quality (RACE):** current open ~27–32B models inside a good framework reach the level of legacy commercial DR products or exceed it. Examples: VeriTrace + Qwen3.5-27B 52.6 against Gemini DR 49.7 and OpenAI DR 46.5 (legacy judge) [23][20]; WebWeaver + Qwen3-30B-A3B 46.8 [22]. Under the GPT-5.5 judge, the older Qwen3-32B in good frameworks gets 41–45 against 47.8 for OpenAI DR [25][24]. Moving to a frontier backbone in the same framework adds about 7–10 RACE points [25]. **[E]** Gemma-4-31B is a 2026 model with τ2 76.9; expect it to land between the Qwen3-32B and Qwen3.5-27B numbers. Unverified, which is why our own reproduction is required.
- **Citation faithfulness (FACT):** this is where on-prem models lose most. Qwen3-30B-A3B in WebWeaver gets 25 % against 93 % with Claude [22]. Qwen3-32B baselines get 11–40 % [25]. Architecture that binds claims to stored verbatim evidence lifts this to 54–68 % on ~30B models [23][25]. Fine-tuning lifted WebWeaver-30B to 85.9 % [22].
- **Framework vs. model:**
  - With the model fixed, framework spread on RACE is about 3 points among competent designs (ReAct 42.2 to ScaffoldAgent 44.7 on Qwen3-32B). Weak designs fall to 32.8 (STORM), and some do not beat a no-search prompt (39.5) [25].
  - With the framework fixed, model spread is about 4–10 points [22][25][3].
  - Citation accuracy swings by 30–60 points with either choice.
  - Search backend: ±2 RACE and up to 9 points of citation accuracy [25].
  - Token budget is the strongest single factor in Anthropic's BrowseComp analysis: 80 % of variance, with tool-call count and model choice as the other two factors explaining 95 % in total [33].
  - **Conclusion: with on-prem models fixed, framework choice is the main lever we control, and it matters most for Q2.**

---

## 3. Tokens, calls and runtime

| Framework / system | Backbone | Tokens per task (published) | LLM calls / searches | Runtime | Source | "Standard depth" estimate on Gemma-4-31B |
|---|---|---|---|---|---|---|
| LangChain open_deep_research, defaults | GPT-4.1 (+4.1-mini summaries) | 58.0M / 100 tasks = **~580k** | defaults: 5 parallel research units, 6 supervisor iterations, 10 tool calls per researcher, 50k chars per page | n/p | [3][34] | **[E] 0.4–1.2M** (input-dominated; scales about linearly with units × iterations × tool calls) |
| open_deep_research | Claude Sonnet 4 | 138.9M / 100 = **~1.39M** ($1.87/task) | | | [3] | |
| open_deep_research | GPT-5 | 204.6M / 100 = **~2.05M** | | | [3] | reasoning output inflates tokens. **[E]** Gemma thinking mode on means toward the upper bound |
| GPT-Researcher, standard report | gpt-4o-mini + gpt-4o | n/p; **~$0.005/task** | 20+ sources | **~2 min** | [35] | **[E] 30–150k** (embedding-based context compression keeps LLM input small) |
| GPT-Researcher, deep research (breadth 4, depth 2, concurrency 4) | o3-mini (high) | n/p; **~$0.40/task** | **[E]** about 12 sub-researches (breadth halves at each level; verify) | **~5 min** | [36] | **[E] 250–800k** |
| DeerFlow (ByteDance) | any | **n/p** (no published token or runtime data found) | plan → research steps → report | n/p | – | **[E] 150–600k**; measure ourselves |
| STORM | any | n/p | | | – | **[E] 100–400k**; under-performs on DRB anyway (32.8) [25] |
| Local Deep Research (langgraph-agent) | Gemma4:31b | n/p ("tokens" column shows 36,352, probably the context window setting) | | **6m25s per SimpleQA question** | [31] | short-answer only. **[E]** detailed-report mode 0.2–1M |
| VeriTrace Config-27B | Qwen3.5-27B + 35B-A3B | **2.70M** (1.59M in / 1.11M out) | **212 LLM calls, 47 searches** | **57 min** | [23] Table 15 | upper bound for a deep, verify-heavy design |
| VeriTrace Config-3B | Qwen3.5-35B-A3B | 3.65M | 260 calls, 57 searches | 46 min | [23] | |
| ScaffoldAgent / WebWeaver (reimpl.) / EDR | Qwen3-32B | 26.3k / 37.2k / 29.8k (as reported) | 8.2 / 15.9 / 9.1 searches | 117 / 149 / 136 s | [25] Table 9 | suspiciously low. Probably excludes page summarisation; treat as a lower bound |
| WebWeaver (original) | Claude Sonnet 4 | 67k evidence tokens + 26k output (totals n/p) | 15.7 search steps, 112 pages saved, 24.8 writing steps | n/p | [22] | **[E] 0.5–2M** including the reading phase |
| Tongyi DeepResearch (ReAct) | 30B-A3B | n/p | up to 128 tool calls in 128k context | n/p | [26] | **[E] 1–5M** cumulative prompt tokens (re-sent context; prefix caching cuts compute but not counted tokens) |
| DR Tulu-8B | 8B | n/p; $0.0018/query incl. inference | | | [21] | |
| OpenAI Deep Research | closed | n/p; **$1.80/query** | | | [21] | |
| Gemini Deep Research (API) | Gemini 3.x | one user-reported run: **23M tokens (22M input)**; Google: "on the high end, … not outside of the expected bounds" | | | [37] | shows commercial DR can use 10M+ tokens per task |
| Anthropic multi-agent Research | Claude Opus 4 + Sonnet 4 | agents ≈ **4×** chat tokens; multi-agent ≈ **15×** chat tokens | simple: 1 agent, 3–10 tool calls; comparison: 2–4 subagents × 10–15 calls; complex: >10 subagents | parallel tool calls cut time by up to 90 % | [33] | rule-of-thumb scaling for depth presets |

**How the knobs scale tokens.**

- ODR: tokens ≈ `max_concurrent_research_units × max_researcher_iterations × max_react_tool_calls × (page-summary tokens + researcher context)`, plus compression and the final report [34]. **[E]** Approximately linear.
- GPT-Researcher deep: about breadth × (1 + depth-related fan-out) sub-researches, each a full mini-run [36]. **[E]** Approximately linear in sub-research count.
- ReAct agents (Tongyi, MiroThinker): **[E]** cumulative prompt tokens grow about quadratically in turn count until context folding or pruning kicks in [28].

**On-prem implication.** Inputs dominate (VeriTrace: 75 % input on DeepSeek [23]). With vLLM prefix caching, real GPU cost is much lower than raw token counts. Report both counted tokens and cached-prefix tokens.

---

## 4. Recommended benchmark protocol

### 4.1 Benchmarks and subset

1. **Primary (Q1, Q2, Q4): DeepResearch Bench v1, 30 EN tasks.**
   - Take all EN tasks from domains closest to public administration (e.g. finance/economics, health, education, law/policy, transport, energy/environment, social science), then fill to 30 with a stratified random draw. **[E]** This captures about 60 % of the EN set.
   - Freeze the task IDs in Git.
   - Why DRB: it has the largest set of published open-framework and closed reference points. The harness is open, and FACT directly measures Q2.
2. **Anchor re-scoring (cheap, high value).** The HF leaderboard Space publishes raw reports for OpenAI DR, Gemini DR, Perplexity, Tongyi-30B and LangChain ODR (`data/raw_data/*.jsonl`) [38]. Re-judge their reports for our 30 tasks with *our* judge. That gives apples-to-apples anchors even if our judge differs from the official one.
3. **Secondary (Q1 robustness): DRB II, same 30-task idea on its EN half (66 tasks).** Binary rubrics with no reference-report bias. Judge cost about $0.25 per task [5]. Optional if budget is tight.
4. **Q3 (agentic search): BrowseComp-Plus, 100-query random subset** [16].
   - Fixed corpus, so the runs are reproducible.
   - Can run **fully on-prem**: index the corpus in pgvector with Qwen3-Embedding-4B. No live web and no contamination.
   - Short answers can be graded by Gemma.
   - Only for frameworks whose retriever is pluggable. Otherwise record "not run".
5. **German check (F6, not a public benchmark).**
   - Translate 5 of the 30 DRB tasks into German with the instruction "Antwort auf Deutsch (Schweiz, kein ß)".
   - Judge with RACE against the English reference, plus a binary check for language and ß.
   - **[E]** RACE validity across languages is unproven, so report this separately and do not mix it into Q1.

### 4.2 Systems under test (fixed conditions)

- Candidates: each shortlisted framework with **Gemma-4-31B** as main model and **Qwen3.5-4B** in summariser/query roles where the framework supports per-role models (E3).
- Baselines on the same 30 tasks:
  - (a) Gemma-4-31B, no search: the floor. Qwen3-32B's no-search prompt already scored 39.5 [25].
  - (b) Gemma-4-31B with the current OWUI native web search.
- Same search stack for all: Serper + Firecrawl through proxy.bs.ch. Same "standard depth" preset, documented per framework in GitOps.
- **Block contamination domains** in search: huggingface.co/datasets and the DRB Space, github.com/Ayanami0730, the DRB arXiv paper and mirrors [19].
- Repetition: 1 full run of the 30 tasks per candidate, plus 3 repeats on 10 tasks to estimate run-to-run variance. VeriTrace measured ±0.3 RACE over 3 runs [23]. **[E]** Treat RACE differences under 2 points as ties. Report bootstrap 95 % CIs over tasks.

### 4.3 Judge: policy decision needed

| Option | Pro | Con |
|---|---|---|
| **A. Official cloud judge** (GPT-5.5 RACE + GPT-5.6 Luna cleaner + GPT-5.4-mini FACT) [1] | Comparable with the current leaderboard and recent papers [24][25] | Sends public DRB prompts plus reports built from public web pages to OpenAI. No personal or internal data, but it is still a cloud-LLM call. A1 governs the *production system*, not the eval harness. Needs an explicit governance OK and an egress exception, or run the harness outside the cluster. **[E]** Judge spend is low hundreds of USD for about 180 reports (prices not verified). |
| **B. On-prem judge** (Gemma-4-31B, or a larger on-prem model if one can be hosted temporarily) | No policy issue | Not comparable with published numbers. **Self-preference bias** when Gemma judges Gemma reports. FACT verification quality drops with weaker judges. |
| **Recommended** | Use **A** for the reported Q1/Q2 numbers. Re-judge the anchors (4.1 step 2) with the same judge. If A is refused, use **B** for *relative ranking only*: calibrate B against A on 10 tasks of public anchor reports (Spearman ρ ≥ 0.8 **[E]**) before trusting it. | |

FACT has to re-fetch every cited URL. Point its scraper at our Firecrawl instead of the default external reader (repo default to verify).

### 4.4 Measuring tokens and runtime (E1, E4, A2, A12)

- Put an OpenAI-compatible gateway (e.g. LiteLLM) in front of vLLM.
- Tag every request with `run_id` and `role` through headers or metadata.
- Record per run: prompt, completion and cached-prefix tokens; number of LLM calls; number of search and fetch calls (Serper and Firecrawl logs); wall-clock time; JSON or tool-call parse failures; run completion status.
- Cross-check against vLLM Prometheus counters and the OTel collector.
- Report median and p90 per depth preset, at concurrency 1 and 4. On-prem latency depends on load.

### 4.5 Pass thresholds

| ID | Gate (MUST) / scoring (SHOULD) | Threshold | Rationale |
|---|---|---|---|
| **Q1** MUST | RACE overall, GPT-5.5 judge, 30-task EN subset | **Gate: ≥ 43.0** (Perplexity Research level under GPT-5.5 [24]) **and ≥ +3 over the Gemma no-search baseline.** Score: 0 if below 43 · 1 for 43–45.5 · 2 for 45.5–47.8 · 3 for ≥ 47.8 (OpenAI DR [24]) | Qwen3-32B frameworks score 41–44.7 under this judge [25]. Gemma-4-31B should do at least as well. With option B, use the same bands relative to re-judged anchors instead. |
| **Q2** MUST | FACT citation accuracy and effective citations per task | **Gate: accuracy ≥ 60 % and ≥ 20 effective citations per task.** Score: 1 for 60–70 % · 2 for 70–75 % · 3 for ≥ 75 % (OpenAI DR 75.0 %, Gemini DR 78.3 % [20]) | ~30B models often score 25–40 % in naive frameworks [22][25]. Evidence-bound designs reach 54–68 % [23][25]. Check O1 coverage (≥ 90 %) separately. |
| **Q3** SHOULD | BrowseComp-Plus, 100-query subset, local corpus | Score: 0 if below 10 % · 1 for 10–25 % · 2 for 25–40 % · 3 for ≥ 40 % (gpt-oss-120B with a good retriever: 42.9 % [16]) **[E bands]** | |
| **Q4** SHOULD | Gap to the best published result for the same framework, or to re-judged anchors | Score 3 if our RACE is within 3 points of the framework's best published frontier-backbone score and citation accuracy ≥ 70 %; 2 within 5 points; 1 within 8 points; else 0 **[E bands]** | Frontier-vs-32B gap within one framework is 7–10 points [25] |
| **E1** MUST | Median counted tokens (input + output) per standard run | **200k ≤ median ≤ 1M; p90 ≤ 1.5M** | Spec. ODR/GPT-4.1 defaults are about 580k [3] |
| **E4** SHOULD | Median wall-clock time per preset at concurrency 1 | Quick ≤ 5 min · Standard ≤ 20 min (p90 ≤ 30) · Deep ≤ 120 min. Score 3 if all are met, 2 if standard is ≤ 30 min, 1 if ≤ 60 min | GPT-Researcher deep is about 5 min on a cloud model [36]. VeriTrace with Qwen3.5-27B is 57 min [23]. |
| A2 (same runs) | Completion rate with Gemma-4-31B | ≥ 90 % of the 30 runs produce a report; log parse failures per run | Spec |

---

## 5. Open questions

1. **Cloud judge policy:** may the eval harness send public DRB prompts and our generated reports (built from public web) to OpenAI for judging? If not, we accept non-comparable on-prem judging (§4.3 B).
2. **Judge budget:** current GPT-5.5 and GPT-5.4-mini prices and a realistic per-report token count for RACE and FACT are not published in the DRB repo. Run a 3-task pilot to measure.
3. **German validity:** no German DR benchmark exists. Do we accept the 5 translated tasks as a signal, or commission about 10 Swiss-administration tasks with DRB-II-style binary rubrics written by staff? That would be internal, not public.
4. **No published data** exists for Gemma-4-31B on any report benchmark, or for DeerFlow, STORM, GPT-Researcher or Local Deep Research on DRB with open backbones. Our reproduction is the only Q4 evidence for those.
5. **Thinking mode:** do we run Gemma-4-31B with thinking on? It probably raises quality and multiplies output tokens (compare the GPT-5 ODR run at about 2M tokens per task [3]). Fix this per preset before E1 is measured.
6. **Serper vs. benchmark contamination:** confirm that Serper supports domain exclusion (`-site:`) reliably for the blocklist.
7. **Self-reported paper numbers** (WebWeaver, VeriTrace, ScaffoldAgent) use different search APIs (Serper, Bocha) and judges. Treat them as directional, not as leaderboard entries.
8. **DRB task fit:** DRB topics are PhD/industry-level, not cantonal administration. Is a DRB score accepted as a proxy for Bebbi Bot users, or does steering want the internal German set (Q3 of this list) to carry weight too?

---

## Sources

1. DeepResearch Bench README (judges, news): https://github.com/Ayanami0730/deep_research_bench
2. DeepResearch Bench paper: https://arxiv.org/abs/2506.11763
3. LangChain open_deep_research README (RACE, cost, tokens): https://github.com/langchain-ai/open_deep_research
4. DRB II page: https://agentresearchlab.com/benchmarks/deepresearch-bench-ii/index.html
5. DRB II paper: https://arxiv.org/html/2601.08536v1
6. DRB II leaderboard CSVs: https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard/blob/main/data_drb2/leaderboard_gemini25.csv and `/data_drb2/leaderboard.csv`
7. DeepResearchGym paper: https://arxiv.org/html/2505.19253v1
8. LiveResearchBench repo: https://github.com/SalesforceAIResearch/LiveResearchBench
9. LiveResearchBench paper: https://arxiv.org/html/2510.14240
10. ResearchRubrics: https://alphaxiv.org/abs/2511.07685 (dataset: https://huggingface.co/datasets/ScaleAI/researchrubrics)
11. ReportBench: https://arxiv.org/html/2508.15804v1
12. DeepConsult, as used in VeriTrace [23] (Table 4 / Table 16)
13. Mind2Web 2: https://arxiv.org/abs/2506.21506
14. DR³-Eval: https://arxiv.org/abs/2604.14683
15. BrowseComp: https://arxiv.org/abs/2504.12516 (OpenAI DR 51.5 %, GPT-4o browsing 1.9 %)
16. BrowseComp-Plus: https://arxiv.org/html/2508.06600
17. BrowseComp-ZH: https://arxiv.org/abs/2504.19314
18. Local Deep Research README: https://github.com/LearningCircuit/local-deep-research
19. Search-time contamination: https://arxiv.org/abs/2606.05241
20. DRB v1 leaderboard CSV (legacy Gemini judge): https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard/blob/main/data/leaderboard.csv. FACT detail files: `/data/fact_results/*/fact_result.txt`
21. DR Tulu paper: https://arxiv.org/html/2511.19399 (repo https://github.com/rlresearch/dr-tulu)
22. WebWeaver paper: https://arxiv.org/html/2509.13312v3
23. VeriTrace paper (Qwen3.5-27B controlled comparison, cost Table 15, judge Table 16): https://arxiv.org/abs/2605.26081
24. DRB v1 leaderboard, GPT-5.5 judge: https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard/blob/main/data_gpt55/leaderboard.csv
25. ScaffoldAgent paper (same-backbone Qwen3-32B framework comparison, GPT-5.5 judge, Tables 1, 2, 9, 10): https://arxiv.org/abs/2606.20122
26. Tongyi DeepResearch technical report: https://arxiv.org/html/2510.24701v1, model https://huggingface.co/Alibaba-NLP/Tongyi-DeepResearch-30B-A3B
27. MiroThinker repo: https://github.com/MiroMindAI/MiroThinker
28. Qwen3.5-27B model card: https://huggingface.co/Qwen/Qwen3.5-27B
29. Qwen3.5-4B model card: https://huggingface.co/Qwen/Qwen3.5-4B
30. Gemma-4-31B-it model card: https://huggingface.co/google/gemma-4-31B-it
31. LDR community benchmarks: https://huggingface.co/datasets/local-deep-research/ldr-benchmarks
32. HF Open Deep Research blog: https://huggingface.co/blog/open-deep-research
33. Anthropic, multi-agent research system: https://www.anthropic.com/engineering/multi-agent-research-system
34. ODR configuration defaults: https://github.com/langchain-ai/open_deep_research/blob/main/src/open_deep_research/configuration.py
35. GPT-Researcher PyPI/FAQ (~2 min, ~$0.005): https://pypi.org/project/gpt-researcher/0.9.2 , https://docs.gptr.dev/docs/faq
36. GPT-Researcher deep research docs: https://docs.gptr.dev/docs/gpt-researcher/gptr/deep_research
37. Gemini Deep Research token report (forum): https://discuss.ai.google.dev/t/deep-research-max-preview-04-2026-consuming-millions-more-tokens-than-it-should/145356
38. DRB leaderboard Space files (raw reports per system): https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard/tree/main/data/raw_data
