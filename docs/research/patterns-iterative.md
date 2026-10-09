# Reusable patterns from the iterative research engines (ZH deep-research, Local Deep Research, dzhng)

Scope: techniques worth lifting into our own lean research agent (plan -> bounded research rounds with reflection -> writer that cites only fetched pages; YAML presets). Code was read, nothing was run and no LLM was called.

Evidence tags: **[V]** verified in code (file/function given), **[C]** claim by the project (README/docstring, not reproduced by us), **[O]** our own observation from `docs/analysis/*.md`, **[E]** my estimate, **[S]** my synthesis (not found in any of the three codebases; a recommendation).

Clone paths (under the scratchpad `repos/` dir): `deep-research` (ZH, HEAD 6556d51), `local-deep-research` (LDR, HEAD ff14cf1, 2026-10-06), `dzhng-deep-research`. Short names below: ZH = `deep-research/02_app/_core/*`, LDR = `local-deep-research/src/local_deep_research/*`, DZ = `dzhng-deep-research/src/*`.

## 0. Findings in five lines

1. **Anchoring is the single most important thing the good engines do and GPT-R dropped.** ZH and LDR put the full original query into every query-generation prompt and also search it verbatim. DZ does lose the original query in its recursion (`nextQuery` = research goal + follow-ups), but it feeds all accumulated `learnings` back into the query generator and does one SERP hop per branch. GPT-R's port removed both protections (see section 4).
2. **The best pattern for citation binding is LDR's focused fetch**: `fetch_content(url, focus)` returns only verbatim quotes (<=1500 chars) or `NOT RELEVANT`, and every result gets a stable `[N]` index at tool-return time. ZH's "relevance gate, then full-document analysis with quotes" is the best pattern for primary documents. DZ's learnings carry no source, so they cannot be bound to claims.
3. **Relevance filtering before reading** comes in two cheap forms: LDR's one-call index-list filter over title+snippet (regex-parsed, fallback to top 10), and ZH's per-chunk `{reasoning, relevance}` gate. For web search the LDR form is right; the ZH form only pays off on a corpus where chunks are the retrieval unit.
4. **None of the three handle multilingual queries or primary-source preference.** ZH is monolingual German on a closed corpus, LDR passes one `language` to SearXNG, DZ's system prompt even says "the source is irrelevant". Both must come from our preset layer (section 3.4, 3.5).
5. **Local-model evidence** (LDR README [C]): `langgraph-agent` strategy with Serper, models in Ollama: Qwen3.6-27B 95.7% SimpleQA (287/300) and 77% xbench-DeepSearch (n=100); Qwen3.5-9B 91.2% / 59%; gpt-oss-20B 85.4% SimpleQA. That is short-answer retrieval, not report quality, and graded by an LLM, so it supports "a bounded tool-calling agent with a small tool surface works with ~30B open models", which matches our own finding that the simple agent is cheap and decent [O].

## 1. Summary table

Priority: P0 = build into v1, P1 = build once v1 runs, P2 = optional. Gemma fit = how well it should work with Gemma-4-31B (thinking on/off), given our vLLM setup.

