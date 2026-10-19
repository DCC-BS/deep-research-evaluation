# Deep Research for Bebbi Bot (Open WebUI) — Requirements v2

Context: Open WebUI deployment on Kubernetes (GitOps), operated by a public administration.
On-prem LLMs via OpenAI-compatible API: a ~30B main model, a small task model, an embedding model and a reranker.
Existing stack: Serper web search, self-hosted Firecrawl (web loader), pgvector, S3, Redis, document conversion, observability collector, workflow automation.
Platform features: SSO with group sync, seeder image that ships tools, models, prompts and configs.
OWUI features in use: subagents enabled, automations disabled, web search admin-only toggle.
Cluster constraints: restricted pod security (non-root, drop all capabilities), no RWX storage, emptyDir size capped, all egress via an HTTP proxy.

Priority = MoSCoW. MUST items are gates: an option that fails one and cannot cheaply close it is out.
Scoring for SHOULD/COULD: 0 = absent, 1 = possible with custom code, 2 = supported with config/small glue, 3 = native and solid.

Benchmark judges: the official DeepResearch Bench judges (GPT-5.5 for RACE, GPT-5.4-mini for FACT) via OpenRouter, allowed for public benchmark data and our generated reports only.

Evaluation weights (from interview): Result quality 30 % · Integration & ops 25 % · Configurability & HITL 20 % · Efficiency 10 % · Governance 10 % · Maintenance 5 %.

## A — Architecture & integration (weight: Integration & ops)
| ID | Pri | Requirement | Metric / how to measure |
|---|---|---|---|
| A1 | MUST | Production runs solely on on-prem LLMs via OpenAI-compatible endpoints (no cloud LLM, incl. embeddings/rerank). Research-specialised open models are out of scope for v1 but may be reconsidered later. | Configurable base_url+model per role; egress capture during a run shows 0 calls to LLM SaaS. |
| A2 | MUST | Works reliably with open-weight ~30B models (Gemma-4-31B class): tool calling / structured output robust. | Run completion rate ≥ 90 % on 20 eval tasks with Gemma-4-31B; # of JSON/tool-call parse failures per run. Evidence of open-model support in docs/issues. |
| A3 | MUST | Uses our search + fetch stack (Serper and/or SearXNG, Firecrawl) or pluggable equivalents; no new mandatory SaaS. | Backend pluggability: native / adapter needed / impossible. Count of new external services required. |
| A4 | MUST | Sources: public web, OWUI knowledge bases, files uploaded in chat. | Per source type: native / via adapter / no. |
| A5 | MUST | Sources through MCP servers: opencaselaw (`mcp.opencaselaw.ch`: federal and cantonal law, court decisions, Botschaften) and data.bs.ch (`mcp.data.bs.ch`: open data portal incl. Grosser Rat documents and proceedings, Statistisches Amt datasets). No SharePoint in v1. Users can also add a knowledge base or links manually. | Streamable-HTTP MCP client; per-server tool allowlist (opencaselaw exposes 45 tools); both servers reachable from the cluster through the proxy. |
| A6 | MUST | Entry point 1: selectable "Deep Research" model in the OWUI chat (pipe or OpenAI-compatible model endpoint), streaming status. | Works in model picker; status updates visible; person-days to integrate. |
| A7 | MUST | Entry point 2: async job. The user can leave, and the report arrives as a message in the OWUI chat. | Job survives browser close and pod restart; report posted to the originating chat. |
| A8 | SHOULD | Entry point 3: API for n8n / other KI apps. | REST/OpenAI/MCP API exists, documented, authenticated. |
| A9 | MUST | OWUI change footprint limited to extension points (functions, tools, MCP/OpenAPI tool servers) or small fork patches. | LOC of fork patch; expected merge conflicts per OWUI upgrade (0/low/high). |
| A10 | MUST | K8s fit: OCI image, non-root, restricted PSS, no RWX, no emptyDir > 250Mi, works behind HTTP proxy, state in Postgres/Redis/S3 (or stateless). | Checklist pass count (6 items). |
| A11 | SHOULD | Robustness & scale: run state persisted (survives pod restart), N parallel runs, horizontal scaling. | Kill pod mid-run → resume/clean fail; max concurrent runs tested. |
| A12 | SHOULD | Observability: JSON logs, OTel traces/metrics, token usage per run. | Present y/n per item. |

