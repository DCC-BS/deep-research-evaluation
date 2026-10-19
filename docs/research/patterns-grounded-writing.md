# Outline-first research and citation-grounded writing: patterns for a lean Gemma-4-31B research agent

Scope: STORM / Co-STORM, WebWeaver, FS-Researcher, VeriTrace and related attribution work, read for what to copy into our skeleton (plan -> research rounds -> writer that cites only fetched pages). Sources are the papers and repo code read on 2026-10-08 (clones and PDF text in the session scratchpad). Nothing was run and no model was called. Cost and "Gemma fit" columns are my estimates unless a number is cited. Tags: [paper] = number from the paper, [code] = read in the repo, [inferred] = my reasoning, [unverified] = could not confirm.

## Summary

- The citation-accuracy gain in the literature does not come from outlines. It comes from three mechanical things: (a) the writer sees only the evidence for its own section, (b) every piece of evidence is a stored record with an ID, a verbatim quote and a URL, (c) the citation is checked or restricted by code, not by the writer's goodwill.
- WebWeaver is the clearest warning for us. With a prompt-only Qwen3-30B-A3B backbone its citation accuracy was 25.0%; after SFT on 3.1k writer trajectories it was 85.9% [paper, Fig. 14 and text]. Free-form tool-calling writers on ~30B models are not reliable. So we should move the citation work out of the model's tool loop and into data structures and code.
- VeriTrace is the best fit for our constraint. On a Qwen3.5-27B backbone it reaches RACE 52.6 with 134 effective citations and 68.5% citation accuracy [paper, Table 2]. Its trick is mechanical: reader findings without an exact-string quote from the page are dropped, records enter the evidence store "without further LLM processing", and each section writer only sees the quotes bound to its own 2-5 insights.
- Section-wise writing helps both comprehensiveness and accuracy. FS-Researcher: one-shot vs section-wise writing on the same knowledge base = RACE 47.63 vs 52.76 (GPT-5) [paper, Table 5]. WebWeaver: brute-force long-context writer vs hierarchical writer = citation accuracy 86.73 vs 93.37, insight 42.72 vs 50.02 (Claude Sonnet 4) [paper, Fig. 10].
- STORM as a whole is a poor fit (Wikipedia-article target, topic-only input, snippet retrieval, 1,500-word evidence cap per section). Two parts are worth keeping: perspective-guided question generation for the plan, and per-section retrieval of evidence by outline heading.
- Recommended minimum: a plan that mirrors the task (we already know this wins), an evidence store of quote-bound records created at fetch time, per-section writing from bound records only, one citation per claim, and a code-level verifier (quote substring check plus a Gemma entailment check on the claim) that deletes or rewrites unsupported sentences. Details in section 5.

## 1. Summary table

