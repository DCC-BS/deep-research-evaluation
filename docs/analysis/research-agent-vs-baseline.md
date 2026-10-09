# Why research-agent loses to the baseline agent on the German set

Data: `results/research-agent/de`, `results/baseline-agent/de`, `results/research-agent@v1/de` (13 tasks, one run each, judge GPT-5.4-mini). Everything below was computed from `raw/judge/artifacts/runs.jsonl`, no model or tool was called. The baseline's tool outputs are not stored (only tool calls), so what the baseline actually saw is inferred from its calls and report.

## Summary

Rubric: baseline-agent 53.8, research-agent 44.0, v1 47.1. The gap of 9.8 points is not a retrieval-depth problem. It comes from five causes, in order of weight:

1. **The gap sits in the shared criteria.** Shared criteria 1-6: 43.2% vs 57.7% (-14.5). Task criteria 7-10: 45.3% vs 48.0% (-2.7). Criteria 1+2 (complete/structured, every claim sourced) alone are 45% of the lost points. Structure is not the problem (13/13 reports have Zusammenfassung / parts / Offene Punkte). The judge's reasons for criterion 1 are about content: "wegen zahlreicher unbelegter oder falscher Aussagen nur ansatzweise vollständig".
2. **The report contract leaks into the plan.** The contract text ("SG- bzw. SR-Nummer", "Grossratsgeschäfte", "Stand") is part of the task string and the planner turns it into `must_name`, sub-questions, parts and web queries. 10 of 13 plans have `SG-Nummer`/`SR-Nummer`/`Grossratsgeschäft(e)` in `must_name` (also for tasks about waste fees and Klimastrategie). It produces queries like `Basel-Stadt Grossratsgeschäfte Leerstand Wohnungsmarkt` (ST1), parts like "Gesetzliche Grundlagen und Erlasse" (G2) and "Referenzen auf Erlasse und Geschäftsnummern" (G1), and closing sections that apologise for missing Grossrat items in a video surveillance report (R1).
3. **Grossrat retrieval is broken, not weak.** The query rules mention data.bs.ch; the query model copies it into `site:data.bs.ch ...` for 53/53 queries in G1, 21/22 in G2, 5/5 in G3. Serper has no pages for that site: 13 of 20 search events in G1 returned 0 results, G3 got 5 results in total and fetched nothing, `cards = 0`. The baseline searched `site:grosserrat.bs.ch "23.5544"` and cited 32 grosserrat.bs.ch URLs in G1. A second bug (`parts[1].strip('"')`, agent.py `_queries`) removes the closing quote of quoted phrases: 20/53 queries in G1 and 28/41 in R2 have unbalanced quotes.
4. **Section-wise writing pads thin evidence and loses global coherence.** Fixed `words_per_part` (800/1100) plus a 600-1000 word uncited "Einordnung und Bewertung" gives 4,100 words on average (baseline 770). G1: "Identifikation" 881 words from 20 cards, "Beschlüsse und Abstimmungsergebnisse" 37 words. S2 (comparison with "drei weitere Kantone"): parts name Freiburg, Luzern, Wallis, Waadt, Bern and Zürich; the summary compares Luzern/Wallis/Zürich/Bern; the table compares Luzern/Wallis/Waadt and omits Basel-Stadt. Criterion 7 = 0.
5. **Source list and citation hygiene.** Every source carries "abgerufen am 2026-10-08" instead of the document's Stand (criterion 4: 0.85 vs 1.08). 28% of citations are removed by the verifier and the sentence stays, so one in four checked claims turns into an uncited claim. MCP cards cite the server root (`https://mcp.opencaselaw.ch/`, 13 cards in R1-R3) or are titled "opencaselaw: get_legislation". Judge: "mehrere Quellen wirken thematisch verfehlt oder nicht abrufbar".

About 3-5 points of the gap may be judge artefact (exposure of long reports to the "unbelegte Zahlen -> max. 1 Punkt" rule, no date reference, one run per cell), but the three spot checks (section 5) show the main deductions are correct.

