# Orchestration patterns from the bigger engines: what to borrow, what to avoid

Scope: control flow of a lean in-house research agent (Gemma-4-31B, 128k ctx, Serper + Firecrawl + MCP, German reports, Open WebUI pipe, night-window queue). Source code and prompts were read, nothing was run. Local evidence comes from internal analysis. Open WebUI statements (section 7) are from memory of its function API, not verified in this session.

Repos read: open_deep_research (`src/open_deep_research/{deep_researcher,prompts,configuration,state,utils}.py`, last commit 2026-08-10), Onyx (`backend/onyx/deep_research/dr_loop.py`, `tools/fake_tools/research_agent.py`, prompts read via `git show` because the clone is sparse), NVIDIA Deep Researcher 2.2 (`agents/deep_researcher/{prompts,models/subagent_contracts.py}`, `agents/clarifier`, `configs/domain_catalogs`), DeerFlow (local clone is 2.0, a general super-agent with no plan-approval graph; the 1.x flow was read from GitHub `main-1.x` `src/graph/nodes.py` and `src/prompts/planner.md` via fetch summary), GPT-Researcher 0.16 (`skills/deep_research.py`, installed in `candidates/gpt-researcher/.venv`).

## 1. Summary table

| Technique | Source | Phase | Value | Cost | Gemma fit | Priority |
|---|---|---|---|---|---|---|
| Plan with `required_components` (id, name, description) + `constraints` + `answer_type` | NVIDIA `ResearchPlan` | plan | High: made NVIDIA reports mirror the prompt (RACE 46.5 vs GPT-R 45.2 on shared tasks; GPT-R missed named entities entirely) | 1 call, ~2-3k completion | Good as plain JSON, 5 fields per component | MUST |
| Every sub-question carries `target_components` and is self-contained | NVIDIA `ResearchQuery`, Onyx "agent has no context" | plan -> research | High: fixes drift and gives a coverage ledger | 0 | Good | MUST |
| Always re-inject the original task into every sub-run | Counter-example GPT-R (drift, internal analysis) | research | High | 0 | n/a | MUST |
| Clarify first, JSON `{need_clarification, questions[], assumptions}`, max 1 round, skippable | open_deep_research `ClarifyWithUser`, Onyx, NVIDIA clarifier | pre-plan | Medium-high (F1) | 1 small call, ~1k tokens | Good, no tools needed | MUST |
| Background search on the raw query before planning | DeerFlow 1.x `background_investigation_node`, GPT-R `generate_research_plan`, NVIDIA planner discovery | pre-plan | Medium: plan uses real source families, not guesses | 1 search (+ one 2-4k prompt) | Good if truncated to titles/snippets | SHOULD |
| Plan approval as chat turn: render plan as numbered Markdown, user answers "ok" or pastes an edited list | DeerFlow 1.x `interrupt` + `[ACCEPTED]`/`[EDIT_PLAN]` (idea), adapted | plan | Required (F2) | 1 more small call to parse edits | Good: edit parsing is small JSON | MUST |
| Per-sub-question researcher with bounded tool loop (3-5 calls) and explicit stop rules | open_deep_research `max_react_tool_calls`, Onyx `MAX_RESEARCH_CYCLES=8`, NVIDIA "1 primary + 1 fallback call" | research | High | Dominant token cost | Medium: native tool calling works with vLLM `gemma4` parser, but keep to 2-4 tools | MUST |
| Parallel researchers, hard concurrency cap (3-5) | all four | research | Wall-clock only; on-prem GPU is the bottleneck | 0 extra tokens | Fine; vLLM batches | SHOULD (cap 3) |
| Think/reflect step between rounds, producing a list of gaps | open_deep_research `think_tool`, Onyx `think_tool` | reflection | Medium. Better as a plain JSON call than as a tool | ~1-2k per round | Better as JSON (see 2.7) | SHOULD |
| Gap check = coverage ledger over `required_components` + "last round added few new sources" | derived from Onyx stop list, NVIDIA `ResearchGap` | stop | High; deterministic half is free | 1 small call per round | Good | MUST |
| Compress each researcher's raw tool output into structured notes with source ids, before the writer | open_deep_research `compress_research`, NVIDIA `ResearchNotes`, Onyx intermediate report | research -> write | High: only way to fit 128k | 1 call per sub-question, 2-5k completion | Medium: "preserve verbatim" prompts work, long outputs drift; use JSON findings | MUST |
| Source ids assigned by code, not by the LLM; writer sees `[n]` -> url table | Onyx `citation_mapping` + `collapse_citations` | write | High for citation binding (NVIDIA's weak spot) | 0 | Good | MUST |
| One citation per sentence, finding = (claim, short verbatim quote, one source id) | internal analysis items 1-2 | notes + write | High (FACT, est. +8 to +15 pp) | +3% | Good | MUST |
| Source router: preset YAML says which tool families for which component type | NVIDIA domain catalog + `SourceRoutingPlan` | plan | High for us (law and open data via MCP were barely used by the engines, `german-set.md`) | 0 if done by preset; 1 small call if LLM-routed | Deterministic preset + planner `preferred_tools` is more reliable than an LLM router | MUST (preset form) |
| Budget object: max rounds, queries, fetches, tokens, wall time; "force report" when exceeded | Onyx 30 min force-report, NVIDIA `resource_limits`, open_deep_research iteration caps | all | Required (E2, G2) | 0 | n/a | MUST |
| Self-judged `evidence_judgment` score (0-100) per note | NVIDIA | write | Low-medium: only used to weight notes in writer prompt | ~0 | Self-scores from a 30B are weakly calibrated | COULD |
| Supervisor LLM deciding delegation by tool call (ConductResearch / ResearchComplete) | open_deep_research, Onyx orchestrator | research | Flexibility | Re-sends growing history every cycle | Weak: needs reliable multi-tool calls with long histories | AVOID (use code loop) |
| Orchestrator LLM that only forwards between sub-agents | NVIDIA orchestrator | all | None beyond a code loop | ~12% of prompt tokens, 8.5k prompt per start | Weak | AVOID |
| Full-text page summarization per search hit | open_deep_research `summarize_webpage_prompt` | research | Medium (shrinks pages) | 1 call per hit | Fine with `gemma-fast` | COULD |
| Recursive depth with follow-up-only queries | GPT-R `deep_research` | research | Negative as shipped (drift) | Cheap | n/a | AVOID in that form |
| Writer retry with progressive truncation on context overflow | open_deep_research `final_report_generation` | write | Safety net | 0 | Needs token counter, not "4 chars per token" | SHOULD |

## 2. Details per technique

### 2.1 Clarifying questions

- open_deep_research `clarify_with_user` (`deep_researcher.py`, `prompts.py:clarify_with_user_instructions`): one structured-output call returning `{need_clarification: bool, question: str, verification: str}`. Prompt rules: if the history already contains a clarifying question, "almost always" do not ask again; ask about acronyms and unknown terms; be concise, bullets; do not ask for what the user already gave. When no question is needed the model writes a short acknowledgement ("verification") that is shown to the user, which doubles as a status message. Config `allow_clarification` (default True). Cost: one call with the conversation, ~1k tokens.
- Onyx (`orchestration_layer.py:CLARIFICATION_PROMPT`): the model either asks or calls `generate_plan` (no-arg tool = "no clarification needed"). Rules: never answer the query; skip clarification when the query is longer than 3 sentences; at most 5 numbered questions; friendly "could you" tone; a closing sentence on what the answers will help with. A config flag `SKIP_DEEP_RESEARCH_CLARIFICATION` and a per-request `skip_clarification` exist.
- NVIDIA clarifier (`clarifier/prompts/research_clarification.j2`): JSON only, `needs_clarification`; may run 1-2 searches first ("search first, ask second") so it does not ask the user to define terms a search resolves; max two questions over the whole conversation, never the same dimension twice; explicit list of "does not need clarification" examples.
- Robustness: all three are a boolean plus text. Easy for Gemma with `response_format` JSON or a simple prompt plus `json_repair`.
- Borrow: Onyx's "long query (> 3 sentences or a named structure) means skip", open_deep_research's "already asked once, do not ask again", NVIDIA's "max 2 questions and never the same dimension". Add Basel-specific questions via preset (Zeitraum, Rechtsstand/Stand-Datum, Kanton BS vs Bund, Quellenpolitik, gewünschte Gliederung). Make the output `{need_clarification, questions[<=4], assumptions[]}`; if the user skips, the assumptions are written into the plan header, so the report states what was assumed (this is what the `german-set` rubric's "limits stated" and "Stand" criteria reward).
- Sketch: `clarify(task, history) -> {need: bool, questions: [str], assumptions: [str]}`; the pipe returns the questions as a normal assistant message and ends the turn. The next user turn re-enters with the history and a counter (max 1 round) kept in the job row.