| Technique | Source | Phase | Value | Cost | Gemma fit | Priority |
|---|---|---|---|---|---|---|
| Quote-bound evidence records, quote must be an exact substring of the fetched page | VeriTrace (2605.26081) reader + evidence store E | research | Very high for citation accuracy; makes every claim traceable | Low: one extraction call per fetched page (page chunk in, 0-3 records out) | Good: extraction with a mechanical check is easy to retry | 1 |
| Section-wise writing from a section-specific evidence subset, prior-section tail with citations stripped | WebWeaver writer, FS-Researcher writer, VeriTrace section writer | write | High for accuracy and comprehensiveness | Medium: N section calls with 3-8k tokens in, 1-2k out; no growing history if sections are independent calls | Good if each call is a plain generation, not a multi-turn tool loop | 1 |
| Outline with evidence IDs attached per section (outline = plan + citation map), updated after each research round | WebWeaver planner (dynamic outline), VeriTrace cognitive graph | plan + research | High for structure and coverage; dynamic part is the gap-finding | Low-medium: one outline-update call per round | Good as a JSON/markdown update; weak if it requires multi-turn ReAct with `<write_outline>` tags | 1 |
| Post-write claim verification (quote substring + entailment on the single bound quote), delete or rewrite failures | Not one paper; combines VeriTrace's quote check, DeepTRACE-style statement/citation matrix, FS-Researcher section checklist | write | High: removes the dominant error classes in our analysis (stacked, swapped, invented specifics) | Medium: one short call per sentence batch; can use `gemma-fast` | Good: yes/no entailment on a 300-char quote is easy | 1 |
| One citation per claim, cited right after the claim, no stacked `[1][2][3]` | FS-Researcher writer prompt (code), our nvidia-quality.md | write | High: our data show multi-URL pairs valid 46% vs 67% single | None | Good | 1 |
| Perspective-guided question asking (personas from task) | STORM `GenPersona`, `AskQuestionWithPersona` | plan | Medium: breadth of sub-questions; STORM ablation +0.4 outline recall points | Low: 1 call for personas | Good | 2 |
| Simulated expert conversation (writer asks, retriever answers, multi-turn) | STORM `knowledge_curation.py` | research | Low-medium for us: replaced by direct tool calling | High: 3 personas x 3 turns x (queries + answer) | Medium: answer step paraphrases snippets, invites drift | 4 (skip) |
| Outline draft from parametric knowledge, then refine with conversation | STORM `NaiveOutlineGen` + `WritePageOutlineFromConv` | plan | Medium: draft outline before search gives structure, refinement adds task-specific headings | Low | Good, but must be seeded by the task text and required parts, not a bare topic | 2 |
| Checklist-gated section status (PENDING / IN-PROGRESS / COMPLETE) with section-level and report-level checklist | FS-Researcher | research + write | Medium: gap reflection and self-check; the "dual agent" split is worth -10 RACE when removed | Medium | Medium: self-review by a 31B model is lenient; pair with code checks | 2 |
| Evidence memory bank with retrieve tool for the writer (writer calls `retrieve(ids)`) | WebWeaver | write | High in the paper, but needs SFT for 30B | Medium | Weak: 25% citation accuracy without SFT | 3 (use code-side binding instead) |
| Co-STORM mind map (hierarchical knowledge base, LLM inserts info node by node) | Co-STORM `information_insertion_module.py` | research | Low-medium: good for human-in-the-loop UI | High: one LLM navigation step per tree level per snippet | Weak: tree-walk prompts are brittle | 4 (skip) |
| Co-STORM human-in-the-loop turn | Co-STORM paper | plan | Medium: matches our "user approves plan" step | Low | Fine | 2 (plan approval only) |
| Section-wise outline-driven retrieval (embedding retrieval of evidence by heading text) | STORM `retrieve_information(queries=section outline)` | write | Medium: simple way to bind evidence to sections when no explicit IDs exist | Low (we already have Qwen3-Embedding) | Good | 2 (fallback and gap check) |
| Lead / polish pass to remove repetition | STORM `PolishPage` | write | Low-medium | One long call | Risky: rewrites can drop citations | 3 (only over cited text with a citation-preservation check) |

## 2. Details per technique

### 2.1 STORM and Co-STORM

**What it does.** Pre-writing is separated from writing. (1) `FindRelatedTopic` + `GenPersona` produce up to 3 "editor" perspectives from the outlines of related Wikipedia pages plus a default "Basic fact writer". (2) For each persona a simulated conversation runs for at most `max_conv_turn=3` turns: the persona asks (`AskQuestionWithPersona`), `QuestionToQuery` turns the question into at most `max_search_queries_per_turn=3` queries, search results are filtered, `AnswerQuestion` writes an answer that must be supported by the gathered information, with `[n]` marks [code: `storm_wiki/modules/knowledge_curation.py`, `engine.py` defaults]. (3) `NaiveOutlineGen` drafts an outline from parametric knowledge, then `WritePageOutlineFromConv` refines it using the conversations [code: `outline_generation.py`]. (4) Each top-level section is written in parallel by `ConvToSection`: the section's outline headings are the retrieval queries against an embedded information table, `retrieve_top_k=5` snippets per query, and the evidence text is cut to 1,500 words before it is shown to the writer [code: `article_generation.py`]. Inline `[n]` numbers refer to snippet-sourced entries. (5) A lead section is written and `PolishPage` removes repetition [code: `article_polish.py`].