Ranked fixes (details in section 6): (1) strip the contract from planning and give it to the writer only; (2) fix the `strip('"')` bug and the Grossrat query rules/domain routing; (3) cut words and drop or shrink the analysis part, scale words to evidence; (4) pin comparison entities in the plan; (5) delete instead of un-cite failed factual sentences, show Stand and real URLs/titles in the source list; (6) harden the MCP loop. (1), (3) and the rules part of (2) are config or prompt-only.

## 1. Where research-agent loses, per criterion

Mean score 0-3 (13 tasks; G3 has 9 criteria):

| # | criterion | research-agent | baseline | v1 | delta RA-BA |
|---|---|---|---|---|---|
| 1 | complete and structured | 1.38 | 2.08 | 1.69 | -0.70 |
| 2 | every claim sourced, quote supports | 0.31 | 0.92 | 0.69 | -0.61 |
| 3 | primary sources first | 1.08 | 1.46 | 1.15 | -0.38 |
| 4 | Stand/Datum, outdated flagged | 0.85 | 1.08 | 0.92 | -0.23 |
| 5 | Swiss spelling, plain style | 2.08 | 2.54 | 2.15 | -0.46 |
| 6 | limits stated | 2.08 | 2.31 | 2.23 | -0.23 |
| 7 | task: identifiers/lists | 1.46 | 1.46 | 1.38 | 0 |
| 8 | task | 1.46 | 1.62 | 1.54 | -0.16 |
| 9 | task | 1.23 | 1.31 | 1.23 | -0.08 |
| 10 | task | 1.27 | 1.36 | 1.09 | -0.09 |

Points lost by type: shared 2.61 of 2.94 (89%), task criteria 0.33. By category (RA / BA): Recht 37.8 / 55.6, Strategien 47.8 / 58.9, Web-Inhalte 55.7 / 66.9, Grossrat 34.0 / 41.9, Statistik 46.7 / 30.0 (the only win, ST1).

By criterion type, with judge reasons:
- **Structure / completeness (c1)**. RA has the headings. Deductions are for content: R1 "mehrere inhaltliche Fehler sowie unklare oder widersprüchliche Aussagen" (BA 3), S2 "weicht mehrfach auf zusätzliche, nicht geforderte Vergleiche aus" (BA 2), W1 "teils falsche Gewichtungen" (BA 3), W3 (RA 2, BA 3), G3 "nennt keine Geschäfte, keine offenen Aufträge" (RA 0, BA 1).
- **Citations (c2)**: RA scores 0 in 9 of 13 tasks (baseline 2 of 13). Reasons repeat: "Quellen thematisch verfehlt oder nicht abrufbar" (R1), "sekundär" (S3), "unbelegte oder fragwürdige Zahlen" (W2). The rubric text caps the score at 1 as soon as an invented or unsupported number appears, so a 7,000-word report (R2, S1, S3, W2) is hit more easily than a 700-word one.
- **Primary sources (c3)**: RA 1.08 vs 1.46. R1: "Primärquellen ... durch Sekundärquellen ersetzt oder falsch verwendet" (BA 3: BV, IDG, IDV from gesetzessammlung). R3: "private Webseiten oder themenfremde Dokumente". In R1 the report cites a Bundesgericht decision, a job ad (campus-career.ch), rehab.ch and a Zug bill.
- **Identifiers (SG/SR/Geschäftsnummer)**: c7 is level (1.46 each). RA does not lose here on average, but it writes `SR 153.260` for IDG (that is SG in Basel-Stadt; the baseline makes the same mistake) and `§ 6a DSG` from the 2004/2007 documents instead of the current IDG. G1/G2: RA gets Geschäftsnummern only from the few grosserrat.bs.ch pages it found (13 cited URLs vs 32 for BA in G1).
- **Dates/Stand (c4)**: RA's source list gives only the fetch date; the baseline puts the document date into the label ("bs.ch, 2023", "In Kraft seit 16.01.2025"). W1: RA 0 "fehlen belastbare Standangaben im Fliesstext". Both lose points to "Zukunftsdatierung" (judge thinks 2026 is the future; RA in W2/G1/S1, BA in R2/S2/G1/G3).
- **Language (c5)**: RA 2.08 vs 2.54; ß count is 0 everywhere. Reasons: "teils schwer verständliche Ausschweifungen", "englische Begriffe", "spekulativ", "wertend" (R3, S1, S2, S3, W1, W2, ST1). Source: the prompt asks for mechanisms/causes and "Daraus folgt ..." paragraphs; samples contain "mechanistisches Zusammenspiel", "torpedieren", a LaTeX `$\S$` and a table cell `|, [1] |`.
- **Limits (c6)**: roughly level (2.08 vs 2.31). RA's closing is generic and generated from gaps and `must_name_missing`, so it lists contract artefacts ("SR-Nummern", "Grossratsgeschäfte" in R1).

