"""Own sources in the engine (research_agent/own.py): tools with a fake retrieval, source kinds, only/prefer/off.
Same engine tests as in bebbi-deep-research (there against its presets); here with presets built in code."""

import asyncio
import copy
import functools
import json
from types import SimpleNamespace

from research_agent import ResearchAgent
from research_agent.config import Budget, Config, Preset
from research_agent.ledger import Ledger, SubQ
from research_agent.own import (OwnCollection, OwnFile, OwnSources, PassageIndex, knowledge_search, prompt_block, read_upload,
                                tool_specs)
from research_agent.sources import Registry


def arun(fn):
    """This repo has no pytest-asyncio: run an async test function to completion."""
    @functools.wraps(fn)
    def wrapper():
        return asyncio.run(fn())
    return wrapper


VOCAB = ["homeoffice", "frist", "gebühr", "reise", "auftragswert"]
PLAN = {"title": "Plan", "task_core": "Frist und Homeoffice", "language": "de", "parts": [{"id": "P1", "title": "Teil", "goal": "g"}],
        "sub_questions": [{"id": "Q1", "part": "P1", "text": "Welche Frist gilt?", "intent": "primary"}], "must_name": [], "constraints": []}
BIG = ("Allgemeine Hinweise zur Verwaltung. " * 60 + "\n") * 4 + "Gesuche sind mindestens 28 Tage vor Beginn einzureichen. Die Frist beträgt 28 Tage.\n" \
      + ("Weitere allgemeine Hinweise. " * 80 + "\n") * 6


class FakeLLM:
    """Scripted chat turns; keyword-count embeddings (so 'similar' means 'shares a keyword')."""

    def __init__(self, turns=(), json_out=None):
        self.turns, self.calls, self.json_out, self.prompts = list(turns), [], json_out or {}, []
        self.usage = SimpleNamespace(total=0, calls=0, prompt_tokens=0, completion_tokens=0, by_step={})

    async def embed(self, texts):
        return [[t.lower().count(w) for w in VOCAB] for t in texts]

    async def chat(self, role, messages, tools, step=""):
        self.calls.append({"messages": copy.deepcopy(messages), "tools": [t["function"]["name"] for t in tools or []]})
        return self.turns.pop(0)

    async def json(self, role, system, user, step="", default=None):
        self.prompts.append(user)
        return self.json_out.get(step, default)

    async def text(self, *a, **k):
        return "keine"