**Co-STORM** adds a round-table with several LLM experts, a moderator that picks a new discussion focus grounded in not-yet-used information (`GroundedQuestionGeneration`), and a hierarchical mind map. New information is placed into the tree by an LLM that walks it level by level with the actions `insert`, `step: child`, `create: child` (`InsertInformation`), and sections get expanded by `ExpandSection`. A human may interject at any turn; a final report is written from the mind map [paper 2408.15232; code `collaborative_storm/modules/`].

**Evidence.** STORM outline recall (heading soft recall / entity recall) with GPT-4: 92.73 / 45.91 vs Direct Gen 87.66 / 34.78 and oRAG 89.55 / 42.38; removing the conversation hurts most (w/o Conversation 88.75 / 39.30), removing perspectives costs little (92.39 / 42.70) [paper 2402.14207, Table 3]. Citation recall 84.83, citation precision 85.18 judged by Mistral 7B-Instruct [paper, Table 4]. The human study used 20 Wikipedia-like topics; STORM beats oRAG on organization and coverage. The measure of "citation precision" there is NLI on a snippet by a 7B model, which is much weaker than the FACT judge we use.

**Why STORM scored 32.8 RACE with Qwen3-32B on DRB.** I could not locate the table that reports 32.8 [unverified; the DRB paper text I have does not list STORM]. From the code, the likely causes are structural [inferred]:
1. Input is a bare topic. Everything in the prompts is "Wikipedia article on {topic}". A DRB or administrative task has constraints, named entities, a question and required parts. None of that reaches the outline or the writer, so instruction-following and comprehensiveness criteria are missed. NVIDIA wins for the opposite reason: its plan mirrors the task.
2. Target is an encyclopedic, neutral article. RACE rewards analysis and insight. STORM's `PolishPage` deletes repetition, the writer is told to write a Wikipedia section, and there is no analysis or recommendation step.
3. Evidence is search snippets, not fetched pages. The information table stores snippets; the writer sees at most 5 snippets per heading query and at most 1,500 words per section. Reports cannot get long or number-dense from that.
4. Fixed shallow budget: 3 personas x 3 turns x 3 queries, no reflection on gaps and no second round.
5. DSPy output parsing and the `[n]` numbering assume models that follow formats exactly. With a 32B model I would expect more malformed outlines and numbering errors [inferred].
Not the cause: perspective-guided asking itself. It is a cheap idea that works.

**Cost.** Per STORM run, roughly personas (1 call) + 9 questions + 9 query calls + 9 answer calls + outline (2) + one writer call per section + lead + polish: about 40-60 short calls. Prompts are small (1-6k tokens). Latency is mostly search. Co-STORM is more expensive per turn because every snippet triggers a tree walk (several LLM calls).

**Robustness with ~30B.** Persona and question generation are fine. The expert-answer step is the risk: it paraphrases snippets and then becomes a second layer between source and report, which is the kind of URL/claim swap we see in NVIDIA notes (nvidia-quality.md). The mind-map insertion is a navigation prompt with a strict output grammar; skip it.

**What to take.**
- Perspective prompt in the plan phase: ask for 3-4 stakeholder perspectives relevant to the task (for Basel-Stadt: Verwaltung, Recht, betroffene Bürger, Finanzen) and generate 2-3 sub-questions per perspective. This broadens coverage at the cost of one call.
- Draft outline from the task before searching, then refine after the first round (what STORM does with conversations). Keep the task text and required parts in the prompt.
- Section heading as retrieval query over the evidence store (embedding search), as a fallback when a section's bound evidence is thin.
- Co-STORM: only the human turn. Our "user approves the plan" is the same idea in the cheapest form.

### 2.2 WebWeaver (Alibaba / Tongyi)

**What it does.** Two agents [paper 2509.13312]. The planner loops over `search` / `retrieve` and `<write_outline>` actions; it alternates evidence gathering and outline rewriting ("dynamic outline"). Each outline node carries `<citation>id_x</citation>` pointers to saved pages in a memory bank. Only a short summary of each page goes into the planner context; raw pages stay in the bank. The writer receives the outline and, per section, calls `retrieve` with the IDs listed in the outline, thinks, writes within `<write>` tags, and the retrieved raw text is pruned from the context and replaced by a placeholder before the next section. Final output cites with `<qwen:cite id="id_1,id_2">statement</qwen:cite>` spans [code: `WebAgent/WebWeaver/prompt/write_prompt_multi_hop_2.py`; the README confirms the section-wise retrieve-then-write design].