## 2. Evidence pipeline

| task | preset/depth | subq | cards | distinct URLs | MCP cards | extract: zero-yield / rejected quotes | fetch failed | searches with 0 results |
|---|---|---|---|---|---|---|---|---|
| G1 | grossrat/deep | 18 | 20 | 14 | 11 | 54 of 64 / 0 | 0 | 13 of 20 |
| G2 | grossrat/std | 10 | 17 | 10 | 3 | 23 of 32 / 6 | 1 | 2 of 8 |
| G3 | grossrat/quick | 4 | 0 | 0 | 0 | 6 of 6 / 0 | 0 | 3 of 4 |
| R1 | recht/std | 9 | 61 | 24 | 22 | 16 of 45 / 4 | 4 | 0 |
| R2 | recht/deep | 14 | 98 | 46 | 4 | 17 of 64 / 13 | 1 | 2 of 17 |
| R3 | recht/std | 10 | 64 | 28 | 13 | 14 of 42 / 5 | 1 | 1 of 12 |
| S1 | web/deep | 12 | 118 | 42 | 0 | 1 of 44 / 28 | 1 | 0 |
| S2 | web/std | 11 | 61 | 24 | 0 | 4 of 28 / 16 | 0 | 3 of 14 |
| S3 | web/deep | 14 | 79 | 37 | 0 | 9 of 46 / 25 | 10 | 0 |
| ST1 | statistik/std | 9 | 27 | 13 | 2 | 15 of 28 / 3 | 0 | 2 of 7 |
| W1 | web/std | 12 | 69 | 28 | 0 | 12 of 40 / 33 | 3 | 0 |
| W2 | web/deep | 16 | 91 | 40 | 0 | 13 of 55 / 11 | 1 | 0 |
| W3 | web/quick | 4 | 20 | 7 | 0 | 1 of 8 / 12 | 1 | 1 of 4 |

Findings:
- **Source breadth is not the issue.** RA has 24 distinct card URLs per task (313 total); the baseline cites 17 per task (222) and fetched pages in only 2 of 13 tasks (5 `fetch_page` calls in total, W1 and ST1). Most baseline claims rest on search snippets and MCP output. Reading 8k-char focus passages and extracting verbatim quotes did not buy rubric points.
- **Overlap with the baseline's sources is low.** Only 36 of the baseline's 222 cited URLs appear among RA's card URLs. Domain overlap is partial (e.g. S3: 2 of 17 domains). In G1-G3 RA has none of the baseline's grosserrat.bs.ch Geschäft pages (0 of 59), so the baseline's content is not in RA's evidence there. Where the web works (R1, R3, S1, W1, ST1) RA's evidence contains the same primary pages (gesetzessammlung.bs.ch, fedlex, zh.ch, ge.ch, statistik.bs.ch) and more.
- **Queries.** The query model is fed `query_rules` and the contract-polluted `task_core`:
  - Grossrat: `site:data.bs.ch` in nearly every query (see summary point 3). The first query per sub-question also gets `site:` of up to 8 preferred domains appended (agent.py `_web`); for grossrat that yields `site:data.bs.ch ... site:grosserrat.bs.ch OR site:bs.ch ...`, which also returns nothing.
  - Contract drift: `Grossratsgeschäfte Basel-Stadt Photovoltaik Schutzzone` (R3), `Basel-Stadt "Digitalstrategie" Geschäftsnummer SG SR` (S2), `Kanton Zürich Einbürgerung "SG" "SR" gesetzliche Grundlagen` (W1), `Basel-Stadt Gesetzessammlung "Wohnwesen" Leerstand` (ST1).
  - Unbalanced quotes (W2 32/61, R2 28/41, G1 20/53) from `strip('"')`.
  - Good: multilingual queries do appear (fr/it for Genf, Lugano) and W1/W3 hit ge.ch, geneve.ch, lugano.ch.