### 2.2 Research brief / plan schemas

- open_deep_research: the brief is one free-text paragraph (`ResearchQuestion.research_brief`), first person, "list key dimensions, mark unstated ones as open-ended, do not invent constraints, prefer official sources, answer in the query's language". It is the only task description the supervisor and writer get. Simple, but no component list, so coverage is checked only by the supervisor's judgement (think_tool).
- Onyx: the plan is a numbered list of at most 6 steps, plain text ("6 or less individual steps", "standalone exploration question", "same language as the user"). The prompt includes anti-refusal text because some models claimed the plan was infeasible. No schema, no parser. Very robust, least structure.
- DeerFlow 1.x planner: JSON `{locale, has_enough_context, thought, title, steps[{need_search, title, description, step_type: research|analysis|processing}]}`, max `max_step_num` steps (default 3), default `max_plan_iterations` 1. `has_enough_context` is true only if existing info fully answers all aspects (strict, default false), so the planner can short-circuit to the reporter after background investigation. Code repairs missing `step_type` and forces at least one `need_search` step (`validate_and_fix_plan`).
- NVIDIA `ResearchPlan` (`models/subagent_contracts.py`): `task_analysis{user_intent, explicit_requirements[], implicit_requirements[], out_of_scope[], language}`, `answer_strategy{answer_type enum, title, required_components[{id,name,description}]}`, `constraints[{category enum content|source|structure|depth|format|exclusion, constraint, rationale}]`, `queries[{query, subqueries[], preferred_tools[], fallback_tools[], target_components[], rationale}]` (max 20). Strict (`extra=forbid`) pydantic. This is the structure that made reports mirror the task: the writer gets component ids and constraints and the researcher notes carry `target_components`.
- Evidence it works: NVIDIA RACE lead is "structure: required_components and constraints turn the prompt's axes into section headings" (`nvidia-quality.md`). GPT-R, with no such object, produced 0 mentions of Norway/GIC/Temasek on task 53 and "clothing" 0 times on task 51.
- Robustness: NVIDIA's schema is deep (nested lists, enums, 4 levels). It ran on Gemma through LangChain structured output, but the planner call is also a tool-using subagent with 7 calls and 5.8k-17.9k growing prompts (`nvidia-tokens.md`), so most of the cost is the tool loop, not the schema. A flattened version is safer: drop `task_analysis` sub-lists into two string lists, keep `components`, `constraints`, `subquestions`.
- Minimal schema for us (JSON, repaired with `json_repair` as GPT-R does):

