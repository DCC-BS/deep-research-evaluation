#!/usr/bin/env bash
# After followup.sh: rerun GPT-Researcher@patched DRB task 66 (writer context overflow) with the retry, judge, report.
set -uo pipefail
cd "$(dirname "$0")/.."
until grep -q -E "=== .* (done|giving up)" logs/followup.log; do sleep 120; done
echo "=== $(date -Is) rerun drb 66"
uv run python -m eval.run --candidate gpt-researcher@patched --set drb --ids 66 --concurrency 1
uv run python -m eval.judge_drb --candidate gpt-researcher@patched --ids 66
uv run python -m eval.report --ids 51 53 57 59 66 68 69 71 72 77 78 81 82 87 90 93 94 96 97 100 > results/final-report-all20.md
uv run python -m eval.report --ids 90 51 53 57 68 72 82 87 94 97 > results/final-report-stage1.md
uv run python -m eval.viewer
echo "=== $(date -Is) done"
