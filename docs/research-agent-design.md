# research-agent: design

A lean deep-research agent for Bebbi Bot (Kanton Basel-Stadt). It combines the techniques that worked
in other engines and avoids the ones that failed in our evaluation. It runs on on-prem Gemma-4-31B and
is driven by YAML presets. In production it sits behind an Open WebUI pipe as a small job service.

Sources for every design decision:
- [docs/research/patterns-iterative.md](research/patterns-iterative.md): Zürich deep-research, Local Deep Research, dzhng
- [docs/research/patterns-grounded-writing.md](research/patterns-grounded-writing.md): STORM, WebWeaver, VeriTrace, FS-Researcher
- [docs/research/patterns-orchestration.md](research/patterns-orchestration.md): open_deep_research, Onyx, NVIDIA, DeerFlow, GPT-Researcher
- our own analyses in [docs/analysis/](analysis/)

## Principles

1. **Code decides, the model fills in.**
   - Code drives the control flow, stopping, citation numbering, URLs, budgets and source policy.
   - The model plans, writes queries, extracts quotes and writes text.
   - There is no LLM supervisor loop: NVIDIA's re-sent context cost 860k tokens per run.
2. **Anchoring.** Every model call sees the short task (`task_core`) and its own sub-question. GPT-Researcher's recursion dropped the task, and its searches drifted.
3. **Evidence cards instead of paraphrase.** A finding counts only with a verbatim quote that code finds in the fetched page (VeriTrace, LDR). The writer cites card IDs, never URLs.
4. **Plan mirrors the task.** Report parts and `must_name` entities come from the task (NVIDIA's `required_components`). Code checks the finished report against them.
5. **Small outputs in line format, JSON only where it pays.** JSON is used only for the plan, reflection and extraction, and is loaded with repair. A ~30B model is more reliable that way than with tool-calling graphs.
6. **Presets are the only steering.** Sources, domains, MCP tools, query rules, report parts and budgets all live in YAML. There's no code change per topic.

## Control flow

```
            ┌───────────── chat turns (Open WebUI pipe, online, cheap) ─────────────┐
 task ──► 0 CLARIFY (fast, ≤2 questions, skipped for detailed tasks)
          1 PLAN (think, JSON): task_core, parts[{id,title,goal}], sub_questions[{id,part,text,route}],
                                must_name[], constraints[], language
            └─► user approves / edits ("approve" or free text → EDIT_PLAN, max 3 rounds)
            └──────────────────────────────────────────────────────────────────────────┘
                                   │ job queued (night window 20:00–05:00 or "now" for quick)
          2 RESEARCH, rounds r = 1..R (concurrency 3 per sub-question)
              a QUERIES (fast, line format "lang | intent | query | purpose"); code adds site:, gl/hl,
                dedupes against all previous queries; round 1 also searches task_core verbatim
              b MCP route (if the preset lists tools for the route): small tool loop, ≤3 calls,
                allowlisted tools only; results are cards with a citable URL
              c SEARCH via gateway (Serper); code drops avoid_domains, ranks prefer_domains first
              d TRIAGE (fast, index list) on titles and snippets → ≤k URLs not yet fetched
              e FETCH (Firecrawl) → focus passages (embeddings, ≤8k chars) → EXTRACT (fast, JSON):
                [{finding, quote}] or NOT_RELEVANT; code keeps a card only if its quote is in the page
            REFLECT, after each round:
              code: coverage per sub-question = distinct sources; stop if budget is spent,
                    all covered, or the round added < min_new cards
              model (fast, JSON): status per sub-question, missing identifiers (SG number,
                    Geschäftsnummer, dataset id, date), ≤4 new anchored follow-up questions
          3 WRITE, section by section (think): one call per part; input is only that part's cards
                (+ must_name hits); one [E12] per sentence, no citation on own analysis.
                Then a summary and "Offene Punkte / Grenzen" (from gaps and missing must_name)
          4 VERIFY (code + fast):
                drop unknown IDs; stacked [E1][E2] → keep the first; a cited number or name must
                occur in the card's quote, else the citation is removed; optional yes/no
                entailment check per citation; resolve [E12] → [n] + source list
                (title, URL, date fetched); report must_name coverage
 output: Markdown report, sources, evidence trail (JSON: queries, URLs, cards, decisions), tokens
```

## Data model

```python
Plan:  task_core: str; language: "de"|"en"; parts: [Part{id, title, goal}];
       sub_questions: [SubQ{id, part, text, route: "web"|"mcp:<name>"|"both"}];
       must_name: [str]; constraints: [str]
Card:  id "E12"; subq; url; title; fetched_at; quote (verbatim, ≤500 chars); finding (1 sentence);
       source_kind "web"|"mcp:<name>"; intent "primary"|"data"|"secondary"
Ledger: cards, fetched URLs, queries asked, per-subq coverage, gaps, token/search/fetch counters
```

## Preset schema (config/presets.yaml)

```yaml
<name>:
  description: ...                      # shown in Open WebUI as its own model ("Deep Research · Recht")
  language: de
  routes: {primary: [mcp:opencaselaw], data: [mcp:data-bs], secondary: [web]}
  mcp: {opencaselaw: [search_laws, get_law, ...]}   # allowlist per server
  prefer_domains: {primary: [...], data: [...]}     # site: filter for intent; ranked first in results
  avoid_domains: [...]                               # dropped after search
  query_rules: |                                     # appended to the query prompt
  report: {parts_hint: [...], citation_rules: |, closing_part: "Offene Punkte und Grenzen"}
budgets:
  quick:    {rounds: 1, max_subq: 4,  queries_per_subq: 2, fetch_per_subq: 3, max_follow_up: 0}
  standard: {rounds: 2, max_subq: 6,  queries_per_subq: 3, fetch_per_subq: 4, max_follow_up: 4}
  deep:     {rounds: 3, max_subq: 8,  queries_per_subq: 3, fetch_per_subq: 5, max_follow_up: 6}
```

## Where each technique comes from

| Technique | From | Our observation it addresses |
|---|---|---|
| task_core in every call, task searched verbatim | ZH, LDR | GPT-R drift (task 53 never names Norway, GIC) |
| Plan with parts, must_name and constraints, checked in code | NVIDIA (`required_components`) | NVIDIA's RACE lead comes from its structure |
| Clarify ≤2 questions, plan approval as chat turn | DeerFlow 1.x, Onyx, open_deep_research | Requirements F1, F2 |
| Swiss multilingual queries with intent; site: added by code | own rules (patterns-iterative T3) | GPT-R bad queries, weak primary sources, DE-W3 Lugano |
| Snippet triage before fetching | LDR cross-engine filter | Fewer, better fetches |
| Extraction with verbatim quote, checked in code | LDR `fetch_content`, VeriTrace | NVIDIA cited paraphrased notes (55% accuracy) |
| Reflection with coverage decided in code | ZH (considerations), own | NVIDIA follow-up depth too shallow; GPT-R depth without anchor |
| Section-wise writing on that part's cards only | FS-Researcher (+5.2 RACE), WebWeaver, VeriTrace | Reports too short, low comprehensiveness |
| One citation per sentence; code resolves IDs to URLs | Onyx `collapse_citations`, FS-Researcher | Stacked citations valid 46% vs 67% single |
| Number/name check against the quote, optional entailment | grounded-writing T7 | Task 51: "46.5%" cited for a page saying 44.3% |
| MCP results as citable cards with URL | german-set analysis | NVIDIA cited bare tool names |
| Presets for sources and budgets | LDR strategies, NVIDIA domain catalogs | Requirements F3, F4 |

Deliberately left out:
- STORM's simulated conversations and Co-STORM's mind map.
- LLM supervisor and think-tool loops.
- Recursive sub-researchers.
- Trimming the writer's context from the end.
- Citation numbers assigned by the LLM.
- Self-scored evidence quality.
- LangGraph.

## Integration into Open WebUI (v0.11.4, verified in source)

- **Pipe function** (one model per preset, seeded via the seeder). It runs the chat turns (clarify, plan, approve or edit), creates the job, and streams status through `__event_emitter__` (`status` and `citation` events).
- **Job service** (FastAPI, its own deployment, Postgres job table). It runs the research phases, with a night-window queue and per-user quota.
- **Delivering the report:** while the chat is open, the pipe polls and streams. For jobs that finish later, the service writes the report into the assistant message via `POST /api/v1/chats/{id}/messages/{message_id}`, which updates the message and emits it live to the open chat. That needs an admin service account: the endpoint allows the owner or an admin regardless of `ENABLE_ADMIN_CHAT_ACCESS`.
  - Alternative without an admin key: the report stays in the job service and the pipe fetches it on the user's next message.
- **API for n8n and other apps:** the same job service.

## Evaluation

The harness candidate `research-agent` calls the same core code directly, with no clarify step and the plan auto-approved, like the other candidates. The preset per task:
- DRB tasks use `web_survey`.
- German tasks map by category: Recht → `rechtsrecherche`, Grossrat → `grossrat`, Statistik → `statistik`, Web-Inhalte and Strategien → `verwaltung_web`.

Targets (standard depth):

| Measure | Target |
|---|---|
| Citation accuracy | ≥ 80% |
| RACE | ≥ `gpt-researcher@cfg` |
| German rubric | ≥ agent baseline |
| Tokens | 150–400k |
| Runtime | ≤ 15 min |