```json
{
  "language": "de",
  "title": "...",
  "answer_type": "report|brief|table|comparison",
  "explicit_requirements": ["..."],
  "assumptions": ["..."],
  "components": [{"id": "c1", "name": "...", "description": "what the report must cover", "must_name": ["entities that must appear"]}],
  "constraints": ["Stand-Datum nennen", "Primärquellen zuerst", "..."],
  "subquestions": [{"id": "q1", "question": "self-contained, names all entities",
                     "components": ["c1"], "sources": ["law","opendata","web"], "queries_hint": ["..."]}]
}
```
`must_name` is our addition against the GPT-R failure mode (missing named entities); a regex check over the final report can verify it for free.

### 2.3 Dispatch: parallel vs sequential

- open_deep_research: supervisor emits up to `max_concurrent_research_units` (default 5) `ConductResearch` tool calls per iteration; executed with `asyncio.gather`; overflow calls get an error message; hard cap `max_researcher_iterations` (default 6). Prompt: "bias towards single agent", comparisons get one agent per element.
- Onyx: orchestrator, at most 3 parallel `research_agent` calls, `MAX_ORCHESTRATOR_CYCLES` 8 (4 for reasoning models, which drop the think tool); thread pool with 30 min per-agent timeout and a failure message returned to the orchestrator.
- NVIDIA: planner returns all queries; orchestrator makes one `run_research_batch` call (max 6 concurrent, 20 queries); ledger of already-submitted queries; "do not create smaller curated waves". One wave, no iteration. Gaps are recorded in notes but nothing consumes them (no second round in the prompts: `orchestrator.j2` only retries failed queries).
- GPT-R: concurrency 2 via semaphore, but the depth recursion is sequential per branch.
- For us: the GPU serves one Gemma; parallel researchers only help wall time through vLLM batching, and the run is in the night window anyway. Use `asyncio.Semaphore(3)` over sub-questions inside a round; rounds are sequential. NVIDIA's six parallel researchers produced 50 calls and ~862k tokens, so concurrency does not reduce tokens, it only changes wall time.

