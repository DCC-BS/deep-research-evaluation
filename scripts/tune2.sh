#!/usr/bin/env bash
# Tuning round 2: the three candidate variants on the remaining 7 stage-1 tasks, then judge.
# Together with round 1 (tuning_ids 51 57 87) each variant then covers all 10 stage-1 tasks.
set -uo pipefail
cd "$(dirname "$0")/.."
IDS="90 53 68 72 82 94 97"
VARIANTS="gpt-researcher@cfg gpt-researcher@patched nvidia-dra@lean"
for cand in $VARIANTS; do
  echo "=== $(date -Is) generate $cand"
  uv run python -m eval.run --candidate "$cand" --set drb --ids $IDS --concurrency 1
  echo "=== $(date -Is) judge $cand"
  uv run python -m eval.judge_drb --candidate "$cand" --ids $IDS
done
uv run python -m eval.report --ids 90 51 53 57 68 72 82 87 94 97
uv run python -m eval.viewer
echo "=== $(date -Is) done"
