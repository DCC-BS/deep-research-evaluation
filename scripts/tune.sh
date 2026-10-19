#!/usr/bin/env bash
# Tuning run: given variants on the tuning subset (config/tasks.yaml tuning_ids), then judge.
# Usage: setsid nohup scripts/tune.sh gpt-researcher@cfg gpt-researcher@patched > logs/tune-<name>.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/.."
IDS="51 57 87"
for cand in "$@"; do
  echo "=== $(date -Is) generate $cand"
  uv run python -m eval.run --candidate "$cand" --set drb --ids $IDS --concurrency 1
done
for cand in "$@"; do
  echo "=== $(date -Is) judge $cand"
  uv run python -m eval.judge_drb --candidate "$cand" --ids $IDS
done
uv run python -m eval.report --ids $IDS
echo "=== $(date -Is) done"