### 2.4 Stopping criteria ("enough evidence")

- open_deep_research researcher prompt: simple queries 2-3 searches, complex up to 5; stop immediately when you can answer comprehensively, have 3+ relevant sources, or "your last 2 searches returned similar information". Code: `max_react_tool_calls` (default 10) and a `ResearchComplete` tool. Supervisor: think after each ConductResearch ("what is missing? enough?"), stop at `max_researcher_iterations` or `ResearchComplete`.
- Onyx orchestrator: call `generate_report` when the plan is covered, the model has deviated from the plan and is done, all aspects are answered, or "the last cycle yielded minimal new information". Cycle counter is injected into the system prompt each cycle ("used 3 of 8"). Wall clock: forced report after 30 min; sub-agent forced intermediate report after 12 min. Final guard in code: last cycle or timeout skips the LLM and writes.
- DeerFlow: `has_enough_context` (planner), `max_plan_iterations`.
- NVIDIA: researcher budget "one primary call plus at most one fallback"; planner "dynamic discovery budget: continue only while it changes the plan materially"; run-level `max_source_tool_calls` 100, circuit breaker after 8 consecutive tool failures.
- Evidence: open_deep_research's stop rules are LLM judgements; Onyx/NVIDIA add counters. Nobody uses a deterministic coverage test, which is the cheap, strong signal available to us because we have `components`.
- Proposed stop test per round (code decides, LLM only proposes follow-ups):
  1. Budget exhausted (rounds, fetches, tokens, wall time) -> stop.
  2. For each component: count distinct fetched sources whose findings tag it. Component is "covered" at >= `min_sources_per_component` (preset, default 2; 1 for law) .
  3. All covered, or the last round added < N new distinct domains/findings (saturation) -> stop.
  4. Else one small JSON call: given uncovered components and the notes' `gaps`, emit <= 4 new self-contained sub-questions. Round cap 2-3.

### 2.5 Compression between phases

- open_deep_research: per-search-result summarization with `summarization_model` (JSON `{summary, key_excerpts}`, 25-30% of original, `max_content_length` 50000 chars); then `compress_research` per researcher: "preserve ALL relevant info verbatim, list queries, findings with inline citations, sources list", retries 3 times, on context overflow removes messages up to the last AI message and retries. Compressed text goes to the supervisor as the tool result; raw notes are kept separately. Final writer gets only the compressed notes (+ brief, + messages), truncated by `4 * model_token_limit` chars on overflow.
- Onyx: sub-agent writes an intermediate report ("several pages, facts only, no analysis, cite every fact inline as [n]", `MAX_INTERMEDIATE_REPORT_LENGTH_TOKENS=10000`, comment says ~5,000 tokens works well). Orchestrator history only holds those reports (not raw pages). Citation numbers are global: the tool assigns the number to each document, sub-agent reports keep markers, `collapse_citations` renumbers and merges mappings; the final writer is given only cited documents (`final_documents`).
- NVIDIA: researcher returns `ResearchNotes` JSON (summary, findings[claim, evidence, source_ids, confidence, caveats], gaps, sources, narrative_notes, language, evidence_judgment). Persisted as files, orchestrator then pulls the whole notes array back into its context (20-25k prompts, `nvidia-tokens.md`), writer reads files sequentially (+1.8-2k per call).
- GPT-R: learnings (max 3 per query, `max_tokens=4000`) as `{insight, sourceUrl}`; final context is the last 25,000 words (tail-trim drops the learnings first). Compression itself is weak and the trim policy is a known fault.
- Recommendation: structured notes per sub-question, in JSON, with (claim, quote <= 40 words verbatim, source_id) triples built so that the quote can be string-matched against the fetched page (cheap faithfulness check, no LLM). Keep raw pages on disk for the evidence trail (O3) and for the claim check. Target 1.5-3k tokens of notes per sub-question; 8 sub-questions -> 12-24k notes for the writer, well inside 128k and leaving room for a 20k-token report.