**Prompt gist [code].** Writer: "You are an analyst and interpreter, not a compiler or summarizer"; call tools to retrieve the related page contents for each section; wrap every verifiable claim (numbers, attributed opinions, specific examples) in the cite tag; common knowledge is not cited; tables must be followed by analysis; avoid "multiple citations strung together without synthesis". Planner: "Web Information-Seeking & Outline-Building Master", cross-check key points, put supporting references next to outline points.

**Evidence [paper].**
- DRB, Claude Sonnet 4: RACE 50.58, 200.75 effective citations, citation accuracy 93.37. Qwen3-235B-A22B: RACE 50.62, 166.73, 78.25. GPT-oss-120B: 48.11, 64.88, 66.14. Qwen3-30B-A3B-Instruct (prompting only): RACE 46.77, 26.74 effective citations, **25.00** accuracy (Table 1).
- SFT of Qwen3-30B-A3B on WebWeaver-3k (3.3k planner and 3.1k writer trajectories from a teacher): citation accuracy 25% -> 85.90%, DeepConsult 4.57 -> 6.09 (text around Fig. 14). This is the "25% -> 86%" figure. It is an SFT result, not a prompting result.
- Hierarchical vs brute-force writing, Claude Sonnet 4: citation accuracy 86.73 -> 93.37, supportiveness 90.95 -> 98.73, insight 42.72 -> 50.02, readability 43.82 -> 49.79 (Fig. 10).
- Scale of a run (Table 3, Claude): about 16 search steps, 112 saved pages, 20 queries, 67k evidence tokens, 15k summary tokens, 26k output tokens, about 25 writing steps. The planner reads 100+ pages.
- Under a shared Qwen3.5-27B backbone, rerun by the VeriTrace authors: WebWeaver 50.77 RACE [VeriTrace Table 3].

**Cost.** The planner is a long ReAct trajectory with growing context; the writer is about 25 steps with pruning, so each step is moderate. Total output near 26k tokens for the report plus planner thinking. Estimate for Gemma: 300-600k tokens per run if the planner keeps page summaries only [inferred].

**Robustness with ~30B.** Planner side: acceptable with summaries only. Writer side: the paper's own prompt-only 30B result (25% citation accuracy, 26.7 effective citations) shows the multi-turn `retrieve` + `<write>` + custom cite-tag protocol is the fragile part for a model that was not trained on it. Gemma-4-31B is stronger than Qwen3-30B-A3B at tool calling in my expectation, but I have no evidence, so treat the 25% as the downside case [inferred].

**What to take.**
- Memory bank: full fetched pages stored outside context; context holds only summaries and IDs.
- Outline nodes carry evidence IDs (the plan is also the citation map).
- Writer isolation per section, with raw evidence removed after each section.
- Do not copy: the writer-calls-`retrieve` protocol. Do the retrieval in code and hand the section its records (see 2.3).

### 2.3 Quote-bound claims: VeriTrace, FS-Researcher, and neighbours

