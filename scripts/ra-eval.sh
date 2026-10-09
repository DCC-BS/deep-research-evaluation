#!/usr/bin/env bash
# research-agent: DRB tuning subset + German set (standard depth unless the task says otherwise), then judge.
set -uo pipefail
cd "$(dirname "$0")/.."
CAND="${1:-research-agent}"
echo "=== $(date -Is) generate $CAND drb"
uv run python -m eval.run --candidate "$CAND" --set drb --ids 51 57 87 --concurrency 1
echo "=== $(date -Is) generate $CAND de"
uv run python -m eval.run --candidate "$CAND" --set de --concurrency 1
echo "=== $(date -Is) judge"
uv run python -m eval.judge_drb --candidate "$CAND" --ids 51 57 87
uv run python -m eval.judge_de --candidate "$CAND"
uv run python -m eval.report --ids 51 57 87
echo "=== $(date -Is) done"
