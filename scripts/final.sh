#!/usr/bin/env bash
# Final run (tuned configurations). Sequential so runtimes stay comparable; each block judged right after.
#   DRB (20 tasks): research-agent all, gpt-researcher@patched + nvidia-dra@lean the 10 held-out tasks
#                   (stage-1 tasks already done); baselines keep their 10 stage-1 tasks.
#   German set (13 tasks, shared report contract): all five approaches.
set -uo pipefail
cd "$(dirname "$0")/.."
ALL="51 53 57 59 66 68 69 71 72 77 78 81 82 87 90 93 94 96 97 100"
STAGE2="59 66 69 71 77 78 81 93 96 100"
RA_NEW="53 59 66 68 69 71 72 77 78 81 82 90 93 94 96 97 100"
log() { echo "=== $(date -Is) $*"; }

log "drb research-agent";      uv run python -m eval.run --candidate research-agent --set drb --ids $RA_NEW --concurrency 1
log "judge drb research-agent"; uv run python -m eval.judge_drb --candidate research-agent --ids $RA_NEW

for cand in research-agent baseline-agent baseline-nosearch gpt-researcher@patched nvidia-dra@lean; do
  log "de $cand";       uv run python -m eval.run --candidate "$cand" --set de --concurrency 1
  log "judge de $cand"; uv run python -m eval.judge_de --candidate "$cand"
done

for cand in gpt-researcher@patched nvidia-dra@lean; do
  log "drb $cand";       uv run python -m eval.run --candidate "$cand" --set drb --ids $STAGE2 --concurrency 1
  log "judge drb $cand"; uv run python -m eval.judge_drb --candidate "$cand" --ids $STAGE2
done

log "report"
uv run python -m eval.report --ids $ALL | tee results/final-report-all20.md
uv run python -m eval.report --ids 90 51 53 57 68 72 82 87 94 97 | tee results/final-report-stage1.md
uv run python -m eval.viewer
log "done"