- **Triage** is not logged (only counts), so choices cannot be audited. Pages are ranked preferred-domain-first before triage, then the model picks by title/snippet. Results show some off-topic picks reaching the report (job ad, rehab.ch, Zug bill in R1; `jelt.padovauniversitypress.it`, `list.ailocalism.org` in S3).
- **Fetch failures** are small (24 in total, S3 has 10 of 56). Extraction yield is fine on the web (S1 118 cards from 44 extracts). Rejected quotes are 156 of ~880 candidates (18%), but 32% in W1, 38% in W3, 24% in S3: the 92% fuzzy threshold plus markdown tables probably rejects table rows, which are exactly the fee/requirement facts W1/W3 need.
- **MCP.** 757k tokens (24% of all tokens) produced 55 of 725 cards (8%). data-bs: G1 made 79 calls, 22 with empty arguments `{}` (answer 168 chars, an error), 48 exact duplicates, `get_records` queries with invented field names returning 32 chars; 54 of 64 extracts gave zero cards because dataset catalogue pages are not evidence. opencaselaw works (R1: 22 MCP cards from `get_legislation`), but its cards often carry the MCP root URL because `_mcp` falls back to the server URL.
- **Reflect/rounds.** G1 ran 3 rounds with 18 sub-questions for 20 cards: new cards per round 9, 7, 4 while tokens went 131k, 264k, 420k. `todo` re-researches every sub-question that is partial and has `coverage < 3` (almost all), so rounds repeat dead queries.
- **Plan drift.** Beyond must_name: G1's plan has parts "Beschlüsse und Abstimmungsergebnisse", "Klassifizierung nach Vorstossart", "Referenzen auf Erlasse und Geschäftsnummern" (task asked for Vorstösse, Antworten, Beschlüsse). G3 collapsed into one part ("Hauptteil: ...") with `task_core` containing "SG/SR-Nummern, Geschäftsnummern, URLs". S2 plan never fixes which three cantons.

## 3. Writing and verification

- **Verifier removal.** 1,657 citations checked, 1,196 kept, 311 removed by entailment and 150 by number check: 28% (S1 33%, R1 37%, W3 35%, ST1 17%). Removed citations leave the sentence in place (agent.py `_verify`: `text.replace(u, u.replace(tag, ""))`). Share of cited sentences in the final text: 0.40 (v1 0.56, baseline 0.43). Correlation of removal % with rubric is -0.11 and with criterion 2 is +0.05, so the removal rate alone does not explain the scores; it does lower citation density versus v1 and leaves uncited factual statements.
- **Length.** 4,100 words vs 770 (baseline) and 1,680 (v1). Within research-agent, length vs rubric is r = +0.30; pooled across engines the earlier analysis found r = -0.37 (`docs/analysis/german-set.md`). The data are consistent with: length is not penalised by itself, but each extra claim is another chance to hit the "falsch/unbelegt -> max 1 Punkt" rule, and padding produces the "spekulativ/Ausschweifungen" deductions in c5. Analysis sections add 600-1,000 uncited words (15-20% of a report); the summary is written after them and repeats their conclusions.
- **Repetition/genericity.** No exact paragraph duplicates (S2: 79 of 79 paragraphs unique), but heavy topical repetition: S2 mentions Luzern/Bern/Zürich/Wallis 14-15 times each across overview, per-canton parts, comparison, synthesis and analysis. Each part has a fixed length target regardless of evidence (G1 "Beschlüsse" 37 words next to 880-word parts built from 20 cards), so thin parts are filled with methodology talk ("Systematik der Identifikation und Datengrundlage" in G1).
- **Structure vs contract.** Aligned: `Zusammenfassung`, parts, `Einordnung und Bewertung`, `Offene Punkte und Grenzen der Recherche`. The extra analysis part and 5-10 `###` sub-headings inside each part make a long document; the baseline uses 3 headings.
- **Lead citation oddity.** Sources are numbered by first citation, so the summary's first claim in R1 ("Bundesgesetz über den Datenschutz (SR 235.1) [1]") points to BGer 6B_1133/2021, because the card was extracted from that decision. Single-card citation fits the quote but looks wrong to a reader and to the judge.

