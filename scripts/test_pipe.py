#!/usr/bin/env python3
"""Simulate an Open WebUI chat against the pipe + job service (no Open WebUI needed).

  RA_TOKEN=... uv run python scripts/test_pipe.py "<task>" [preset]

Turns: task -> (clarifying questions -> "weiter") -> plan -> edit -> "ok jetzt schnell" -> report.
"""

import asyncio
import importlib.util
import os
import re
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("pipe", Path(__file__).resolve().parent.parent / "pipe" / "deep_research.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


async def main(task: str, preset: str) -> None:
    pipe = mod.Pipe()
    pipe.valves.SERVICE_URL = "http://127.0.0.1:8088"
    pipe.valves.SERVICE_TOKEN = os.environ["RA_TOKEN"]
    pipe.valves.POLL_SECONDS = 5
    messages: list[dict] = []

    async def emit(ev):
        print(f"   [status] {ev['data']['description']}", flush=True)

    async def turn(user: str) -> str:
        messages.append({"role": "user", "content": user})
        print(f"\nUSER: {user}")
        out = await pipe.pipe({"model": f"research_agent.{preset}", "messages": messages}, {"id": "test-user"},
                              emit, "chat-test", f"msg-{len(messages)}")
        messages.append({"role": "assistant", "content": out})
        shown = re.sub(r"<!--.*?-->", "", out, flags=re.S).strip()
        print(f"ASSISTANT ({len(out)} chars):\n{shown[:1800]}{' ...' if len(shown) > 1800 else ''}")
        return out

    print("models:", pipe.pipes())
    out = await turn(task)
    if '"state": "clarify"' in out:
        out = await turn("weiter")
    await turn("Bitte zusätzlich die Praxis des Datenschutzbeauftragten berücksichtigen.")
    await turn("ok jetzt")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "rechtsrecherche"))