### 2.6 Source routing

- NVIDIA: `source-router-agent` makes one call to `lookup_source_catalog`, picks one `domain_id` from a YAML catalog (`configs/domain_catalogs/deep_research_domain_catalog.yml`: per domain `preferred_source_ids`, `fallback_source_ids`, `is_default`), and returns `SourceRoutingPlan` (recommendations with tool names and priority, fallbacks, planner_guidance). The planner copies tool names into each query's `preferred_tools`/`fallback_tools`; researchers are told to try them in order but all tools stay callable (advisory). Cost on our run: two `gemma-fast` calls of ~3.1k and ~3.4k tokens, trivial. Weakness: in our `german-set` analysis NVIDIA cited MCP data as a bare tool name; routing chose the source but the writer had no URL to cite.
- open_deep_research: no routing; the researcher gets all tools, optional `mcp_prompt` text and `mcp_config` tool filter. GPT-R: retrievers fixed per run; MCP retriever got the full unfiltered tool list and a drifted sub-query (`german-set.md`).
- Onyx: the orchestrator task text can say "focus on internal vs web" (`INTERNAL_SEARCH_RESEARCH_TASK_GUIDANCE`); clarification asks the user which source when ambiguous.
- For us: do it as preset data, not as an LLM agent. Preset YAML maps component types or keywords to source families (`law` -> opencaselaw tools `get_legislation`, `search_decisions`; `parliament`/`statistics` -> data.bs.ch tools; `web` -> Serper+Firecrawl with allow/deny domains). The planner fills `sources` per sub-question from the preset's menu (enum-constrained); the researcher gets only the tool schemas for those families (3-6 tools instead of 45+5+2), which also removes the "full unfiltered tool list" failure. Every MCP result must be turned into a citable record `{id, title, url_or_uri, retrieved_at, text}` by the tool wrapper (e.g. `https://mcp.opencaselaw.ch/entscheid/...`, dataset URL on data.bs.ch with the dataset id), so the writer never has to cite a tool name.

### 2.7 Reflection / think tool

- open_deep_research and Onyx both use a `think_tool(reflection: str)` that returns a canned acknowledgement. Purpose: force a pause for non-reasoning models. Both prompts forbid calling it in parallel with search.
- Cost: each think is a full model turn re-sending the growing history. Onyx drops the think tool for reasoning models (cycles 8 -> 4). Gemma-4 has a thinking switch (`gemma-think`), which does the same job natively inside the call.
- Recommendation: do not implement think as a tool. After each search/read batch, either rely on `gemma-think` for the next tool-calling turn or run a separate cheap JSON reflection `{covered: [...], gaps: [...], next_queries: [...], stop: bool}` over the compact notes so far, not over the raw history.

### 2.8 HITL plan approval in a chat UI

