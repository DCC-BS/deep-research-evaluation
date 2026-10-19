# Deep Research Evaluation

This repo evaluates deep-research engines for Bebbi Bot (Open WebUI, Kanton Basel-Stadt). The setup mirrors production: Gemma-4-31B NVFP4 on vLLM, Serper search, self-hosted Firecrawl and MCP sources. It runs on one machine with 2× RTX 4090.

- **Requirements and rubric:** [docs/requirements.md](docs/requirements.md)
- **Design research for the own agent:** [docs/research/](docs/research/) and [docs/research-agent-design.md](docs/research-agent-design.md)

## Layout

| Path | Content |
|---|---|
| `compose.yaml`, `gateway/`, `config/models.yaml` | vLLM (Gemma, embeddings), the metering gateway (role aliases, tokens per run, Serper and Tavily proxies with blocklist), Firecrawl |
| `eval/` | Harness: `run` (generate), `judge_drb` (RACE + FACT), `judge_de` (German rubric), `report`, `viewer` |
| `eval/candidates/` | Adapters for the approaches compared |
| `candidates/gpt-researcher/` | GPT-Researcher v3.7.0 venv, runner and code patches (`build_overlay.py`) |
| `candidates/nvidia-dra/` | NVIDIA Deep Researcher 2.2 config and prompt patches (`build_prompts.py`) |
| `research_agent/`, `config/presets.yaml` | Our own engine and its presets |
| `service/`, `pipe/` | Job service (FastAPI) and Open WebUI pipe for production |
| `config/tasks.yaml`, `testsets/de-admin.json` | Task sets (DRB subset, German administrative set) and MCP allowlists |
| `config/variants.yaml` | Tuning variants (`<candidate>@<variant>`) |
| `scripts/` | Smoke tests and the run scripts used for the evaluation |
| `vendor/deep_research_bench` | DeepResearch Bench, cloned at setup (git-ignored) |

## Prerequisites

- **GPUs:** 2× 24 GB (e.g. RTX 4090). Docker with the NVIDIA runtime.
- **Tools:** `uv`, Python 3.12+.
- **Models in the Hugging Face cache:** `RedHatAI/gemma-4-31B-it-NVFP4` and `Qwen/Qwen3-Embedding-0.6B`. vLLM runs with `HF_HUB_OFFLINE=1`.
- **Keys in `.env`** (see [.env.example](.env.example)):
  - `SERPER_API_KEY`
  - `OPENROUTER_API_KEY`, for the judges only
  - `NGC_API_KEY`, for the NVIDIA image

## Setup

```bash
cp .env.example .env                                   # fill in the keys
git clone https://github.com/Ayanami0730/deep_research_bench vendor/deep_research_bench
git -C vendor/deep_research_bench checkout f2735b5           # version used in the evaluation
docker compose --profile llm --profile search up -d   # vLLM, embeddings, gateway, Firecrawl
uv sync
(cd candidates/gpt-researcher && uv sync && .venv/bin/python build_overlay.py)
python3 candidates/nvidia-dra/build_prompts.py         # only for the nvidia-dra@cite variant
set -a && . ./.env && set +a && echo "$NGC_API_KEY" | docker login nvcr.io -u '$oauthtoken' --password-stdin
docker pull nvcr.io/nvidia/blueprint/aiq-agent:2.2.0
python3 scripts/smoke_gateway.py                       # 9 checks: aliases, thinking switch, tools, embeddings
```

**GPU memory:** Gemma uses 80% of each card and the embedding server 10% of GPU 0. At 82%, long prompts crashed vLLM with out-of-memory errors.

## Running

```bash
# generate reports (resumable; tasks already in raw.jsonl are skipped)
uv run python -m eval.run --candidate research-agent --set de --concurrency 1
uv run python -m eval.run --candidate gpt-researcher@patched --set drb --ids 51 57 87 --concurrency 1

# judge (OpenRouter): RACE + FACT about $0.35/report (--no-fact for baseline-nosearch); German rubric about $0.02/report
uv run python -m eval.judge_drb --candidate gpt-researcher@patched --ids 51 57 87
uv run python -m eval.judge_de --candidate research-agent

# comparison against the pass gates, and the side-by-side viewer (results/viewer.html)
uv run python -m eval.report --ids 51 57 87
uv run python -m eval.viewer
```

