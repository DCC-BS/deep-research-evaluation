#!/usr/bin/env bash
# Stage 1: 10 DRB tasks for all four candidates, sequential (clean runtimes), then judge.
# Usage: setsid nohup scripts/stage1.sh > logs/stage1.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/.."
IDS="90 51 53 57 68 72 82 87 94 97"
# Task 90 was judged during calibration; judge only the new ones (report merges all judge runs).
JUDGE_IDS="51 53 57 68 72 82 87 94 97"
for cand in baseline-nosearch baseline-agent gpt-researcher nvidia-dra; do
  echo "=== $(date -Is) generate $cand"
  uv run python -m eval.run --candidate "$cand" --set drb --ids $IDS --concurrency 1
  echo "=== $(date -Is) judge $cand"
  if [ "$cand" = baseline-nosearch ]; then
    uv run python -m eval.judge_drb --candidate "$cand" --ids $JUDGE_IDS --no-fact
  else
    uv run python -m eval.judge_drb --candidate "$cand" --ids $JUDGE_IDS
  fi
done
echo "=== $(date -Is) report"
uv run python -m eval.report --ids $IDS
echo "=== $(date -Is) done"