## 4. v1 (47.1) vs current (44.0)

Same 13 tasks, v1 had no analysis part, 430-550 words per part, 2-3 parts (current 4-7).
- Per task delta: G1 +3, G2 +20, G3 -19, R1 -10, R2 +13, R3 -10, S1 +3, S2 -33, S3 -17, ST1 +13, W1 -17, W2 -3, W3 +15. Mean -3.1, SD of deltas ~16, so SE ~4.5: **the change is within noise**. The baseline itself moved from 50.0 (older run in `german-set.md`) to 53.8.
- Direction by criterion: shared 49.1 -> 43.2, task 44.0 -> 45.3. Criteria 1 (1.69 -> 1.38) and 2 (0.69 -> 0.31) fell; 10 rose (1.09 -> 1.27). More depth helped task content (G2 +20, ST1 +13, R2 +13), longer/analytical text hurt the shared criteria.
- What changed: average length 1,680 -> 4,120 words; cited-sentence share 0.56 -> 0.40; removal 23% -> 28% (entailment removals 105 -> 311, mostly because there are 1.5x more cited sentences from the longer parts); tokens 2.2M -> 3.2M (+45%: extract +25%, mcp +82%, verify +93%, analysis +112k, summary +67%); the readability rule and analysis prompt add interpretive prose (c5 2.15 -> 2.08).
- Worst regressions S2 (-33), S3 (-17), W1 (-17) are tasks with comparison structure: more parts and more entities lead to the inconsistent entity sets described above. G3 -19: v1 got 3 cards, current 0 (the Grossrat query bug).

## 5. Judge artefacts: three verdict pairs checked against the reports

1. **R1, c1/c2/c3 (RA 1/0/1, BA 3/2/3).** Fair. RA's summary: "SR 235.1 [1]" cites a Bundesgericht decision, uses `§ 6a DSG` (2004-era text) next to `SR 153.260`, and cites Art. 13 DSG as the central test; the Quellen list contains a job ad, rehab.ch and a Zug bill. The baseline (BV Art. 13, IDG, IDV, PolG, all from gesetzessammlung/fedlex via MCP) is shorter, current, and lists "In Kraft seit" per source. The baseline also writes SR for SG numbers and the judge does not notice, so its 3s are slightly lenient.
2. **S2, c7 (RA 0, BA 1) and c8 (RA 1, BA 3).** Fair. RA's sets of cantons differ between summary, parts and table (see summary point 4), cells read "Nicht im Beleg enthalten", Basel-Stadt is missing in the final table. The baseline compares BS, ZH, BE, LU in one table with sources per cell.
3. **G3, c1 (RA 0, BA 1).** Fair for RA (0 cards, the report says nothing about any Geschäft), lenient for the baseline: it cites 16 grosserrat/bs.ch URLs but scores only 22.2% and the judge notes "2026-Dokumente nicht sauber markiert".