def say(content="", calls=()):
    tcs = []
    for i, (name, args) in enumerate(calls):
        function = SimpleNamespace(name=name, arguments=json.dumps(args))
        tcs.append(SimpleNamespace(id=f"c{i}", function=function,
                                   model_dump=lambda n=name, a=args, i=i: {"id": f"c{i}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}))
    return SimpleNamespace(content=content, tool_calls=tcs or None)


class FakeTools:
    def __init__(self):
        self.searched, self.fetched = [], []

    async def search(self, q, lang="de", num=8):
        self.searched.append(q)
        return [{"title": "Web", "url": "https://example.ch/x", "snippet": "s", "date": ""}]

    async def fetch_meta(self, url):
        self.fetched.append(url)
        return "Seite", "x" * 500, ""

    async def fetch(self, url):
        self.fetched.append(url)
        return "Seite", "x" * 500


def make_cfg(own_sources="prefer", engine="focus"):
    budget = Budget(rounds=1, max_subq=4, queries_per_subq=2, fetch_per_subq=3, max_follow_up=0, max_tokens=200000, words_per_part=350,
                    parts=[2, 3], focus_calls=8, focus_words=600)
    preset = Preset(name="p", description="d", language="de", routes={"primary": ["web"]}, engine=engine, own_sources=own_sources)
    return Config(presets={"p": preset}, budgets={"quick": budget}, mcp_servers={})


def make_agent(llm, own_sources="prefer", engine="focus"):
    agent = ResearchAgent(make_cfg(own_sources, engine), llm, FakeTools())
    return agent


def make_own(retrieve=None, files=None, collections=None):
    async def default(query, collection):
        return [{"text": "Homeoffice ist an zwei Tagen pro Woche möglich.", "name": "Weisung-Homeoffice.txt", "file_id": "w1",
                 "url": "https://owui/api/v1/files/w1/content", "date": "2026-10-01", "score": 0.7},
                {"text": "Kernzeit ist Dienstag und Donnerstag.", "name": "Weisung-Homeoffice.txt", "file_id": "w1",
                 "url": "https://owui/api/v1/files/w1/content", "date": "2026-10-01", "score": 0.6}]

    return OwnSources(files=files if files is not None else [OwnFile("f1", "merkblatt.pdf", BIG, "2026-10-09", "https://owui/api/v1/files/f1/content")],
                      collections=collections if collections is not None else [OwnCollection("kb1", "Personal")], retrieve=retrieve or default)




def test_tools_exist_only_for_what_is_there():
    assert [t["function"]["name"] for t in tool_specs(make_own())] == ["read_upload", "knowledge_search"]
    assert [t["function"]["name"] for t in tool_specs(make_own(collections=[]))] == ["read_upload"]
    assert [t["function"]["name"] for t in tool_specs(OwnSources(collections=[OwnCollection("k", "K")]))] == []     # no retrieval: no tool
    assert "Personal" in tool_specs(make_own())[1]["function"]["description"]


def test_registry_key_merges_sources_without_url():
    reg = Registry()
    a = reg.add("", "merkblatt.pdf", "upload", "erster Teil", key="upload:f1")
    b = reg.add("", "merkblatt.pdf", "upload", "zweiter Teil", key="upload:f1")
    c = reg.add("", "merkblatt.pdf", "upload", "anderer Text", key="upload:f2")
    assert a is b and a.id == "S1" and "erster Teil" in a.text and "zweiter Teil" in a.text and c.id == "S2"
    assert reg.add("https://a.ch/x#frag", "A", "web").id == reg.add("https://a.ch/x", "A", "web").id        # URL keys behave as before


@arun
async def test_passage_index_picks_the_matching_chunks_and_embeds_once():
    llm = FakeLLM()
    embedded = []
    real = llm.embed

    async def counting(texts):
        embedded.append(len(texts))
        return await real(texts)

    llm.embed = counting
    idx = PassageIndex(BIG)
    text, score = await idx.top(llm, ["Frist"], budget_chars=1500)
    assert "28 Tage" in text and len(text) < 1800 and score > 0.5
    await idx.top(llm, ["Homeoffice"], budget_chars=1500)
    assert embedded[0] > 5 and embedded.count(embedded[0]) == 1               # the chunks were embedded once, queries (1 text) twice
    short = PassageIndex("kurzer Text")
    assert (await short.top(llm, ["x"])) == ("kurzer Text", 1.0)


@arun
async def test_read_upload_registers_the_file_as_source_with_its_url_and_date():
    own, reg = make_own(), Registry()
    out, added = await read_upload(own, {"file": "U1", "query": "Frist"}, reg, FakeLLM(), "Frage")
    src = added[0]
    assert src.kind == "upload" and src.title == "merkblatt.pdf" and src.url.endswith("/f1/content") and src.date == "2026-10-09"
    assert out.startswith("[S1] merkblatt.pdf (2026-10-09)") and "28 Tage" in out
    out2, added2 = await read_upload(own, {"file": "merkblatt.pdf", "query": "Gebühr"}, reg, FakeLLM(), "Frage")
    assert added2[0] is src                                                    # same file: same source and ID
    err, none = await read_upload(own, {"file": "U9"}, reg, FakeLLM(), "Frage")
    assert err.startswith("error: unknown file") and none == []


@arun
async def test_knowledge_search_groups_passages_per_document():
    own, reg = make_own(), Registry()
    out, added = await knowledge_search(own, {"query": "Homeoffice"}, reg)
    assert len(added) == 1 and added[0].kind == "knowledge:Personal" and added[0].title == "Weisung-Homeoffice.txt"
    assert added[0].date == "2026-10-01" and "Kernzeit" in added[0].text and "zwei Tagen" in out
    assert out.startswith("[S1] Weisung-Homeoffice.txt (Wissensbasis Personal, 2026-10-01)")


@arun
async def test_knowledge_search_uses_only_the_collections_of_the_job():
    asked = []

    async def retrieve(query, collection):
        asked.append(collection.id)
        return []

    own = make_own(retrieve=retrieve, collections=[OwnCollection("kb1", "A"), OwnCollection("kb2", "B")])
    # a model that invents a "collection" argument cannot widen the search: the tool has only `query`
    out, added = await knowledge_search(own, {"query": "x", "collection": "kb-secret", "collection_names": ["kb-secret"]}, Registry())
    assert sorted(asked) == ["kb1", "kb2"] and added == [] and "no results" in out
    assert set(tool_specs(own)[1]["function"]["parameters"]["properties"]) == {"query"}


@arun
async def test_knowledge_search_reports_unreachable_bases_without_failing():
    async def retrieve(query, collection):
        if collection.id == "kb2":
            raise RuntimeError("down")
        return [{"text": "Text", "name": "a.txt", "file_id": "a"}]

    own = make_own(retrieve=retrieve, collections=[OwnCollection("kb1", "A"), OwnCollection("kb2", "B")])
    out, added = await knowledge_search(own, {"query": "x"}, Registry())
    assert len(added) == 1 and 'knowledge base "B" not reachable' in out
    async def broken(query, collection):
        raise RuntimeError("x")

    out, added = await knowledge_search(make_own(retrieve=broken), {"query": "x"}, Registry())
    assert added == [] and "not reachable" in out


def test_prompt_block_inlines_small_files_and_lists_large_ones():
    reg = Registry()
    own = make_own(files=[OwnFile("s", "klein.txt", "Gebühr CHF 120.", "2026-10-09"), OwnFile("g", "gross.pdf", BIG)])
    system, first = prompt_block(own, reg)
    assert 'U1 "klein.txt": complete text below as [S1]' in system and 'U2 "gross.pdf"' in system and "read_upload" in system
    assert "[S1] klein.txt (2026-10-09)\nGebühr CHF 120." in first and BIG[:40] not in first
    assert list(reg.sources) == ["S1"] and reg.sources["S1"].kind == "upload"
    assert "FIRST" in system and "Use ONLY" not in system                                       # prefer: own sources first, web for the rest
    own.mode = "only"
    assert "Use ONLY these sources" in prompt_block(own, Registry())[0]



def run_args(**kw):
    return dict(plan=PLAN, **kw)


@arun
async def test_focus_only_mode_has_no_web_tools_and_cites_the_sources():
    llm = FakeLLM([say(calls=[("read_upload", {"file": "U1", "query": "Frist"}), ("knowledge_search", {"query": "Homeoffice"})]),
                   say("# Bericht\n\n## Zusammenfassung\n\nDie Frist beträgt 28 Tage [S1]. Homeoffice ist an zwei Tagen möglich [S2].\n\n"
                       "## Offene Punkte und Grenzen der Recherche\n\nKeine.")])
    agent = make_agent(llm, "only")
    res = await agent.run("Frist und Homeoffice?", "p", "quick", **run_args(own=make_own()))
    assert llm.calls[0]["tools"] == ["read_upload", "knowledge_search"]
    assert agent.tools.searched == [] and agent.tools.fetched == []
    assert [t["tool"] for t in res.ledger["trail"]] == ["read_upload", "knowledge_search"]
    assert "[1] merkblatt.pdf. https://owui/api/v1/files/f1/content (Stand 2026-10-09;" in res.report
    assert {s["title"]: s["kind"] for s in res.ledger["sources"]} == {"merkblatt.pdf": "upload", "Weisung-Homeoffice.txt": "knowledge:Personal"}


@arun
async def test_focus_prefer_off_and_unchanged():
    llm = FakeLLM([say("# B\n\n## Zusammenfassung\n\nDie Frist beträgt 28 Tage [S1].")])
    agent = make_agent(llm)
    own = make_own(files=[OwnFile("f1", "merkblatt.pdf", "Die Frist beträgt 28 Tage.", "2026-10-09")], collections=[])
    res = await agent.run("Frage", "p", "quick", **run_args(own=own))
    assert llm.calls[0]["tools"] == ["web_search", "fetch_page", "read_upload"] and "[1] merkblatt.pdf." in res.report
    llm = FakeLLM([say("# B\n\n## Zusammenfassung\n\nText.")])
    agent = make_agent(llm, "off")
    await agent.run("Frage", "p", "quick", **run_args(own=make_own()))
    assert llm.calls[0]["tools"] == ["web_search", "fetch_page"] and agent.own is None
    llm = FakeLLM([say("# B\n\n## Zusammenfassung\n\nText.")])
    await make_agent(llm).run("Frage", "p", "quick", **run_args())
    assert llm.calls[0]["tools"] == ["web_search", "fetch_page"] and "OWN SOURCES" not in llm.calls[0]["messages"][0]["content"]


@arun
async def test_pipeline_extracts_cards_from_own_sources_and_only_mode_skips_the_web():
    findings = {"findings": [{"quote": "Die Frist beträgt 28 Tage.", "finding": "Frist 28 Tage"}]}
    llm = FakeLLM(json_out={"extract": findings})
    agent = make_agent(llm, "only", engine="pipeline")
    agent.own = make_own(files=[OwnFile("f1", "merkblatt.pdf", "Allgemein. Die Frist beträgt 28 Tage. Ende.", "2026-10-09", "https://owui/f1")],
                         collections=[])
    agent.own.mode = "only"
    led = Ledger()
    await agent._research_subq(SubQ("Q1", "P1", "Welche Frist gilt?"), PLAN, agent.cfg.presets["p"], agent.cfg.budgets["quick"], led)
    card = next(iter(led.cards.values()))
    assert card.source_kind == "upload" and card.title == "merkblatt.pdf" and card.url == "https://owui/f1"
    assert agent.tools.searched == [] and agent.tools.fetched == []
