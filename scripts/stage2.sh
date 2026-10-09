#!/usr/bin/env bash
# Stage 2: remaining 10 DRB tasks for the two stage-1 finalists, sequential, then judge.
# Usage: setsid nohup scripts/stage2.sh > logs/stage2.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/.."
IDS="59 66 69 71 77 78 81 93 96 100"
for cand in gpt-researcher nvidia-dra; do
  echo "=== $(date -Is) generate $cand"
  uv run python -m eval.run --candidate "$cand" --set drb --ids $IDS --concurrency 1
  echo "=== $(date -Is) judge $cand"
  uv run python -m eval.judge_drb --candidate "$cand" --ids $IDS
done
echo "=== $(date -Is) report"
uv run python -m eval.report
uv run python -m eval.viewer
echo "=== $(date -Is) done"
