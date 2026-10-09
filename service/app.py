"""research-agent job service: chat-turn helpers (clarify, plan, edit) and a job queue with a night window.

Used by the Open WebUI pipe (pipe/deep_research.py) and by other apps (n8n). One process, SQLite for the
evaluation; Postgres in production (same tables).

  uv run uvicorn service.app:app --port 8088

Environment:
  RA_TOKEN                bearer token shared with the pipe (required)
  RA_LLM_BASE_URL         OpenAI-compatible endpoint (vLLM or the eval gateway)
  RA_LLM_API_KEY          key; "{job}" in it is replaced by the job id (per-job metering in the eval gateway)
  RA_SEARCH_URL / RA_SEARCH_KEY       Serper-compatible search endpoint (the gateway's /serper/search)
  RA_FIRECRAWL_URL / RA_FIRECRAWL_KEY
  RA_PRESETS              path to presets.yaml (default config/presets.yaml)
  RA_DB                   SQLite file (default data/research-agent.db)
  RA_NIGHT_WINDOW         e.g. 20:00-05:00 (jobs submitted with when=night start only inside it)
  RA_WORKERS              concurrent jobs inside the night window (default 1)
  RA_DAY_WORKERS          concurrent jobs outside it (default 1); only quick runs of a focus-engine preset
                          start outside the window, everything else is queued for the night
  RA_QUOTA_PER_DAY        jobs per user and day; 0 = no quota (default, decision 2026-10-09)
  OWUI_URL / OWUI_API_KEY optional: write finished reports into the Open WebUI chat message
                          (POST /api/v1/chats/{chat}/messages/{message}; needs an admin service account)
"""

import asyncio
import json
import os
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from research_agent import LLM, ResearchAgent, Tools, load_config

ROOT = Path(__file__).resolve().parent.parent
CFG = load_config(Path(os.environ.get("RA_PRESETS", ROOT / "config" / "presets.yaml")))
DB_PATH = Path(os.environ.get("RA_DB", ROOT / "data" / "research-agent.db"))
WINDOW = os.environ.get("RA_NIGHT_WINDOW", "20:00-05:00")
WORKERS = int(os.environ.get("RA_WORKERS", "1"))
DAY_WORKERS = int(os.environ.get("RA_DAY_WORKERS", "1"))
QUOTA = int(os.environ.get("RA_QUOTA_PER_DAY", "0"))

SCHEMA = """
create table if not exists drafts (id text primary key, task text, preset text, depth text, plan text, created real);
create table if not exists jobs (id text primary key, draft text, task text, preset text, depth text, plan text,
  user_id text, chat_id text, message_id text, run_when text, status text, created real, started real,
  finished real, events text, report text, stats text, evidence text, error text);
"""


class DB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)
        self.lock = asyncio.Lock()

    async def run(self, sql: str, *args):
        async with self.lock:
            return await asyncio.to_thread(lambda: [dict(r) for r in self.con.execute(sql, args).fetchall()])


db = DB(DB_PATH)


def auth(request: Request) -> None:
    if request.headers.get("authorization", "") != f"Bearer {os.environ['RA_TOKEN']}":
        raise HTTPException(401, "invalid token")


def make_agent(job_id: str, on_event=None) -> ResearchAgent:
    key = os.environ.get("RA_LLM_API_KEY", "").replace("{job}", job_id)
    llm = LLM(base_url=os.environ["RA_LLM_BASE_URL"], api_key=key)
    tools = Tools(search_url=os.environ["RA_SEARCH_URL"],
                  search_key=os.environ.get("RA_SEARCH_KEY", "").replace("{job}", job_id),
                  firecrawl_url=os.environ["RA_FIRECRAWL_URL"], firecrawl_key=os.environ.get("RA_FIRECRAWL_KEY", ""))
    return ResearchAgent(CFG, llm, tools, on_event=on_event)


def in_window(now: datetime | None = None) -> bool:
    start, end = (datetime.strptime(x, "%H:%M").time() for x in WINDOW.split("-"))
    t = (now or datetime.now()).time()
    return (t >= start or t < end) if start > end else start <= t < end


# ------------------------------------------------------------------ worker
async def run_job(job: dict) -> None:
    events: list[dict] = []

    async def on_event(kind: str, text: str) -> None:
        events.append({"t": round(time.time(), 1), "kind": kind, "text": text})
        await db.run("update jobs set events=? where id=?", json.dumps(events[-50:], ensure_ascii=False), job["id"])

    await db.run("update jobs set status='running', started=? where id=?", time.time(), job["id"])
    try:
        agent = make_agent(job["id"], on_event)
        res = await agent.run(job["task"], job["preset"], job["depth"], plan=json.loads(job["plan"]))
        stats = {**res.stats, "usage": res.usage}
        await db.run("update jobs set status='done', finished=?, report=?, stats=?, evidence=? where id=?", time.time(),
                     res.report, json.dumps(stats, ensure_ascii=False), json.dumps(res.ledger, ensure_ascii=False), job["id"])
        await deliver(job, res.report)
    except Exception as e:
        await db.run("update jobs set status='error', finished=?, error=? where id=?", time.time(), str(e)[:2000], job["id"])


async def deliver(job: dict, report: str) -> None:
    """Write the finished report into the Open WebUI assistant message (if configured and the job came from a chat)."""
    url, key = os.environ.get("OWUI_URL"), os.environ.get("OWUI_API_KEY")
    if not (url and key and job.get("chat_id") and job.get("message_id")):
        return
    async with httpx.AsyncClient(timeout=30) as http:
        await http.post(f"{url}/api/v1/chats/{job['chat_id']}/messages/{job['message_id']}",
                        json={"content": report}, headers={"Authorization": f"Bearer {key}"})


