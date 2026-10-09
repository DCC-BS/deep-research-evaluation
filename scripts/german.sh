#!/usr/bin/env bash
# German administrative set (13 tasks, MCP sources) for all four approaches, then the rubric judge.
# Usage: setsid nohup scripts/german.sh > logs/german.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/.."
for cand in baseline-nosearch baseline-agent gpt-researcher nvidia-dra; do
  echo "=== $(date -Is) generate $cand"
  uv run python -m eval.run --candidate "$cand" --set de --concurrency 1
  echo "=== $(date -Is) judge $cand"
  uv run python -m eval.judge_de --candidate "$cand"
done
uv run python -m eval.viewer
echo "=== $(date -Is) done"