## F — Research flow, HITL & configuration (weight: Configurability & HITL)
| ID | Pri | Requirement | Metric / how to measure |
|---|---|---|---|
| F1 | MUST | Clarifying questions before research starts. | Native y/n; can be skipped by user. |
| F2 | MUST | User reviews and can edit/approve the research plan before execution. | Native y/n; edit granularity (approve only / edit sub-questions). |
| F3 | MUST | Configurable depth per run (breadth, depth, max sources, time/token budget). | # of exposed knobs; settable per run by end user. |
| F4 | SHOULD | Domain presets (e.g. Rechtsrecherche, Statistik, Medienspiegel) with own prompts, source lists, models — defined as files via GitOps. | Preset = config file, no code change; # of tunable prompt slots. |
| F5 | MUST | Platform team configures everything via GitOps (env/YAML/seeder), no mandatory click-ops. | % of settings settable declaratively. |
| F6 | MUST | Output German (Swiss conventions, no ß); searches in DE/EN/FR/IT. | Output language controllable; multilingual query generation y/n. |
| F7 | MUST | Off-peak execution: there is not enough GPU capacity during office hours, so deep runs are queued and run in a configurable window (20:00–05:00 CET). Optional quick runs may run immediately. | Execution window configurable via GitOps; queue survives restarts; GPU load during office hours unchanged (measured via vLLM metrics). |
| F8 | SHOULD | Progress transparency during run (current step, sources found). | Live status events y/n. |

## O — Output
| ID | Pri | Requirement | Metric / how to measure |
|---|---|---|---|
| O1 | MUST | Structured Markdown report with inline citations. | Citation coverage: % of factual sentences with a citation (target ≥ 90 %). |
| O2 | SHOULD | Download as DOCX/PDF. | Native / via OWUI export / custom. |
| O3 | MUST | Evidence trail: source list, queries issued, pages visited, claim → snippet mapping. | Items present (of 4). |

## Q — Result quality (weight: Result quality) — evaluated via public benchmarks
| ID | Pri | Requirement | Metric / how to measure |
|---|---|---|---|
| Q1 | MUST | Demonstrated report quality on a public deep-research benchmark. | DeepResearch Bench RACE score (report quality); DeepResearchGym; published leaderboards. Note model used. |
| Q2 | MUST | Citation faithfulness. | DeepResearch Bench FACT: citation accuracy & effective citations per task. |
| Q3 | SHOULD | Agentic search capability. | BrowseComp / BrowseComp-Plus / GAIA / xbench-DeepSearch scores where published. |
| Q4 | SHOULD | Quality holds with open-weight models (not only GPT/Claude/Gemini). | Published results with open models; else our reproduction on 30-task DRB subset with Gemma-4-31B. |
| Q5 | MUST | Quality on German administrative research: law, Grossrat decisions, web content, strategies. | German test set (13 tasks) scored with a rubric by the LLM judge plus domain-expert spot checks. |

## E — Efficiency (weight: Efficiency)
| ID | Pri | Requirement | Metric / how to measure |
|---|---|---|---|
| E1 | MUST | Standard-depth run consumes 200k–1M tokens. | Measured input+output tokens per run (median, p90). |
| E2 | SHOULD | Hard caps per run (tokens, time, # of LLM calls). | Native y/n. |
| E3 | MUST | Per-role models with a per-role thinking switch: Gemma-4-31B with thinking for planning, research and writing; Gemma without thinking or Qwen3.5-4B for decisions, routing and summaries. | # of separately configurable model roles; thinking toggle per role (chat_template_kwargs). |
| E4 | SHOULD | Wall-clock runtime fits depth level (quick 2–5 min … deep ≤ hours). | Median runtime per depth level. |

## G — Governance (weight: Governance)
| ID | Pri | Requirement | Metric / how to measure |
|---|---|---|---|
| G1 | COULD | Access restricted to SSO groups (low priority). | Via OWUI model access control or own authZ; y/n. |
| G2 | MUST | Per-user quotas/budgets (runs/day or tokens/day). | Enforced limit y/n; where enforced. |
| G3 | SHOULD | Respect usage policy: warn/guard against personal data in queries sent to external search. | Hook for PII check / disclaimer y/n. |

## M — Sourcing & maintenance (weight: Maintenance)
| ID | Pri | Requirement | Metric / how to measure |
|---|---|---|---|
| M1 | MUST | Permissive OSS licence (MIT/Apache-2.0/BSD) or own build. AGPL/proprietary = only as reference. | Licence. |
| M2 | SHOULD | Actively maintained. | Commits last 90 d; last release date; # contributors (12 mo); open/closed issue ratio; GitHub stars as weak signal. |
| M3 | SHOULD | Forkable / small enough to own if upstream dies. | Core LOC; # of heavy dependencies. |