| # | Technique | Source (file / function) | Phase | Value | Cost (tokens / latency) | Gemma fit | Priority |
|---|---|---|---|---|---|---|---|
| T1 | Anchor every LLM call to the original task + current sub-question; search original verbatim in round 1 | ZH `workflow.py` (`search_queries.extend([user_query])`), LDR `source_based_strategy.py` (`search_original_query`), DZ `deepResearch` (learnings fed back) | all | Very high: prevents the GPT-R drift [O] | ~0 (prompt text, +300-800 tokens per call) | High | P0 |
| T2 | Query-generation prompt rules (aspect-per-query, no near-duplicates, previous-queries list, reflection "considerations", date, per-query purpose) | ZH `prompts.CREATE_QUERIES(+_ADDITIONAL)`, LDR `StandardQuestionGenerator`, DZ `generateSerpQueries.researchGoal` | research rounds | High | 1 small call per round (~1.5k in, 0.3k out) | High (line format) / High (JSON schema) | P0 |
| T3 | Swiss multilingual + jurisdiction-aware queries with `lang`, `intent`, `site` fields | [S]; none of the three do it | research rounds | High for DE-W3-type tasks (Italian source missing) [O] | +30-60% queries | Medium-high (Gemma translates well, needs rules) | P0 |
| T4 | Snippet triage: one batched call ranks title+snippet+domain, returns indices; deterministic domain score first | LDR `cross_engine_filter.py`, `web_search_engines/relevance_filter.py` | research rounds (before fetch) | High: avoids App-Store / blog sources [O] | ~2.5k in, <100 out per 30 results | High (plain text list) | P0 |
| T5 | Focused fetch: `fetch(url, focus)` -> verbatim quotes only or `NOT RELEVANT`, with role framing, empty-page guards | LDR `tools/fetch/prompts.py`, `tools/fetch/__init__.py` (`fetch_content`) | research rounds | Very high: gives claim-level evidence cards | 3-12k in, ~0.4k out per page | High (extractive task) | P0 |
| T6 | Evidence registry with stable `[N]` indices assigned at tool-return time; sources list built in code | LDR `SearchResultsCollector`, `_format_results`, `StandardCitationHandler` | all, writer | Very high: fixes "citation binding" (NVIDIA weakness) | ~0 | High | P0 |
| T7 | Relevance gate, then full-document analysis for primary documents | ZH `check_relevance`, `analyze_documents`, `ANALYZE_DOCUMENT` | research rounds | High for statutes, Grossrat docs, judgments | Gate: 0.9k in per chunk. Analysis: doc length (3-15k) per doc | High | P1 |
| T8 | Gap reflection loop (feeds `considerations` into next query generation) | ZH `REFLECT_TASK`, `reflect_task_status`; LDR `StandardQuestionGenerator` ("Critically reflect...") | after each round | High if made structured | 1 call per round; ZH feeds all analyses (10-40k) | Medium: boolean `finished` is unreliable, use coverage table | P0 |
| T9 | Learnings extraction: <=N dense facts with entities/numbers/dates + follow-up questions per SERP | DZ `processSerpResult` | research rounds | Medium (we get the same from T5 + T8) | 1 call per query, up to 25k chars per page | High | P1 |
| T10 | Breadth/depth as a budget: breadth halves per level, depth bounded, concurrency limit | DZ `deepResearch` (`newBreadth = ceil(breadth/2)`) | budget control | Medium | n/a | High | P1 |
| T11 | Plan = report structure with purpose per section (`STRUCTURE ... END_STRUCTURE`, `name \| purpose`); sibling-aware section prompts | LDR `report_generator._determine_report_structure`, `_research_and_generate_sections` | plan, writer | High (coverage of named items) | 1 call; section loop is costly in LDR, so we do only the writer part per section | High | P0 |
| T12 | Clarifying questions: <=3, "fewer if the query is clear"; answers merged into one brief | DZ `feedback.ts: generateFeedback`, `run.ts` (`combinedQuery`) | plan | Medium | 1 small call | High | P1 |
| T13 | Lead agent + `research_subtopic` parallel subagents sharing one registry; per-subagent caps | LDR `langgraph_agent_strategy.py` (`_make_research_subtopic_tool`, `MAX_SUBTOPICS=5`, `MAX_SUBAGENT_WORKERS=4`) | research rounds (alt. architecture) | Medium: breadth without drift if the subtopics are fixed by the plan | Subagent overhead per topic | Medium | P2 |
| T14 | Writer contract: honest-gap sentence, no own advice, exact identifiers, fixed 3-part structure, start without preamble | ZH `RESEARCH_WRITER` | writer | High (limits criterion lost 2.0 vs 0.69 [O]) | 0 | High | P0 |
| T15 | Novelty/dedupe state across rounds (seen chunk ids, doc ids, previous queries) | ZH `workflow.py` (`previous_chunk_ids`, `previous_doc_ids`), LDR `questions_by_iteration` | rounds | Medium: GPT-R repeated one query 3x [O] | ~0 | High | P0 |
| T16 | Per-role model tiers | ZH `utils.get_model_and_workflow_config` | all | Medium | -30-50% latency [E] | High (`gemma-fast` for T2/T4, `gemma-think` for plan/reflect/write) | P0 |
| T17 | Refuse-to-synthesize-without-sources and empty-content guards | LDR `_no_sources_response`, fetch Guard 1/2 | writer, fetch | Medium (no fabricated sources) | 0 | High | P0 |
| T18 | Mechanical fact-consistency pass across sources | LDR `StandardCitationHandler.analyze_followup` (`is_fact_checking_enabled`) | pre-writer | Low-medium | +1 call, +5-15k | Medium | P2 |
| T19 | DOCX export with AI disclaimer | ZH `utils.create_docx_from_markdown` | delivery | Medium (administrative users) | 0 | n/a | P2 |

## 2. What the three engines do (short)

**ZH deep-research** [V]: query generation (`create_queries`, one structured call, temp 1.0, up to 20 queries; original query always appended) -> hybrid search in Weaviate -> per-chunk relevance gate (structured `{reasoning, relevance}`, parallel) -> chunks mapped to parent documents -> one `ANALYZE_DOCUMENT` call per full document -> optional reflection `{reflection, finished}` (max 3 iterations; reflection text becomes `considerations` for the next query generation) -> one final report call over the per-document analyses (document text is not passed again). No plan, no clarification, no web. 5 roles map to 3 model tiers.

**LDR** [V]: many strategies. `source-based` (iteration loop: question generation -> parallel search -> after all iterations a cross-engine LLM filter -> one cited synthesis). `focused-iteration` (8 iterations x 5 questions, claims 96.51% SimpleQA with GPT-4.1 mini [C]). `langgraph-agent` (tool-calling lead agent with `web_search`, `fetch_content(url, focus)`, `research_subtopic`, specialised engines; this is the strategy behind the local-model results [C]). Report mode: `_determine_report_structure` then research+write per subsection with sibling and previous-section context.

**DZ** [V]: 540 lines of TypeScript. `generateFeedback` (<=3 clarifying questions) -> `deepResearch(query, breadth, depth)`: `generateSerpQueries` (with `researchGoal` per query, previous `learnings` in the prompt) -> Firecrawl search with scraped markdown (limit 5) -> `processSerpResult` (<=3 learnings + follow-up questions) -> if depth>1 recurse per query with `breadth=ceil(breadth/2)` -> `writeFinalReport` (all learnings, sources appended as a URL list).

## 3. Technique details

### 3.1 T1 Anchoring to the original task (and why it matters)

**What**: every prompt that decides what to search next contains the original task, not only the derived sub-question. Round 1 also searches the task (compressed) verbatim.

**Where**: ZH `workflow.py:run_iteration` appends `user_query` to the generated queries and passes it as the *user message* of `create_queries` on every iteration; the reflection prompt and relevance gate also contain it. LDR `StandardQuestionGenerator.generate_questions` puts `Query: {query}` into every iteration prompt, and `source_based_strategy.py` searches the original query verbatim in iteration 1 (skipped when it is longer than `app.max_user_query_length`=300 chars, because a long prompt is a poor search string). LDR also forwards the overall question into the fetch extractor (T5) and into every report-section research prompt ("in a report about '{query}'").

