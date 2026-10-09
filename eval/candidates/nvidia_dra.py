"""NVIDIA Deep Researcher Agent 2.2 (Apache-2.0), one `nat run` container per task on the dr-eval network."""

import os
import re
import subprocess

import yaml

from eval.common import ROOT, Task, mcp_config, meter_key

IMAGE = "nvcr.io/nvidia/blueprint/aiq-agent:2.2.0"
CONFIG_DIR = ROOT / "candidates" / "nvidia-dra"
PROMPT_DIR = "/app/src/aiq_agent/agents/deep_researcher/prompts"  # inside the 2.2.0 image


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out.get(k) or {}, v) if isinstance(v, dict) else v
    return out


def task_config(task: Task, tag: str, variant: dict | None = None) -> str:
    """Base config plus an mcp_client function group per MCP source of the task (same allowlists
    as the other candidates). Returns the config file name inside CONFIG_DIR."""
    mcps = [s[4:] for s in task.sources if s.startswith("mcp:")]
    overlay = (variant or {}).get("config") or {}
    if not mcps and not overlay:
        return "config_eval.yml"
    cfg = _merge(yaml.safe_load((CONFIG_DIR / "config_eval.yml").read_text()), overlay)
    groups = cfg.setdefault("function_groups", {})
    tools = cfg["functions"]["deep_research_agent"]["tools"]
    for name in mcps:
        conf = mcp_config()[name]
        gname = "mcp_" + name.replace("-", "_")
        groups[gname] = {"_type": "mcp_client", "include": conf.get("allow", []),
                         "server": {"transport": "streamable-http", "url": conf["url"]}}
        tools.append(gname)
    out = CONFIG_DIR / "generated"
    out.mkdir(exist_ok=True)
    fname = "generated/" + re.sub(r"[^a-z0-9-]", "-", tag.lower()) + ".yml"
    (CONFIG_DIR / fname).write_text(yaml.safe_dump(cfg, sort_keys=False))
    return fname


def nvidia_dra(task: Task, tag: str, variant: dict | None = None, timeout_s: int = 7200) -> dict:
    query = task.prompt
    if task.language == "de":
        query += "\n\nSchreibe den Bericht auf Deutsch (Schweizer Rechtschreibung, kein ß)."
    name = "dra-" + re.sub(r"[^a-z0-9-]", "-", tag.lower())
    cmd = ["docker", "run", "--rm", "--name", name, "--network", "dr-eval",
           "-v", f"{CONFIG_DIR}:/cfg:ro",
           *[a for f in ("writer.j2", "researcher.j2") if (variant or {}).get("prompts")
             for a in ("-v", f"{CONFIG_DIR / 'prompts' / variant['prompts'] / f}:{PROMPT_DIR}/{f}:ro")],
           "-e", f"METER_RUN_KEY={meter_key(tag)}", "-e", f"TAVILY_API_KEY={meter_key(tag)}",
           "--entrypoint", "nat", IMAGE, "run", "--config_file", f"/cfg/{task_config(task, tag, variant)}", "--input", query]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, env=os.environ)
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        raise
    out = re.sub(r"\x1b\[[0-9;]*m", "", proc.stdout + "\n" + proc.stderr)  # strip ANSI colours
    if proc.returncode != 0:
        raise RuntimeError(f"nat run failed ({proc.returncode}): {out[-2500:]}")
    # nat's console front end prints "Workflow Result:\n['<report>']".
    m = re.search(r"Workflow Result:\s*\n(.*)", out, re.S)
    if not m:
        raise RuntimeError(f"no workflow result in output: {out[-2500:]}")
    article = m.group(1).strip()
    article = re.split(r"\n-{10,}|\n\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", article)[0].strip()
    if article.startswith("['") or article.startswith('["'):
        import ast
        try:
            article = ast.literal_eval(article)[0]
        except (ValueError, SyntaxError):
            article = article[2:-2]
    return {"article": article, "log_tail": out[-1500:]}