**Candidates**

| Name | What it is |
|---|---|
| `baseline-nosearch` | A single Gemma call, no tools |
| `baseline-agent` | A tool-calling loop: web search, page fetch, allowlisted MCP tools, at most 16 calls |
| `gpt-researcher` (`@patched`, `@cfg`) | GPT-Researcher deep mode. `@patched` adds the code fixes from `build_overlay.py` |
| `nvidia-dra` (`@lean`, `@cite`) | NVIDIA Deep Researcher via `nat run`, one container per task |
| `research-agent` | Our own engine (`research_agent/`). The preset per task is set in `eval/candidates/research_agent.py` |

**Results** go to `results/<candidate>/<set>/` (git-ignored):

| File | Content |
|---|---|
| `raw.jsonl` | Reports in DRB format |
| `runs.jsonl` | Tokens, runtime, searches, errors |
| `artifacts.jsonl` | Plans and evidence trails |
| `judge/` | Judge outputs |

Gateway logs go to `logs/usage.jsonl` and `logs/search.jsonl`.

## Reproducing the final evaluation

The final runs were done in this order, in order:

| Step | Script | What it does |
|---|---|---|
| 1 | `scripts/stage1.sh` | 10 DRB tasks for the four default candidates |
| 2 | `scripts/tune.sh`, `scripts/tune2.sh` | Tuning variants: tasks 51, 57, 87, then all 10 stage-1 tasks |
| 3 | `scripts/final.sh` | `research-agent` on all 20 DRB tasks; the German set for all approaches; the 10 held-out DRB tasks for `gpt-researcher@patched` and `nvidia-dra@lean` |
| 4 | `scripts/rerun66.sh` | Reruns after source outages and context overflows |
| 5 | `scripts/v3eval.sh` | `research-agent@v3`, then re-judges the German set |

Notes:
- **Code version:** the `research_agent/` code in this repo is **v3**.
- **Single runs are noisy:** about ±4 rubric points on the German set and about ±1.5 RACE. Repeat runs before drawing conclusions.
- **MCP endpoints:** `mcp.data.bs.ch` moved from `/` to `/mcp` during the evaluation. `config/tasks.yaml` and `config/presets.yaml` use `/mcp`.

**Deviations from the official DRB protocol**
- **20 of 50 English tasks** ([config/tasks.yaml](config/tasks.yaml)).
- **FACT scrapes with the local Firecrawl** instead of the Jina Reader. Unreachable pages count as `unknown` and are excluded from accuracy.
- **A focus step trims each cited page** to the 16k characters most relevant to its claims, ranked with local embeddings ([eval/drb_focus.py](eval/drb_focus.py)).

**Judges:**
- **DRB:** RACE GPT-5.5 (cleaning step: GPT-5.6 Luna), FACT GPT-5.4-mini. These are the official judges, via OpenRouter.
- **German rubric:** GPT-5.4-mini, with today's date in the prompt.

## Job service and Open WebUI pipe (local test)

```bash
set -a && . ./.env && set +a
export RA_TOKEN=test-token RA_LLM_BASE_URL=http://localhost:4000/v1 RA_LLM_API_KEY="${METER_API_KEY}:service-{job}" \
  RA_SEARCH_URL=http://localhost:4000/serper/search RA_SEARCH_KEY="${METER_API_KEY}:service-{job}" \
  RA_FIRECRAWL_URL=http://localhost:3002 RA_DB=data/test-service.db
uv run uvicorn service.app:app --port 8088
RA_TOKEN=test-token uv run python scripts/test_pipe.py "<research question> schnell" rechtsrecherche
```

The test script simulates an Open WebUI chat: task → clarifying questions → plan → plan edit → "ok jetzt" → report. The pipe ([pipe/deep_research.py](pipe/deep_research.py)) has not been tested in a real Open WebUI yet.