Artefacts that do exist:
- The judge's "Zukunftsdatierung" reflects its own knowledge cutoff (reports use 2026 data; today is 2026-10). It hits both systems (3 vs 4 reports) but lowers c4 for everybody. Fix: pass today's date in `PROMPT` in `eval/judge_de.py`.
- Exposure effect: the rubric says any invented or unsupported number caps the criterion at 1. A 4,000-word report with 150-300 citations is more likely to contain one; the judge reads only the report and cannot see the verbatim quotes that the pipeline verified. Quote verification therefore earns no rubric credit.
- Date handling: "abgerufen am" is not a Stand; the baseline's explicit Stand/In-Kraft dates are rewarded even where they may be unverified.
- Noise: one run and one judge pass per cell; baseline 50.0 vs 53.8 across reruns, v1-to-current delta SE ~4.5. Differences below ~5 points are not reliable; the research-agent deficit (9.8, same direction in 9 of 13 tasks) is.

## 6. Ranked fixes

Effects are estimates on the rubric, to be tested with 3 repeats per arm.

| # | fix | where | expected effect | config-only? |
|---|---|---|---|---|
| 1 | **Keep the contract out of planning.** Split `task.prompt` into question and contract (the contract starts at "\n\nAnforderungen an den Bericht:"); give the planner/queries/reflect only the question, and append the contract's identifier/Stand rules to `WRITE_PART` and `ANALYSIS` (`research_agent/prompts.py`: "Nenne bei Erlassen die SG-/SR-Nummer, bei Geschäften die Geschäftsnummer, bei Daten das Datum/den Stand der Quelle, nur wenn die Evidenz sie enthält"). Also add to `PLAN`: "must_name and parts come from the question only; ignore formatting and citation requirements". | `eval/candidates/research_agent.py` (strip before `agent.run`) + `prompts.py` PLAN | +3 to +5; removes junk parts/queries/closing text in 10 of 13 tasks | prompt/small code |
| 2 | **Fix query parsing.** `parts[1].strip('"')` -> strip only if the string starts and ends with a quote; drop queries with odd quote count. | `agent.py` `_queries` | +1 to +2 (R2, W2, G1 queries) | code (2 lines) |
| 3 | **Grossrat/web routing.** Rewrite `grossrat.query_rules` ("Web-Suche: site:grosserrat.bs.ch bzw. Geschäftsnummer im Format 23.5544; data.bs.ch nicht per site: durchsuchen, der Datensatz wird über das MCP-Werkzeug abgefragt"). Remove `data.bs.ch` from `prefer_domains.primary` and `.data` for the web leg (keep for MCP URLs), and put `web` first in `routes.primary` so that site-restricted searches on grosserrat.bs.ch always run. Stop appending the preferred-domain `site:` filter when the query already has `site:` (`_web`). | `config/presets.yaml` (grossrat, statistik), `agent.py` `_web` | Grossrat +8 to +12 on 3 tasks (about +2 overall); G3 from 0 cards | rules/routes config-only |
| 4 | **Shorter, evidence-scaled text.** `budgets.*.words_per_part`: standard 800 -> 350, deep 1100 -> 450, quick 350 -> 250; `parts` [3,5] standard, [4,6] deep; analysis words `max(400, wpp)` -> `min(300, wpp)` or skip the analysis part for `language: de` (`ANALYSIS`, step "analysis" in `run`); per part `words = min(wpp, 45 * cards_in_part)`. Target 1,500-2,500 words. | `config/presets.yaml` budgets, `agent.py` `_write_part`/`run` | +3 to +4 (c1, c2, c5: fewer unsupported claims; v1 shows shorter parts were not worse) | words config-only; per-card scaling is code |
| 5 | **Pin entities for comparison tasks.** In `PLAN`: "If the task asks to choose N entities (cantons, cities), choose them in the plan, name them in `must_name`, state the reason in `constraints`, and do not research others." Add `selection` to every `WRITE_PART`/`SUMMARY`/`ANALYSIS` call ("Use only these entities: ..."). Reflect follow-ups may not introduce new entities. | `prompts.py`, `agent.py` | S2 +20 to +30, W1/S3 +5; c1, c7 | prompt |
| 6 | **Do not leave failed claims uncited.** In `_verify`, if the citation fails and the sentence contains a digit or a capitalised name/identifier, delete the sentence (or mark "[nicht belegt]"); keep analytic sentences. Tune: use `entail` only on sentences with numbers/names, keep the cheap number check for all. Raising the 28% removal needs a better entailment prompt (give card finding plus quote, "yes if the quote supports the core fact"). | `agent.py` `_verify`, `ENTAIL` | c2 +0.2 to +0.3 (+2 pts); fewer unbelievable leftovers | code |
| 7 | **Source list with Stand.** Add `"date"` (publication/Stand/in-force date, empty if absent) to `EXTRACT`, store in `Card`, print `(Stand: ..., abgerufen: ...)` in `_resolve`. Prefer the page `<title>`/document title over "opencaselaw: get_legislation"; for opencaselaw cards use the `gesetzessammlung.bs.ch`/`lexfind` URL, for data-bs the dataset URL; never emit the MCP root. Drop sources that cite the same URL as the first-cited-card but fail the topic (single-card source ranking). | `prompts.py`, `ledger.py`, `agent.py` `_resolve`/`_mcp` | c4 +0.3, c2 +0.1 (+2 pts); c3 via cleaner list | code |
| 8 | **Plain administrative style.** In `WRITE_PART` replace "explain mechanisms, causes and context ... Readability" with: "Sachlich und knapp: Fakten, Zahlen, Zuständigkeiten, Fristen; keine Spekulation über Motive; keine Metaphern; keine LaTeX/Sonderzeichen; Tabellen für Vergleiche; Fachbegriffe beim ersten Gebrauch erklären." Forbid methodology paragraphs ("Systematik der Identifikation"). | `prompts.py` | c5 +0.3 (+1 pt) | prompt |
| 9 | **MCP loop hygiene.** Reject calls with empty `args`, dedupe identical `(tool, args)` per run, pass the tool's required-argument names in the system prompt, and do not extract tool listings (`get_datasets`/`get_dataset`) as evidence; cap `_mcp` per sub-question per round (G1: 79 calls). For data-bs, `get_records` must follow a `get_dataset` call in the same loop. Saves most of the 757k MCP tokens. | `agent.py` `_mcp`, `MCP_AGENT` prompt | cost -15% tokens; Grossrat/Statistik evidence quality | code |
| 10 | **Cheaper rounds.** `budgets.deep`: rounds 3 -> 2, `max_subq` 10 -> 8, `max_follow_up` 6 -> 4; in `_reflect` only re-research sub-questions with `coverage == 0` or those with named missing identifiers; skip sub-questions whose search returned 0 results due to site filters. | `config/presets.yaml` budgets, `agent.py` | tokens -25% (3.2M -> ~2.4M), no loss (G1 gained 7 and 4 cards in rounds 2-3) | rounds/subq config-only |
| 11 | **Table-friendly quote check.** `quote_in_page` threshold 92 -> 85 or compare per cell for markdown tables; log rejected quotes with page id. | `ledger.py` | W1/W3 +5 to +10 cards per run | code |
| 12 | **Judge hygiene** (affects all candidates, not the engine). Pass today's date to the judge, run 3 judge passes, report shared vs task criteria separately; log triage picks in `_web` for the next analysis. | `eval/judge_de.py`, `agent.py` | removes the "Zukunftsdatierung" noise, lowers noise to ~2 points | code |

Suggested first experiment (small, mostly config): fixes 1, 2, 3, 4 and 8. Expected combined effect +8 to +12 points (to roughly baseline level or above), with tokens falling to about 200k per task. Then 5-7 for the comparison and citation criteria, then 9-11 for cost and robustness. If the deficit remains after that, the baseline's advantage is "concise report from snippets": consider a `final_style: compact` writer that produces one 800-1,200 word report from all cards in a single call (keeping citation verification), instead of section-wise writing.

## Files used
`results/{research-agent,research-agent@v1,baseline-agent}/de/*.jsonl`, `research_agent/{agent,prompts,ledger,tools}.py`, `config/presets.yaml`, `eval/candidates/{research_agent,baselines}.py`, `eval/common.py` (`DE_REPORT_CONTRACT`), `eval/judge_de.py`, `testsets/de-admin.json`, `docs/analysis/german-set.md`.