- DeerFlow 1.x: LangGraph `interrupt("Please Review the Plan.")` in `human_feedback_node`; the next resume value is a string; `[ACCEPTED]` proceeds to research, `[EDIT_PLAN]` (with the user's text appended) returns to the planner with the feedback as context; anything else loops to the planner; `max_plan_iterations` caps loops; `auto_accepted_plan` skips it. Requires a checkpointer. The frontend renders the plan card with Accept/Edit buttons.
- Onyx: the clarification turn ends the HTTP request with the question (`state_container.set_is_clarification(True)`); the plan is generated and streamed to the UI as plan packets but is not approved or edited by the user.
- NVIDIA frontends and open_deep_research: no plan approval (open_deep_research ends the graph with a question for clarification, then restarts on the next message with full history).
- Mechanics for an Open WebUI pipe (verify against v0.11.4): a pipe receives the full `messages` list each turn and is otherwise stateless, so the multi-turn flow is: turn 1 -> clarification or plan returned as the assistant message; turn 2 -> pipe inspects the last assistant message for a hidden marker (HTML comment `<!-- dr:job=<uuid> state=plan_pending -->`) and the user's reply. Store the real state (plan JSON, status) in the job service (Postgres), keyed by the job id from the marker, not in the chat text. Reply parsing: (a) approve words ("ok", "ja", "start", "freigeben") -> enqueue job; (b) any other text -> one small `gemma-fast` JSON call `{plan, changed}` that applies the edit instruction to the plan JSON, re-render, ask again (cap 3 rounds); (c) the user can also paste an edited numbered list, which the same call normalizes. Prefer numbered Markdown rendering of components and sub-questions so references like "streiche 3, füge Bundesgericht zu 2 hinzu" are unambiguous. `__event_call__`-style modal prompts would hold the HTTP connection open and conflict with the night queue, so use chat turns.
- Cost: one 1-2k call per edit round.

### 2.9 Budget enforcement

- open_deep_research: `max_researcher_iterations` 6, `max_react_tool_calls` 10, `max_concurrent_research_units` 5, `max_structured_output_retries` 3, token-limit retry. No wall-clock or token budget.
- Onyx: cycles (8/4), per-agent cycles (8), 30 min / 12 min wall-clock thresholds that force report generation, `max_tokens` 1024 on orchestrator turns ("prevents endless loops of null tokens"), report `MAX_FINAL_REPORT_TOKENS` 20000, minimum model context 50k.
- NVIDIA: `resource_limits` (queries 20, source tool calls 100, consecutive failures 8, run seconds 3600, note and state bytes), configurable downwards only. Observed median 40-70 LLM calls per task so the call budget "is not binding" (`nvidia-quality.md`); tokens were the problem, not calls.
- Lesson: count budgets that matter to us: tokens (sum prompt+completion from the gateway), wall time, fetched pages, searches, rounds. Check them in the loop code between steps; when exceeded, jump to the writer with what exists and append the "Offene Punkte" section listing uncovered components.

### 2.10 GPT-Researcher: what to keep, what made queries bad

- Keep: `json_repair` loading with regex fallbacks for JSON blocks and "query:/goal:" line patterns (`_load_repaired_json`, `parse_search_queries_response`), per-query `researchGoal` field (gives each search a purpose), skip-descent when a level produced no results, concurrency semaphore.
- Bad: (1) follow-up depth recursion passes only "Previous research goal + follow-up questions" so the task disappears (internal analysis cause 1; task 53 searches for EU taxonomy and New Mexico fund); (2) duplicates (same query three times); (3) the "follow-up questions" in `generate_research_plan` are auto-answered "Automatically proceeding with research" so they carry no user information; (4) final context tail-trim drops learnings; (5) writer prompt has no coverage instruction. Fixes are the opposite: re-inject the task, dedupe, ledger, never trim from the front.

## 3. Token and robustness evidence

| Engine | Measured (this repo) | Why |
|---|---|---|
| NVIDIA DRA 2.2 | 862k median (868k prompt vs 60k completion), 50 calls, 868 s | Page text inlined into researcher messages and re-sent each call (15-40k prompts); orchestrator re-reads all notes; writer reads files turn by turn |
| GPT-R | 215k median, 33 calls, 633 s | Small prompts (~700 tokens), no re-sent history |
| Plain agent loop (16 tool calls max) | 21.9k median, 168 s on German set | Short loop; beat both engines on the German rubric (50.0 vs 46.7 NVIDIA, 38.3 GPT-R) |
| open_deep_research, Onyx | not run here | Same shape as NVIDIA (growing histories re-sent per cycle); published RACE 43.4 / 54.5 used frontier models, not ~30B |

Takeaway: the cheap designs that win for us re-send small prompts (GPT-R style) but keep the task in every call and keep structure (NVIDIA style). Prefix caching in vLLM makes re-sent history cheaper in compute, but decode tokens (thinking) remain the scarce resource.

Structured-output reliability: all engines use LangChain `with_structured_output` or tool calls, with retry (open_deep_research `max_structured_output_retries=3`). GPT-R is the only one that treats JSON as untrusted text and repairs it, and it ran 660 requests on Gemma with no 4xx/5xx and no parse breakage reported. Recommendation: plain "return JSON only" prompts, schema in the prompt, `json_repair`, then pydantic validation, then one repair re-ask with the validation error. Use native tool calling only inside the researcher loop (search, fetch, MCP), where it is unavoidable, with at most ~6 tools per step.

## 4. Recommended control flow (single process, no LangGraph)

```python
async def run_job(job):                      # job row in Postgres; state saved after each step
    cfg = load_preset(job.preset)            # YAML: sources, domains allow/deny, budgets, prompts slots
    B = Budget(cfg.budgets)                  # tokens, wall, searches, fetches, rounds

    # --- phase 0: chat turns (online, cheap) --------------------------------
    if job.state == "new":
        c = await llm_json(CLARIFY, task=job.task, history=job.history, role="fast")
        if c.need_clarification and job.clarify_rounds == 0:
            return ask_user(c.questions)                   # turn ends; marker in message
        job.assumptions = c.assumptions
        hits = await search(job.task, n=5, titles_only=True)   # background investigation
        job.plan = await llm_json(PLAN, task=job.task, assumptions=job.assumptions,
                                  hits=hits, source_menu=cfg.source_menu, role="think")
        job.plan = validate_and_repair(job.plan)           # fix ids, enum sources, >=1 search step
        return show_plan_and_wait(job)                     # state = plan_pending
    if job.state == "plan_pending":
        if is_approval(user_msg): enqueue(job, window=cfg.window); return "queued"
        job.plan = await llm_json(EDIT_PLAN, plan=job.plan, instruction=user_msg, role="fast")
        return show_plan_and_wait(job)                     # max 3 edit rounds

    # --- phase 1: research (night window worker) ---------------------------
    ledger = Ledger(job.plan)                # sources{id->record}, notes[], components{id->set(source_ids)}, asked_queries
    todo = job.plan.subquestions
    for round_no in range(cfg.max_rounds):                 # 2-3
        async with Semaphore(cfg.concurrency):             # 3
            notes = await gather(*[research_one(q, job.task, job.plan, ledger, B) for q in todo])
        ledger.add(notes)
        if B.exhausted(): break
        cov = ledger.coverage(min_sources=cfg.min_sources_per_component)
        if cov.all_covered or ledger.saturated(last_round_new_sources < cfg.min_new): break
        gaps = await llm_json(REFLECT, plan=job.plan, uncovered=cov.uncovered,
                              note_gaps=ledger.gaps(), asked=ledger.asked_queries, role="fast")
        todo = dedupe(gaps.next_subquestions, ledger.asked_queries)[:cfg.max_new_q]
        if not todo: break

    # --- phase 2: write (only cited ids from ledger) -----------------------
    report = await write_sections(job.plan, ledger, cfg)   # per component group if > N notes
    report = enforce_citations(report, ledger)             # strip [n] not in ledger; one cite/sentence check
    report = append_open_points(report, ledger.uncovered(), B.reason)
    post(job.chat_id, report, evidence_trail=ledger.export())

async def research_one(q, task, plan, ledger, B):
    ctx = f"Gesamtaufgabe: {task}\nTeilfrage: {q.question}\nKomponenten: {q.components}"  # always re-inject task
    msgs = [system(RESEARCHER, tools=tools_for(q.sources)), user(ctx)]
    for step in range(cfg.max_steps):                      # 4-6 tool calls, per sub-question budget
        if B.exhausted(): break
        r = await llm_tools(msgs)                          # search / fetch / mcp_*; fetch returns focused passages
        if not r.tool_calls: break
        msgs += run_tools(r.tool_calls, ledger)            # tools register records, return text tagged [id]
        msgs = trim_old_tool_outputs(msgs)                 # keep last 2 tool outputs in full, older -> 1-line stubs
    return await llm_json(NOTES, msgs=msgs, schema=Notes)  # findings[{claim, quote, source_id, components}], gaps[]
```

Design notes:
- Writer input = plan (components, constraints, must_name) + notes JSON + `source_id -> title,url,date` table. The writer may cite only ids in the table; `enforce_citations` drops unknown ids and checks each cited quote is a substring of the stored page (cheap, no LLM). An optional claim check with `gemma-fast` (est. +100-200k tokens, +10 to +15 pp FACT per `nvidia-quality.md` item 4) runs only if the budget allows.
- Roles: `gemma-fast` (thinking off) for clarify, reflect, edit-plan, notes JSON; `gemma-think` for plan, researcher tool turns, writer.
- Preset YAML slots: source menu and domain allow/deny, `min_sources_per_component`, round and step caps, writer instructions (structure, "Stand", "Offene Punkte", Swiss spelling), clarification questions to always consider.
- Quick mode (immediate): skip clarification and approval, 1 round, 4 sub-questions, no per-component writer split.
- Rough token budget (estimate, not measured): plan 10-15k; 8 sub-questions x (4-6 tool turns at 6-15k prompt, thinking off for reading) = 150-300k; notes JSON 8 x 8k = 64k; reflection 10k; writer 30-45k prompt + 15-20k completion. About 300-450k per standard run, inside the 200k-1M gate. Needs measuring.

## 5. Anti-patterns (caused blow-up or drift)

1. Sub-researchers or recursion that see only their own query (GPT-R): drift to niche topics, missing named entities. Always pass the task + plan components.
2. Letting page text accumulate in the message list across tool calls (NVIDIA: 78% of prompt tokens in calls with 15k+ context, 93% of tokens are prompt). Trim old tool outputs to stubs after they have been noted; return focused passages, not page heads.
3. LLM supervisor/orchestrator that re-reads all notes each cycle and decides by tool call (open_deep_research supervisor, NVIDIA orchestrator, Onyx orchestrator): history re-sent every cycle, needs reliable multi-tool calling on long contexts. Use a code loop.
4. Think tool as a separate turn after every search: one extra full-history call per search. Use thinking mode or a compact JSON reflection per round.
5. Tail-trimming the writer context (GPT-R keeps the last 25k words; learnings are dropped first) and "4 chars per token" truncation. Budget the notes by component instead.
6. Stacked citations and LLM-assigned citation numbers (NVIDIA: 59% of fact-URL pairs from multi-URL sentences, valid 46% vs 67% for single). Code assigns ids; one id per sentence.
7. Citing a tool name instead of a URL for MCP results (NVIDIA on DE-ST1). Wrap MCP results into citable records.
8. Giving the researcher the full unfiltered MCP tool list (GPT-R: 45+5 tools). Filter per sub-question.
9. Planning that cannot be checked: free-text brief only (open_deep_research) means coverage depends on model judgement; no gap loop at all (NVIDIA records `gaps` but never acts on them). Use component ids and a coverage ledger.
10. "Be exhaustive, preserve everything" compression prompts with no cap (open_deep_research, Onyx reports "several pages"): long outputs, and a 30B model starts paraphrasing and inventing specifics. Cap length, force verbatim quotes.
11. Self-reported scores as control signals (`evidence_judgment`, "I am satisfied"): poorly calibrated for 30B models; use counts.
12. Auto-answering clarification questions (GPT-R "Automatically proceeding with research"): wastes the step. If skipped, record assumptions in the report.
13. No dedupe of queries (task 53 repeated one query three times). Keep an `asked_queries` ledger.
14. Wall-clock only guards (Onyx 30 min) without a token budget: a night-window job can still burn the quota. Enforce tokens and time.
15. Over-asking: multi-round clarification. Max one round; skip for long, specific prompts.
16. LangGraph dependency: all four engines use it (or DeepAgents on top). It adds checkpointing and streaming, but our job service already persists state in Postgres and our flow is a fixed 3-phase pipeline with one loop. Not clearly worth it; revisit only if we need resumable mid-research graph state.

## 6. Open questions to test

- Does Gemma-4-31B call 4-6 tools reliably over 6-8 turns with the `gemma4` tool parser, or is a "JSON action per turn" loop (`{"action":"search|fetch|mcp|finish", ...}` with repair) more robust? Measure parse failures per run on 5 tasks.
- Does the fixed-menu source preset beat an LLM router on the 13 German tasks (MCP use rate was 4/8 for the plain agent, 7-12% of cited URLs)?
- Does the quote-substring check correlate with FACT accuracy? (cheap to compute on existing runs).
- Plan approval parsing: how often does `gemma-fast` mangle an edited plan? Keep a fallback of "show diff, ask to confirm".