**VeriTrace** [paper 2605.26081, code github.com/WolfGaga/VeriTrace]. A cognitive graph of tasks (the plan) plus an evidence store E of records `(m, v_m, w_m, l_m, src_m, task_m)`: id, verbatim quote (200-500 characters), one-sentence finding, the acceptance criterion it addresses, source URL, task. The reader returns either a finding or a gap; a finding needs "a one-sentence answer, a 200-500 character verbatim quote from the page, and the source URL", and findings without an exact-string quote that supports the answer are dropped before they reach the manager. Records enter E without further LLM processing. Three-layer writing: outline planner (sees the graph and findings, no quotes) -> section planner (sees the evidence index of IDs and labels, produces insights bound to 2-5 evidence IDs) -> section writer (sees only the bound quotes, with a tail of earlier sections capped at 15k characters, citation markers in the tail stripped so it cannot re-cite earlier evidence). Citation markers `[[m]]`; markers pointing to IDs not bound to the section are dropped ("§7 ref [[64]] dropped" in the appendix example). A convergence guard rejects `finish()` while any node has no finding.
- Numbers: Qwen3.5-27B config, DRB RACE 52.60 (3 runs, +-0.31), 134.2 effective citations, citation accuracy 68.46; under the same backbone WebWeaver 50.77, FS-Researcher 48.03, EnterpriseDR 49.16 (Tables 2-3). DeepConsult win rate 81.1%. Its own ablations of the cognitive-graph loops cost 1.2-2.8 RACE; the writing pipeline is not ablated in the text I read. So the 68.46 is the number to compare with our 55% (NVIDIA) and 79% (GPT-R): a 27B open model with quote binding lands in the high 60s, not 90.
- Cost: not reported in the parts I read; a run has a soft deadline of 70 minutes by default [paper]. Heavy.
- Fit: its mechanical parts (quote check, ID binding, marker stripping) are small and model-independent; its cognitive-graph controller is not needed for us.

**FS-Researcher** [paper 2602.01566, code github.com/Ignoramus0817/FS-Researcher]. Context Builder agent (search + read pages) writes `index.md` (hierarchy + TODOs), `knowledge_base/` notes whose every statement cites an archived file under `sources/`, reviews itself against a fixed checklist each session ("Full Traceability: does every Distilled Note contain citations pointing to its Archived Source"). Report Writer has no web tools; it writes an outline file that doubles as the todo list, then one section per session, with a section-level checklist ("any statements or claims without citations?") and a report-level checklist. Writer prompt asks for citation marks "exactly after the statement, instead of stacking them" and each source appears once in the reference list [code `prompts.py`].
- Numbers: Claude-Sonnet-4.5 RACE 53.94, 139.9 effective citations, 76.17% accuracy; GPT-5 52.76, 113.2, 60.04%; Gemini-2.5-Pro 52.51, 56.7, 78.20% (Table 2). GPT-5's lower accuracy is attributed to stacking several citations at the end of a paragraph (the same pattern we measured in NVIDIA). Ablations (GPT-5): remove persistent workspace -4.07 RACE; merge builder and writer into one agent -10.35; one-shot instead of section-wise writing -5.13 (Table 5). More builder sessions raise report quality (3 -> 10 rounds) but lower readability (59.3 -> 54.8). Under Qwen3.5-27B it only reaches 48.03 [VeriTrace Table 3], so it depends on a strong model.
- Cost: unbounded writer rounds in the paper; file-tool agents with long histories. Too heavy and too agentic for Gemma.
- Take: the separation "no browsing while writing", the per-section checklist as a code-checked list, and "cite right after the statement".

**Related work, for context.**
- DeepTRACE [arXiv 2509.04499]: audit of deep-research systems; citation accuracy ranges from 40% to 80% across systems and many statements are unsupported by their own cited sources. Our 55% and 79% sit inside that range, so this is the normal state, not a bug in our setup.
- "From Fluent to Verifiable" [arXiv 2602.13855]: position paper arguing for claim-level provenance graphs with continuous validation during synthesis. It supports the verifier step but gives no benchmark numbers.
- CAGE [arXiv 2607.24236] and intent-aware attributed LFQA [arXiv 2603.27435, ICLR 2026]: citation work on ASQA/ELI5/ExpertQA-style long-form QA, not on multi-page reports; small gains from claim-to-evidence mapping before writing. I read only abstracts and the CAGE method summary, so treat them as pointers [partially verified].
- Note on the user's brief: "VeriTrace ... claim-quote binding" is accurate for its reader and evidence store, but the paper is mainly about the regulated plan graph. The quote mechanism is a minor part of the text.

### 2.4 Section-wise vs single-pass writing