async def worker_loop() -> None:
    running: set[asyncio.Task] = set()
    while True:
        running = {t for t in running if not t.done()}
        window_ok = in_window()
        if len(running) < (WORKERS if window_ok else DAY_WORKERS):
            rows = await db.run("select * from jobs where status='queued' and (run_when='now' or ?) order by created limit ?",
                                1 if window_ok else 0, (WORKERS if window_ok else DAY_WORKERS) - len(running))
            for job in rows:
                await db.run("update jobs set status='starting' where id=?", job["id"])
                running.add(asyncio.create_task(run_job(job)))
        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # jobs interrupted by a restart are re-queued (they restart from the beginning)
    await db.run("update jobs set status='queued' where status in ('running','starting')")
    task = asyncio.create_task(worker_loop())
    yield
    task.cancel()


app = FastAPI(title="research-agent", lifespan=lifespan)


# --------------------------------------------------------------------- API
class TaskIn(BaseModel):
    task: str
    preset: str = "verwaltung_web"
    depth: str = "standard"


class EditIn(BaseModel):
    instruction: str


class JobIn(BaseModel):
    draft_id: str
    user_id: str
    chat_id: str | None = None
    message_id: str | None = None
    when: str = "night"           # now | night


@app.get("/presets", dependencies=[Depends(auth)])
async def presets():
    return [{"name": p.name, "description": p.description, "engine": p.engine} for p in CFG.presets.values()]


@app.post("/clarify", dependencies=[Depends(auth)])
async def clarify(body: TaskIn):
    return await make_agent("clarify-" + uuid.uuid4().hex[:8]).clarify(body.task)


@app.post("/plans", dependencies=[Depends(auth)])
async def create_plan(body: TaskIn):
    if body.preset not in CFG.presets or body.depth not in CFG.budgets:
        raise HTTPException(400, "unknown preset or depth")
    draft = uuid.uuid4().hex[:12]
    plan = await make_agent("plan-" + draft).plan(body.task, CFG.presets[body.preset], CFG.budgets[body.depth])
    await db.run("insert into drafts values (?,?,?,?,?,?)", draft, body.task, body.preset, body.depth,
                 json.dumps(plan, ensure_ascii=False), time.time())
    return {"draft_id": draft, "plan": plan}


@app.post("/plans/{draft_id}/edit", dependencies=[Depends(auth)])
async def edit_plan(draft_id: str, body: EditIn):
    rows = await db.run("select * from drafts where id=?", draft_id)
    if not rows:
        raise HTTPException(404, "unknown draft")
    d = rows[0]
    plan = await make_agent("plan-" + draft_id).edit_plan(json.loads(d["plan"]), body.instruction, d["task"],
                                                          CFG.presets[d["preset"]], CFG.budgets[d["depth"]])
    await db.run("update drafts set plan=? where id=?", json.dumps(plan, ensure_ascii=False), draft_id)
    return {"draft_id": draft_id, "plan": plan}


def runs_by_day(preset: str, depth: str) -> bool:
    """Office hours: only quick runs of the focus engine (about 20-50k tokens, 2-3 min) start right away."""
    p = CFG.presets.get(preset)
    return depth == "quick" and p is not None and p.engine == "focus"


@app.post("/jobs", dependencies=[Depends(auth)])
async def submit(body: JobIn):
    rows = await db.run("select * from drafts where id=?", body.draft_id)
    if not rows:
        raise HTTPException(404, "unknown draft")
    if QUOTA:
        since = time.time() - 86400
        used = (await db.run("select count(*) n from jobs where user_id=? and created>?", body.user_id, since))[0]["n"]
        if used >= QUOTA:
            raise HTTPException(429, f"quota of {QUOTA} research jobs per day reached")
    d, job_id = rows[0], uuid.uuid4().hex[:12]
    when = body.when if body.when in ("now", "night") else "night"
    if when == "now" and not in_window() and not runs_by_day(d["preset"], d["depth"]):
        when = "night"
    await db.run("insert into jobs (id, draft, task, preset, depth, plan, user_id, chat_id, message_id, run_when, status, created, events)"
                 " values (?,?,?,?,?,?,?,?,?,?,?,?,?)", job_id, d["id"], d["task"], d["preset"], d["depth"], d["plan"],
                 body.user_id, body.chat_id, body.message_id, when, "queued", time.time(), "[]")
    ahead = (await db.run("select count(*) n from jobs where status in ('queued','starting','running') and created<?",
                          time.time()))[0]["n"] - 1
    return {"job_id": job_id, "status": "queued", "when": when, "ahead": max(ahead, 0), "window": WINDOW}


@app.get("/jobs/{job_id}", dependencies=[Depends(auth)])
async def job_status(job_id: str):
    rows = await db.run("select id, status, run_when, created, started, finished, events, report, stats, error from jobs where id=?", job_id)
    if not rows:
        raise HTTPException(404, "unknown job")
    j = rows[0]
    return {**j, "events": json.loads(j["events"] or "[]")[-10:], "stats": json.loads(j["stats"] or "null")}


@app.get("/jobs/{job_id}/evidence", dependencies=[Depends(auth)])
async def job_evidence(job_id: str):
    rows = await db.run("select evidence from jobs where id=?", job_id)
    if not rows:
        raise HTTPException(404, "unknown job")
    return json.loads(rows[0]["evidence"] or "{}")