**Evidence**: LDR's comment explains why: an ambiguous query ("local deep research") was misread as Austin heat islands; the verbatim search saves it [V, docstring]. Our GPT-R analysis found the mirror image: the recursion passes only goal + follow-ups, searches wander into EU taxonomy / New Mexico, and the same query was issued 3x [O].

**Cost/robustness**: free. Works with any model.

**Sketch** (all phases): keep one immutable `Brief` object and render it into every prompt.

```
brief = {task, subquestions[], parts[], source_policy, today}
def prompt_header(brief, sq):   # reused by query-gen, triage, extract, reflect
    return f"AUFGABE: {brief.task_short}\nTEILFRAGE: {sq.text}\nBERICHTSTEIL: {sq.part}"
```
Rule: no LLM call may see only "previous goal + follow-up"; the three lines above are always present. Round 1 also runs `task_core` (<=300 chars, produced by the planner) as a literal query.

### 3.2 T2 Query-generation prompt rules

**ZH prompt gist** (`CREATE_QUERIES`, German, `{query_count}` queries): "Du bist Rechercheassistent ... formuliere N präzise und vielfältige Suchanfragen". Rules: (a) keywords, broad synonyms *or* full sentences (matches a hybrid semantic+lexical engine); (b) cover all relevant aspects; (c) for broad topics one query per sub-aspect; (d) each query focuses on **one** aspect of the original question; (e) "generiere keine mehrfach ähnlichen Anfragen - eine reicht aus"; (f) **omit terms the corpus already implies** ("Kantonsrat Zürich" is dropped from queries). Iteration 2+ appends `CREATE_QUERIES_ADDITIONAL`: the list of previous queries ("generiere diese nicht erneut") and the reflection `considerations`.

**LDR prompt gist** (`StandardQuestionGenerator`): first iteration: "First, identify if your knowledge is outdated (high chance). Today: {date}. Generate N high-quality internet search questions to exactly answer: {query}", output as `Q: ...` lines. Later iterations: "Critically reflect current knowledge (e.g., timeliness), what N high-quality internet search questions remain unanswered to exactly answer the query? Query / Today / Past questions / Knowledge". Parsed by `startswith("Q:")`, no JSON. BrowseComp variant extracts entities (TEMPORAL / NUMERICAL / NAMES / LOCATIONS / DESCRIPTORS) and asks for "combine 2-3 entities not yet tried together"; useful for identifier-heavy tasks (Geschäftsnummer + year + Departement).

**DZ prompt gist** (`generateSerpQueries`): "Return a maximum of N queries, but feel free to return less if the original prompt is clear. Make sure each query is unique and not similar to each other"; schema gives each query a `researchGoal` ("first the goal of this query, then how to advance the research once results are found, mention additional research directions"). Previous `learnings` are appended to produce "more specific queries".

**Evidence**: ZH/LDR/DZ publish no ablation of the wording. What is supported: the dedupe + previous-list rule (our GPT-R run repeated a query 3x [O]); `researchGoal` is used by DZ for the next level (and dropped for query anchoring in the GPT-R port, see section 4). Everything else is plausible practice, not measured.

**Cost**: 1 small call per round, ~1.5k in / 0.3k out. Gemma: use `gemma-fast`; thinking off is fine. LDR's `Q:` line format is the most robust output for a ~30B model; DZ/ZH rely on JSON schema (vLLM guided decoding can enforce it, but ZH's `strict` schema path was never exercised on open models [O: eval-zh]).

**Sketch** (research round, input: brief + sub-question + prior queries + gaps; output: list of `{q, lang, intent, site?, purpose}`) - see the combined prompt in 3.3 (T3), which extends these rules.

### 3.3 T3 Swiss multilingual, jurisdiction-aware queries [S]

None of the three engines do this. Evidence for the need: DE-W3 lost criterion 8 because there was no Italian source for Lugano [O]; the agent cited `SR 153.260` where Basel-Stadt uses SG numbers [O]; nobody cited a BGE number [O].