| Evidence | Setting | One-shot / brute force | Section-wise |
|---|---|---|---|
| FS-Researcher, GPT-5, same KB | RACE | 47.63 (comp 47.06, insight 45.64, readability 46.46) | 52.76 (51.96, 54.44, 51.26) |
| WebWeaver, Claude Sonnet 4 | RACE / citation accuracy | insight 42.72, readability 43.82, accuracy 86.73 | insight 50.02, readability 49.79, accuracy 93.37 |
| Our GPT-R analysis | trimmed 25k-word writer context, no per-section structure | 21k chars median, comp 42.0 | n/a |
| Our NVIDIA analysis | writer reads notes in 13 turns, 85% of prompt tokens re-sent | 12k chars median | n/a |

Mechanism: a section call can show the full text of its 3-8 evidence records instead of summaries, so the model quotes and computes from the actual text; a one-shot writer sees everything and attends to little of it. Length scales with the number of sections times per-section output (about 400-800 words each), instead of being capped by what a model is willing to emit in one pass. Our reports are 8-15k characters against 57-83k in the reference; 10-12 sections of 600 words reach 40k+ characters without asking for a long single generation.

For a 128k context and a 31B model: write each section as an independent call (no chat history), with a fixed header (task, plan, section spec, style rules) plus its evidence (8-20 records, about 3-8k tokens) plus a short summary of what earlier sections already said (about 500 tokens, no citations). Sections can run in parallel on vLLM; coherence comes from the outline plus a final "intro and Fazit" pass that sees section summaries only. Avoid WebWeaver's long multi-turn writer: its history grows and it re-sends its own earlier output.

Risks: repetition across sections (fix with the earlier-sections summary and a "do not repeat" list), and each section call producing a mini-essay with its own conclusion. Both are manageable by a style rule.

## 3. Mapping observed failure classes to techniques

Failure classes seen in evaluation runs (counts are not published):

| Observed failure | Technique that removes it |
|---|---|
| Stacked citations (several URLs on one claim, less often valid than single ones) | One citation per claim, enforced by regex after writing |
| Claim absent from the page, specifics from model memory | Writer sees only quotes; verifier checks that numbers and names in the sentence occur in the quote |
| Whole URLs supporting nothing (URL/claim swap) | Citation is an evidence ID resolved by code to quote + URL; the model never writes a URL |
| Over-generalised claim or recommendation cited to a topic page | Mark analysis sentences as uncited "Einordnung" by design; verifier rejects cited sentences that are not entailed |
| Agent saw only the first part of a page | Extraction reads the page in chunks, quote is selected from the full text |
| Query drift | Plan carries the original task into every sub-question |
| Report mirrors themes instead of named entities | Required parts as sections; check that each named entity appears |

## 4. Minimal implementation sketch for our skeleton

### 4.1 Data structures

```python
@dataclass
class Evidence:            # one row per quote; created in code, never by the writer
    id: str                # "E017"
    url: str
    title: str
    fetched_at: str        # ISO date; also feeds "Stand:" in the report
    quote: str             # 150-500 chars, verbatim substring of page_text (after whitespace normalisation)
    finding: str           # one sentence, German, what the quote says
    subq_id: str           # sub-question it answers
    source_type: str       # statute | case | open_data | official | news | other (from source policy preset)
    page_ref: str          # key into the page store (full text on disk)

@dataclass
class PlanSection:
    id: str; title: str    # heading
    question: str          # what this section must answer
    required: list[str]    # entities / aspects named in the task that must appear
    subq_ids: list[str]
    evidence_ids: list[str]  # filled during research (WebWeaver: outline carries citations)
    status: str            # PENDING | READY | THIN | DONE (FS-Researcher status idea)
```

Page store: `{page_ref: full_text}` on disk (WebWeaver memory bank). Only title + 2-3 sentence summary enters prompts.

### 4.2 Plan phase (1-2 calls, user may approve)

```
persp = llm(task -> 3 perspectives)                       # STORM GenPersona, task text in prompt
plan  = llm(task, persp -> JSON{sections[{title, question, required, subqs[]}], limits})
        # sections come from the task's own axes / named entities first, perspectives only add sections
show plan to user (Open WebUI) -> optional edits
```

### 4.3 Research rounds (per sub-question, bounded)

