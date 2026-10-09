#!/usr/bin/env bash
# research-agent v3 (fixes from the German analyses): German set + DRB regression check, then re-judge the
# whole German set (judge now knows today's date) for all approaches, final reports and viewer.
set -uo pipefail
cd "$(dirname "$0")/.."
log() { echo "=== $(date -Is) $*"; }
log "v3 de";  uv run python -m eval.run --candidate research-agent@v3 --set de --concurrency 1
log "v3 drb"; uv run python -m eval.run --candidate research-agent@v3 --set drb --ids 51 57 87 --concurrency 1
log "judge v3 drb"; uv run python -m eval.judge_drb --candidate research-agent@v3 --ids 51 57 87
until grep -q "=== .* done" logs/rerun66.log; do sleep 120; done
log "re-judge German set (all approaches)"
for c in research-agent@v3 research-agent baseline-agent baseline-nosearch gpt-researcher@patched nvidia-dra@lean; do
  uv run python -m eval.judge_de --candidate "$c"
done
uv run python -m eval.report --ids 51 53 57 59 66 68 69 71 72 77 78 81 82 87 90 93 94 96 97 100 > results/final-report-all20.md
uv run python -m eval.report --ids 90 51 53 57 68 72 82 87 94 97 > results/final-report-stage1.md
uv run python -m eval.report --ids 51 57 87 > results/final-report-tuning3.md
uv run python -m eval.viewer
log "done"