**Rules to put in the query prompt** (German prompt, English gist):
1. One query = one aspect = one language. Tag each query with `lang` in `{de, fr, it, en}`.
2. Default `de`. Add `fr` / `it` queries only when the sub-question concerns another language region (a Romandie/Ticino canton or city, a federal body's French/Italian wording) or a term that exists officially only in that language. Add `en` only for international comparisons.
3. Use the *official term in that language* (e.g. "Abfallgebühren" / "taxe au sac" / "tassa sul sacco"), not a translation of the German query.
4. Keep Serper queries short: 3-8 words, no full sentences, no quotes unless an identifier (Geschäftsnummer `24.5123.01`, `SG 153.260`, `BGE 147 I 1`). Sentences are fine for MCP tools.
5. Name the jurisdiction in the query ("Basel-Stadt", "Kanton Luzern", "Bund") when the task does; never add it when the preset's `site:` filter already carries it (ZH rule f).
6. For each query set `intent`: `primary` (law, Grossrat, official statistics, Regierungsrat), `data` (dataset), `secondary` (media, NGO, research). The code, not the model, expands `primary` into `site:` filters from the preset.
7. Do not repeat a query in `previous_queries` (exact or near-duplicate).

**Code side** (not the model): Serper `gl=ch`, `hl` from `lang`; `site:` lists from the preset's `preferred_domains` per intent; a blocklist applied after search (the gateway already has one); normalize and dedupe URLs.

**Gemma robustness**: translation and term choice should be fine for a 31B model; the risk is over-generating languages, so cap with `max_languages_per_subquestion: 2` in the preset and apply the cap in code.

**Prompt skeleton**
```
System: Du erzeugst Suchanfragen für Serper. Heute ist {today}.
AUFGABE: {task_short}
TEILFRAGE: {sq.text} (Berichtsteil: {sq.part})
BEREITS GESUCHT: {previous_queries}
LÜCKEN AUS DER LETZTEN RUNDE: {gaps}
Regeln: (siehe oben, 1-7)
Ausgabe, je Zeile: lang | intent | query | Zweck (max. 12 Wörter)
```
Line format with `|` is parsed with a regex; falls back to treating the whole line as a German `secondary` query.

### 3.4 T4 Snippet triage before fetching

**Where**: LDR `cross_engine_filter.py:CrossEngineFilter.filter_results` and `web_search_engines/relevance_filter.py` (`_RELEVANCE_PROMPT_TEMPLATE`, `_invoke_text`).

**What it does**: shows up to `cross_engine_max_context_items` (30) results as `[i] Engine | Title\nSnippet (<=200 chars)`, asks for "ONLY the 0-based indices of relevant results as a comma-separated list". Key prompt sentences: "Direct topic match matters more than keyword match - results that just mention the query terms usually don't help." and a role frame ("This is a relevance-filtering step. Kept results move forward and may be used in the final answer"). Parsing is a regex for integers; invalid or duplicate indices are skipped (`_valid_unique_indices`); if the filter returns nothing it falls back to the top 10 originals; if the LLM output is unparseable it returns the originals. No filter is run for <=10 results.

**Evidence**: no ablation published. Its value for us is indirect: the German-set failures were source-quality failures (App Store, Instagram, forasoft blog, Saudi university PDF) [O], and criterion 3 (primary sources first) is the second-largest gap.

**Cost**: ~30 x 60 = 2.5k tokens in, <100 out per batch. Latency a few seconds with `gemma-fast`.

**Gemma fit**: high; a comma list of ints needs no structured output.

**Our improvement [S]**: add the domain and `intent` to each line, and run a deterministic pre-score first so the model only breaks ties:
```
score(r) = +3 if domain in preset.preferred (by intent) else
           -9 if domain in preset.avoided else 0   # drop
           +1 if file type pdf and domain tier 1
keep top 30 by score, then LLM picks <=8 indices for "will I cite this?"
```
Prompt addition: "Wähle nur Treffer, die als Quelle für die TEILFRAGE zitierbar wären. Primärquellen (Gesetz, Protokoll, Amtsstatistik) vor Medien. Maximal 8."
Output: indices; code merges with the URL registry (T6) and skips URLs already fetched (T15).

### 3.5 T5 Focused fetch with verbatim extraction

**Where**: LDR `advanced_search_system/tools/fetch/prompts.py` (`SUMMARY_FOCUS_QUERY_PROMPT`) and `tools/fetch/__init__.py:fetch_content` (mode `summary_focus_query`).

**What it does**: the agent calls `fetch_content(url, focus)`; `focus` must be "the specific question or claim you want answered". A separate LLM call receives: overall research question, focus, title, URL, page content, and returns **only verbatim quotes**: "one quote per line, no bullets"; "copy numbers, names, dates, proper nouns exactly"; omit nav, banners, bios; "if nothing helps reply exactly NOT RELEVANT"; no intro/conclusion/commentary; max 1500 characters, "fewer precise quotes beat many borderline ones". The docstring states why the role frame exists: "small local models (qwen3, gpt-oss) calibrate measurably better when told what's downstream of their output" [C]. Guards: empty page content returns `NOT RELEVANT (no extractable content ...)` without an LLM call; an empty summary is also `NOT RELEVANT` and the URL is **not** registered, so the agent can retry it with another focus.

**Why it matters for us**: it turns each fetched page into an *evidence card* (url, title, date, quotes, focus) with a hard length cap. The writer never sees raw pages, so context stays small (this is the fix for GPT-R's 32-60k-token writer prompt [O]) and every claim can be tied to a quote that exists on a fetched page (our FACT-style verification is then a string match).

**Cost**: 3-12k tokens in per page (page text up to the cap), ~0.4k out. For 6 pages per round x 3 rounds = 18 pages, 60-220k tokens [E]. To cut it: pre-select passages with the local embedding model before the LLM call, our own FACT focus step (`eval/drb_focus.py`) found the 16k most relevant characters beat page heads (38.1 vs 31.6 on the same report) [O]. Use `gemma-fast`.

**Gemma fit**: high, it is extractive and has no structured output. Add a code-side check: every returned line must be a substring (after whitespace normalization) of the page; drop lines that are not. This catches paraphrases and hallucinated quotes cheaply. [S]

**Sketch**
```
def fetch_and_extract(url, focus, brief):
    page = firecrawl.scrape(url)            # markdown
    if not page.text.strip(): return NOT_RELEVANT("empty")
    passages = select_passages(page.text, query=focus, budget_tokens=6000)  # embeddings
    quotes = llm_fast(EXTRACT_PROMPT.format(task=brief.task_short, focus=focus, **page, content=passages))
    quotes = [q for q in lines(quotes) if norm(q) in norm(page.text)]
    if not quotes or quotes == ["NOT RELEVANT"]: return NOT_RELEVANT
    return registry.add_card(url=url, title=page.title, date=page.date, quotes=quotes, sq=focus)
```
Prompt (German adaptation): "Du bist ein Extraktionsschritt in einem Recherche-Agenten. Dein Output geht an den Autor, der die Quelle zitiert. Gib NUR wörtliche Zitate aus der Seite aus. Zahlen, Namen, Daten exakt kopieren. Nichts zusammenfassen. Schreib ausserdem Datum/Stand der Seite in die erste Zeile (`STAND: ...` oder `STAND: unbekannt`). Wenn nichts hilft: genau `NICHT RELEVANT`. Maximal 1500 Zeichen." The `STAND` line addresses criterion 4 (date named; agent 0.69 [O]).

### 3.6 T6 Evidence registry with stable citation indices

**Where**: LDR `langgraph_agent_strategy.py`: `SearchResultsCollector` (dedupe by URL/snippet key, assigns the index, offsets across calls), `_format_results` (`[N] Title (URL)\nsnippet` returned from the tool so the model sees the number with the evidence), `StandardCitationHandler.analyze_followup` ("Include citations using numbers in square brackets ... Citations must only appear inline ... Do NOT create a bibliography ... Never make up sources. Never write or create urls"); the Sources section is then rendered from `all_links_of_system`, not from LLM text. In report mode, indices continue across sections via `nr_of_links`.

**Limits [V]**: LDR does not verify that a cited sentence is supported by the source; it relies on the prompt. ZH has free-form links chosen by the LLM; DZ appends all visited URLs unbound (`## Sources` list). So the "one source per claim" rule has to be enforced by us.

**Sketch** (writer and verifier)
```
cards = registry.cards()            # id, url, title, date, quotes[]
writer_input = for each part: cards for the part (ids + quotes), nothing else
rules: every sentence with a fact/number ends with [id]; only ids given; max 1 id per claim
post:  ids_in_text subset of registry ids else delete the sentence or retry once
       sentence with digits but no [id] -> flag; "Quellen" section rendered by code from used ids
       (optional) verify: quote text appears in card; claim numbers appear in the cited quotes
MCP results: also registered as cards with a stable URL (lexfind / gesetzessammlung.bs.ch /
       data.bs.ch/explore/dataset/<id>) because bare tool names scored 0 on criterion 2 [O]
```
**Cost** ~0. **Gemma**: id citations are the format models handle best.

### 3.7 T7 Relevance gate, then full-document analysis (for primary documents)

**Where**: ZH `llm_processing.check_relevance` (+ `CHECK_RELEVANCE` prompt), `analyze_documents` (+ `ANALYZE_DOCUMENT`).

**Gate prompt gist**: "Es handelt sich nur um einen Ausschnitt ... Der Ausschnitt muss die Frage nicht vollständig beantworten ... Beurteile ausschliesslich, ob er potenziell hilfreich ist." Output `{reasoning: <Stichworte>, relevance: True|False}`. The chunk-level, *lenient* standard ("potentially helpful") is the point: recall at the gate, precision at the analysis. Relevant chunks are mapped to their parent document, deduplicated, and previously analysed docs are skipped.

**Analysis prompt gist**: expert question + whole document (title, date, link, text); "Konsolidiere die wichtigsten Informationen", "zitiere relevante Textstellen und gib Gesetzesstellen an", "beziehe nur Informationen aus dem Dokument ein, erfinde nichts". The per-document analysis (not the raw doc) goes to the writer.

**Cost [E, from eval-zh]**: gate ~0.85k in + 0.1k out per chunk, 60-200 chunks per round; analysis 100-800k tokens for long documents. Too expensive as a default for web pages; fine as a targeted tool for a handful of primary documents (a statute, a Grossrat Geschäft, a judgment).

**Gemma fit**: the gate uses strict JSON schema in ZH (unproven on open models). Replace by a one-line answer (`ja`/`nein` + 5-word reason) or batch via T4. Long documents: 128k context allows one statute or judgment per call, but keep to <40k tokens per call to keep latency sane.

**Sketch** (as an optional tool in the round): `read_document(url_or_mcp_id, questions[])` -> same output type as T5 but with a larger cap (e.g. 3000 chars of quotes + 5-line summary). Use T5 first; escalate to T7 only when the preset marks the source class as `read_full: true` (law, Grossratsgeschäft, Gerichtsentscheid).

### 3.8 T8 Reflection loop (what to copy, what to change)

**ZH** [V]: `REFLECT_TASK` gets the question and *all* per-document analyses so far, returns `{reflection, finished}`; if not finished, `reflection` goes into `previous_considerations` and into the next `CREATE_QUERIES_ADDITIONAL`. Max 3 iterations; skipped in "fast mode"; the check is not run on the last iteration. **LDR** [V]: no explicit judge, the question generator is asked what "remains unanswered", with the `Past questions` list and a knowledge summary. **DZ** [V]: no judge; `followUpQuestions` per SERP drive the next level, bounded by depth.

**Weaknesses**: a single boolean from the same model that wrote the analysis tends to say `finished=True`; ZH sends all analyses (10-40k tokens) every time; ZH's termination is only in the LLM's hands (plus the iteration cap).

**Change [S]**: make the gap check structured per sub-question and let code decide:
```
reflect(brief, cards_by_subquestion) -> for each sq:
    status: covered | partial | missing
    evidence: list of card ids supporting it (must exist)
    missing: what exact fact/identifier is missing (e.g. "SG-Nummer", "Stand", "Datensatz-ID")
    next_queries: 0-2 queries with lang/intent (same format as T3)
code: stop if all required sq are covered OR budget used OR two rounds without new cards
      else next round targets only partial/missing sq (T10)
```
Feed it *card headlines* (id, title, domain, first quote, 200 chars), not full quotes, to keep it at 3-6k tokens. Add the "identifier check" from our own list: law -> SG number and Stand; Grossrat -> Geschäftsnummer; statistics -> dataset id and Stand; each is a checklist item in the preset (`report.required_fields`).
**Cost**: 1 `gemma-think` call per round, ~4-8k in, ~0.8k out. **Gemma**: use JSON schema for this one (small, enums), thinking on.

### 3.9 T9 Learnings extraction and follow-up questions (DZ)

**Where**: DZ `processSerpResult`. Gist: "generate a list of learnings from the contents. Return a maximum of N learnings, fewer if clear ... unique ... concise and to the point, as detailed and information dense as possible. Make sure to include any entities like people, places, companies, products ... as well as any exact metrics, numbers, or dates. The learnings will be used to research the topic further." Also returns `followUpQuestions`. Page contents are trimmed to 25k tokens each.

**Assessment**: the "entities + exact numbers + dates" wording is a good fragment to reuse in T5/T8. The structure itself is weaker than T5: learnings are paraphrases without source (URLs live in a separate `visitedUrls` list), so they cannot back a claim. GPT-R tried to repair this with `[Source: url]` per learning, still a model-chosen mapping [V, `gpt_researcher/skills/deep_research.py`]. We use evidence cards instead and keep DZ's entity/number instruction inside the reflection "missing" field.

### 3.10 T10 Breadth/depth budgets

DZ: `numQueries=breadth` at level 1, `ceil(breadth/2)` at each deeper level, `depth` levels, concurrency via `p-limit` (default 2 for Firecrawl). It is a clean way to express a budget but a bad way to select *what* to research (see section 4). For us: keep the *budget* idea, drop the *recursion*:
```
preset.budget = {rounds: 3, queries_per_round: 6, fetch_per_round: 8, max_cards: 40,
                 max_tokens: 400k, max_minutes: 15}
round 1: breadth = queries_per_round spread over sub-questions (>=1 each)
round 2+: breadth halves unless a required sub-question is still `missing`
stop on first of: all covered | budget | two rounds with no new cards
```
Spread by sub-question, not by branch, which keeps each query tied to a named report part.

### 3.11 T11 Plan = structure with purposes

**LDR** `_determine_report_structure`: asks for a TOC in a fixed text format:
```
STRUCTURE
1. [Section Name]
   - [Subsection] | [purpose]
END_STRUCTURE
```
"Make the structure specific to the content, not generic ... DO NOT include sections about sources, citations, references, or methodology"; a post-filter removes a trailing source-like section. Parsing is line-based (no JSON). Then `_research_and_generate_sections` writes each subsection with: the section's purpose, names of all other sections, names/purposes of sibling subsections, and "the last 3 sections' text (max 4000 chars) with a DO NOT REPEAT instruction", plus "Focus ONLY on information specific to your subsection's purpose".

**What to take**: (a) the `name | purpose` pair, a purpose per part lets the reflection and writer check coverage; (b) sibling-aware, non-repeating section prompts; (c) the line format. **What not to take**: LDR re-runs a full search per subsection (many times the token cost). We research once against sub-questions and write per part from the card set.

**Our plan output [S]** (user can approve):
```
subquestions: [{id, text, part, intent: law|statistics|grossrat|web|mixed, languages, mcp_first: bool}]
parts: [{name, purpose, required_fields[]}]   # e.g. "Rechtsgrundlagen | SG-Nummern, Stand"
task_core: <=300 chars for round-1 verbatim search
```
From our analysis: the biggest single gap was "offene Punkte"/limits (agent 2.00 vs 0.69) [O], so the plan always appends a part "Offene Punkte und Grenzen", and "Stand-Datum" is a required field of every part.

### 3.12 T12 Clarifying questions

DZ `generateFeedback`: "ask some follow up questions to clarify the research direction. Return a maximum of N questions, but feel free to return less if the original query is clear". `run.ts` merges `Initial Query + Q/A` into one `combinedQuery` that anchors everything downstream, including the final report. Take: the "fewer if clear" rule and the merged brief. Skip the interactive CLI. In OWUI, fold it into the plan approval message (plan + at most 2 open questions + defaults). GPT-R replaced the answers with a fake "Automatically proceeding with research" [O], so the original intent of this step is lost there.

### 3.13 T13 Lead agent + subtopic subagents (LDR langgraph-agent)

System prompt gist (`analyze_topic`): "You are a research assistant writing a research report ... NOT a chat conversation ... do NOT ask clarifying questions ... You MUST research using available tools before answering - never answer from memory alone. Strategy: 1. start with web_search; 2. for multi-faceted questions use research_subtopic (pass 2-5 focused, non-overlapping questions); 3. fetch_content(url, focus) when snippets aren't enough, always pass the question as `focus`; 4. specialised engines; 5. answer with [N] citations." Subagent prompt: "focused research assistant ... return a concise factual summary. Reference sources by their [N] index numbers. Do NOT ask clarifying questions". All agents share one `SearchResultsCollector`; recursion limits `max_iterations*2+1` (lead 50 iterations by default, floor 10; subagent `max_sub_iterations`), `max_fetches_per_topic`, per-task deadlines, `SearchAvailabilityMiddleware` for rate limits. 

**Value for us**: this is a more flexible variant of our "research rounds with direct tool calling" and is the strategy with the local-model results [C]. It is more than we need for v1 and harder to bound. Take the *prompt rules* (never answer from memory, always pass the question as `focus`, no clarifying questions inside the loop) and the *shared registry*. A subagent per plan sub-question is a possible v2 if wall-clock matters (Gemma on 2x4090 is throughput-bound, so parallelism helps less than on API models [E]).

### 3.14 T14 Writer contract (ZH)

`RESEARCH_WRITER` rules worth copying nearly verbatim (German, administrative):
- "Formuliere ausschliesslich auf Basis der recherchierten Inhalte"; "zitiere Textstellen, Beschlussnummern, Gesetze exakt und vollständig".
- Honesty clause with a fixed sentence: if no reliable answer is possible, say so and give reasons; for partial information "weise ausdrücklich darauf hin".
- "Gib keine eigenen Ratschläge, Wertungen oder unbegründeten Vermutungen ab. Formuliere ausschliesslich, was sicher durch die Recherche gestützt ist."
- Fixed structure: Zusammenfassung -> Ausführliche Antwort (by Teilfrage) -> Grundlagen und Quellen; "beginne direkt mit der Zusammenfassung, ohne Einleitung"; end after the last chapter.
- Markdown conventions (`##` main headings, `-` lists).
**Fix before use**: ZH writes "ausschließlich" with ß in its prompts, which nudges the output to ß; write the prompt text in Swiss orthography. The prompt is hard-wired to "Kantonsrat Zürich" and "Du" for the expert: move to the preset. Add our parts from T11, T6 citation rules, and a required `Stand` per source.

### 3.15 T15-T17 Small robustness items

- **T15 Novelty state** (ZH `workflow.py`): `previous_queries`, `previous_chunk_ids`, `previous_doc_ids`; new round only processes unseen chunks/docs and says "Keine neuen Suchergebnisse" otherwise (stop signal). Ours: normalized-URL set, MCP-call signature set, queries compared by normalized token Jaccard or embedding cosine > 0.9.
- **T16 Role tiers** (ZH `get_model_and_workflow_config`): query gen + relevance on the cheapest model, analysis medium, final report best. For us: `gemma-fast` (thinking off) for T2/T3/T4/T5, `gemma-think` for plan, reflection, writer. Note GPT-R never reached `gemma-fast` in deep mode [O], so make the mapping explicit in the code, not in a config the framework may ignore.
- **T17 Guards**: LDR refuses to call the LLM when there are no sources ("it would fabricate citations") and returns a message; fetch guards on empty content (T5). ZH is the counter-example: failed parallel calls become the string `"Error: ..."` and are analysed as text [V, `utils.call_function_in_parallel`]. Ours: failed call -> dropped item + counter in the run log; zero cards for a sub-question -> the writer must state "keine Quelle gefunden" for it.

### 3.16 T19 DOCX export

ZH `utils.create_docx_from_markdown(user_query, markdown_text)` (about 90 lines, python-docx) builds headings, lists, bold/italic runs, hyperlinks and an AI disclaimer ("Gib nur als öffentlich klassifizierte Informationen ... " is the input-side disclaimer in `app_info.py`). Reuse the idea, not the code: use `pandoc` or `python-docx` against a Basel-Stadt template, add the disclaimer, source list with `Stand`, and the run parameters (queries, date). Offer it as a download from the pipe. Priority P2.

## 4. Why the GPT-R port drifts, and does dzhng carry the original query?

Verified by reading `dzhng-deep-research/src/deep-research.ts` and `gpt-researcher/gpt_researcher/skills/deep_research.py`:

| Aspect | dzhng original | GPT-R port | Effect |
|---|---|---|---|
| Original task at the top | `run.ts` builds `combinedQuery` (Initial Query + Q&A) and uses it for level 1 and for `writeFinalReport` | task + 3 questions with fake answers; used at level 1 and for the writer | same |
| Query passed to the recursion | `nextQuery` = `Previous research goal` + `Follow-up research directions`. **The original is lost here too.** | `next_query` = `Previous research goal` + `Follow-up questions`, same loss | same weakness |
| Previous learnings in query generation | **Yes**: `generateSerpQueries({query, learnings})` appends "learnings from previous research, use them to generate more specific queries" | **No**: `generate_search_queries(query, num_queries)` has no learnings parameter [V] | DZ's accumulated learnings (all derived from level-1 queries) act as a weak anchor; GPT-R has none |
| What runs per query | one Firecrawl search (limit 5) + one learnings call | a full nested `GPTResearcher(query=serp_query)` with its own planner (`MAX_ITERATIONS` sub-queries) and its own retrieval/filter | second-order drift: the sub-planner only sees the SERP query |
| Branch scheduling | all queries of a level in parallel (`Promise.all` with limiter) | recursion inside the `for result` loop, one branch at a time | slower, and each branch sees only its own goal |
| Final context | all learnings; "include ALL the learnings" | learnings first, then raw contexts, tail-trimmed to the last 25k words (learnings dropped first); writer prompt says "prioritize insights from deeper levels" | the deepest, most drifted branch survives [O] |
| Source preference | system prompt: "Value good arguments over authorities, the source is irrelevant" | not carried over, but no replacement | DZ is tuned for analyst-style open exploration, wrong for administration |

So the direct answer: **no, dzhng does not carry the original query into recursion either**. It stays roughly on topic because the learnings and goals are one hop away from level-1 queries and each branch is shallow. The GPT-R port multiplies the drift by adding a planner per branch, dropping the learnings feedback, and then trimming/prioritizing the wrong end. Our design avoids recursion on free text entirely: sub-questions are fixed by the plan and each round's queries are generated *for a named sub-question with the task in the prompt* (T1, T2, T8, T10).

## 5. Minimal skeleton using these pieces (pseudo-code)

```
# phase 1: plan (gemma-think, 1 call, user approves)
plan = plan_llm(task, preset.report_sections, preset.source_policy)   # T11, T12
brief = Brief(task, plan, today, preset)

# phase 2: research rounds (budgeted)
registry = Registry()                         # T6
state = {sq.id: "missing" for sq in plan.subquestions}
for rnd in range(preset.budget.rounds):
    targets = [sq for sq in plan.subquestions if state[sq.id] != "covered"]
    # 2a MCP first for law/statistics/grossrat sub-questions (deterministic, preset.mcp_first)
    for sq in targets if rnd == 0:
        if sq.intent in preset.mcp_first: call_mcp(sq) -> registry.add_card(url=canonical_url, quotes=...)
    # 2b queries (gemma-fast): T1+T2+T3, previous_queries+gaps in prompt
    queries = gen_queries(brief, targets, registry.queries, gaps)
    if rnd == 0: queries.append(Query(plan.task_core, lang="de", intent="secondary"))
    results = serper(queries, gl="ch", sites=preset.sites_for(q.intent))   # drop avoided domains
    # 2c triage (gemma-fast): domain pre-score + index list    # T4
    urls = triage(brief, results, k=preset.budget.fetch_per_round) - registry.seen_urls
    # 2d focused fetch (gemma-fast): verbatim quotes                # T5 (+T7 for read_full)
    for url in urls: fetch_and_extract(url, focus=sq_for(url), brief)
    # 2e reflect (gemma-think): coverage table, code decides         # T8, T10
    refl = reflect(brief, registry.headlines_by_sq())
    state.update(refl.status); gaps = refl.missing
    if done(state, registry, budget, no_new_cards_rounds): break

# phase 3: writer (gemma-think), one call per part or one call with cards for all parts
for part in plan.parts:
    text = write(part, cards=registry.cards_for(part), rules=T14+T6)    # only card ids allowed
report = assemble(parts) ; validate_citations(report, registry)         # T6 post-check
report += sources_from_registry(used_ids)                               # rendered by code
export_docx(report)                                                      # T19, optional
```

Token budget sketch [E] for a standard run: plan 6k; 3 rounds x (queries 2k + triage 3k x 2 + extraction 18k + reflect 6k) = ~100k; writer 20-35k in, 6-10k out. Total about 150-250k, inside the 200k-1M gate and far below GPT-R (472k) and NVIDIA (733k) [O], while adding the reflection and evidence cards the simple agent (22k) lacks.

## 6. Anti-patterns to avoid

1. **Rewriting the query from "goal + follow-ups" only** (DZ recursion, GPT-R port). Always carry the task and the sub-question (T1).
2. **A planner inside each branch** (GPT-R nested `GPTResearcher`): each level re-plans from a narrower string.
3. **Dropping the learnings/evidence from the query generator** (GPT-R) or putting a free-text blob there.
4. **Tail-trimming the writer context** so the oldest (best-anchored) material is dropped first, combined with "prioritize deeper insights" (GPT-R).
5. **System prompts that rank arguments above sources** ("the source is irrelevant", "high levels of speculation", "suggest solutions I didn't think about" in DZ `prompt.ts`). The opposite of our source policy.
6. **Learnings without a source id** (DZ): the sources are an unbound list at the end; this is exactly the NVIDIA citation problem.
7. **Letting the model build the sources list or URLs** (ZH inline links chosen by the LLM, no validation). Render sources from the registry; the model emits ids only.
8. **A model-only termination decision** (`finished: bool` in ZH). Compute stop in code from coverage + budget + novelty.
9. **Chunk-by-chunk LLM relevance gates on web results** (ZH style): 60-200 calls per round; use snippet triage (T4) on the web and the gate only for corpora.
10. **Strict-JSON-everywhere on an untested open model** (ZH). Use line formats / comma lists for tiny outputs, JSON schema only for plan and reflection, with a parse-failure fallback (ZH has one regex fallback, LDR has `extract_json` and line parsers).
11. **Errors turned into content** (ZH `"Error: ..."` strings analysed as text). Drop and count.
12. **Re-running a full search per report section** (LDR detailed report): multiplies cost by the section count; research once per sub-question.
13. **Free exploration without identifiers** (all three). For law/statistics/Grossrat tasks require SG number, Geschäftsnummer, dataset id and `Stand` as plan fields and check them in reflection [O: criteria 4, 7].
14. **Long prompts used as the verbatim search** (LDR guards at 300 chars). Use the planner's `task_core`.
15. **Treating the LDR numbers as report-quality evidence**: SimpleQA/xbench are short-answer tasks graded by an LLM on small samples; the repo itself lists "small samples, LLM-grader noise, contamination risk" [C]. They justify tool-calling feasibility with 27B-class local models, not the quality of long reports.
16. **Hard-coding corpus names and the audience in prompts** (ZH "Kantonsrat Zürich", "Du"). Put them in the preset.

## 7. Open points / not verified

- No ablations exist in any of the three repos for query-prompt wording; the rules in 3.2/3.3 are consolidated practice plus our own failure analysis, to be tested on the 13-task German set (3 repeats per arm).
- Whether Gemma-4-31B via vLLM follows the `lang | intent | query | purpose` line format without drifting needs a smoke test (cheap: 20 prompts).
- LDR's local-model results rest on `langgraph-agent` with a thinking-tag-stripping wrapper (`ProcessingLLMWrapper`); with the Gemma reasoning parser we get that for free, but tool-call parsing under vLLM `gemma4` is unverified here.
- I did not look at LDR's SearXNG-specific site filtering beyond the `language` and `categories` parameters; `site:` handling via Serper is ours to build from the preset. LDR has no domain allow/deny list for general web search (only journal reputation filtering for academic engines and egress/SSRF policies).
- ZH's team (datashop@statistik.zh.ch) may have an internal on-prem variant with more features; worth a question.