```
for round in 1..R:
  for subq in open_subqs:
      hits  = search(subq.queries); urls = pick(hits, source_policy)
      for url in urls:
          text = fetch(url); ref = store(text)
          for chunk in chunks(text, 6k tokens):               # read all of the page, not the head
              recs = llm_fast(subq, chunk -> [{finding, quote}])   # JSON, up to 3
              for r in recs:
                  if norm(r.quote) in norm(text) and 100<=len(r.quote)<=600:   # VeriTrace exact-string rule
                      evidence.add(Evidence(..., quote=r.quote))
  # reflection: one call, input = plan + counts per section + required entities not yet covered
  gaps = llm(plan, coverage_table -> [{section_id, missing, new_queries}])
  stop when no gaps or token/time budget hit
```
MCP tools (opencaselaw, data.bs.ch) write Evidence records too, with `url` = the canonical document or dataset URL and `quote` = the returned text span or the record row as text. This fixes the "bare tool name" citations in german-set.md.

### 4.4 Write phase

```
for sec in plan.sections (parallel ok):
    ev = [e for e in evidence if e.id in sec.evidence_ids]
    if len(ev) < k: ev += embed_search(sec.title+sec.question, evidence, top=8)    # STORM-style fallback
    prompt = header(task, style_rules) + section_spec(sec) + prev_summaries
             + "\n".join(f"[{e.id}] ({e.title}, {e.fetched_at}) {e.quote}" for e in ev)
    rules: "Jede Tatsachenaussage endet mit genau EINER Quelle [E..]. Keine Quelle für eigene Einordnung.
            Zahlen, Namen und Daten nur aus den Zitaten. Fehlt Evidenz: unter 'Offene Punkte' notieren."
    text = llm(prompt)
    text = verify(text, ev)
intro/Fazit/Offene Punkte = llm(section summaries only)
render: replace [E017] with [n] and build the reference list from Evidence.url/title/fetched_at
```

### 4.5 Verifier (mostly code, one small LLM call)

```
def verify(text, ev):
    for sent in split_sentences(text):
        ids = re.findall(r"\[(E\d+)\]", sent)
        if not ids: continue                                  # uncited analysis stays, shown as "Einordnung"
        if len(ids) > 1: sent = keep_best_id(sent, ids)       # rank by embedding similarity to quote
        if ids[0] not in ev_ids_of_section: drop marker
        nums = numbers_and_names(sent)
        if any(n not in e.quote for n in nums): flag
        verdict = llm_fast(f"Aussage: {sent}\nZitat: {quote}\nWird die Aussage vom Zitat gestützt? ja/teilweise/nein")
        if verdict != "ja": rewrite_once(sent, quote) or delete_marker_and_demote()
```
Budget: one short call per cited sentence (about 400 tokens each, 100-200 sentences) on `gemma-fast`, batched. Nothing here is a knowledge call; it is entailment against a 500-char quote.

### 4.6 Source policy presets (YAML)

Attach `source_type` and a rank to each Evidence at creation. The section writer prompt lists evidence ordered by rank; the verifier can require at least one `statute`/`case` record for sections tagged `legal: true`. Presets also set per-type fetch rules (e.g. do not accept `other` for numeric claims in the `verwaltung` preset).

## 5. Recommended combination (simplest that should help most)

Build in this order; each step is independently testable on the existing de-admin and DRB sets.

1. **Evidence store with exact-quote check at extraction (4.3).** This one change turns "writer cites a URL" into "writer cites a stored quote". Expected effect: removes class (a) invention if the writer is restricted to quotes. It is cheap.
2. **Per-section writer with section-bound evidence and one citation per sentence (4.4).** Addresses stacked citations (the largest single loss in our data), comprehensiveness (length scales with sections), and context dilution. No multi-turn tool loop; no WebWeaver-style `retrieve` calls.
3. **Plan mirrors the task, with `required` entities per section and a gap-reflection call (4.2, 4.3).** Keeps NVIDIA's structure advantage; adds the STORM perspective call only to widen sub-questions. The coverage table (required entities with record counts) is the reflection input and the pre-write check.
4. **Verifier pass (4.5).** Do this after 1-3, because with bound quotes most failures are already gone and the verifier just closes the rest. It also gives a metric for free: share of sentences surviving the check.
5. Optional later: checklist self-review per section (FS-Researcher), polish pass with citation-preservation check, user plan approval UI.

Expected outcomes (my estimates, to be measured, not promises): VeriTrace on a 27B model reaches 68% FACT accuracy with this kind of binding plus a much heavier research controller [paper]. With a verifier on top we should be able to beat that on accuracy because we delete failing sentences; the price is fewer effective citations (aim: stay above our gate of 20 per task, which the NVIDIA run only just met at 20.1). Token cost: extraction adds about 1 call per 6k-token chunk of fetched text; writing is N section calls of 5-10k tokens in; verification adds about 40-80k tokens. Total looks like 300-500k tokens per task, inside the 200k-1M gate [inferred; our agent baseline uses 22k, NVIDIA 862k].

Why not copy a whole system: WebWeaver depends on SFT for 30B models (25% -> 86%), FS-Researcher falls to 48.0 RACE on a 27B backbone and uses unbounded agent loops, VeriTrace's controller is large, STORM targets Wikipedia pages from a bare topic.

## 6. Anti-patterns

- Letting the writer see raw pages or long search results and write URLs itself. Use IDs, resolve in code.
- Stacked citations at the end of a sentence or paragraph (`[1][2][3]`). One claim, one source, placed after the claim.
- Citing analysis. Recommendations, comparisons and "Einordnung" are the model's own text; label them uncited instead of attaching the nearest topical URL.
- Extracting evidence from only the first N characters of a page (our NVIDIA analysis: specifics then come from memory). Read all chunks or retrieve the relevant chunk by embedding.
- A paraphrase layer between source and report (STORM's expert-answer step, NVIDIA's notes). If notes exist, every note must carry its quote and ID.
- Multi-turn writer with a tool protocol the model was not trained on (WebWeaver prompt-only 30B: 25% accuracy).
- Letting a model self-certify citations ("check that all claims have citations") without code checks; a lenient 31B reviewer says yes. Use regex, substring and entailment against a short quote.
- Passing only a topic to the outline step (STORM). Pass the task text and required parts, and keep them in every sub-prompt (GPT-R's query drift).
- Truncating the writer context from the front or tail without regard to relevance (GPT-R `trim_context_to_word_limit` keeps the newest, drops learnings).
- A polish/dedupe pass over cited text with no citation-preservation check.
- Building a mind map or tree-walk insertion for the knowledge base; flat records plus section tags and embeddings are enough.
- Reporting the effective-citation count as a goal on its own: VeriTrace's 134 effective citations come with 68% accuracy; GPT-R's 21k-character reports with 0 named entities show volume is not coverage.

## 7. Open points

- STORM's 32.8 RACE with Qwen3-32B: not found in the sources I could open; causes in 2.1 are inferred from code.
- VeriTrace has no isolated ablation of the quote filter in the text I read; its contribution to the 68.5% is plausible but not proven. A cheap internal ablation (store with and without the substring check) on 5 DRB tasks would settle it.
- WebWeaver code in the Alibaba repo contains prompts and ReAct runners; the exact retrieval tool backend uses internal services (Redis, scraper API), so the memory bank cannot be run as is.
- All "Gemma fit" ratings are untested judgments; the plan should include a smoke test of the extraction JSON and the entailment check on Gemma-4-31B and `gemma-fast`.

## Sources

- STORM, arXiv 2402.14207; code: github.com/stanford-oval/storm (`knowledge_storm/storm_wiki/modules/*.py`, `collaborative_storm/modules/*.py`)
- Co-STORM, arXiv 2408.15232
- WebWeaver, arXiv 2509.13312; code: github.com/Alibaba-NLP/DeepResearch/tree/main/WebAgent/WebWeaver
- FS-Researcher, arXiv 2602.01566; code: github.com/Ignoramus0817/FS-Researcher
- VeriTrace: Evolving Mental Models for Deep Research Agents, arXiv 2605.26081; code: github.com/WolfGaga/VeriTrace
- DeepTRACE, arXiv 2509.04499 (abstract-level summary only)
- From Fluent to Verifiable, arXiv 2602.13855; CAGE, arXiv 2607.24236; intent-aware attributed LFQA, arXiv 2603.27435 (skimmed)
