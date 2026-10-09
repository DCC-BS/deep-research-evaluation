#!/usr/bin/env bash
# v5: survey pipeline with longer, prose-style parts from more pages (web_survey only), DRB tuning tasks 2x.
set -uo pipefail
cd "$(dirname "$0")/.."
log() { echo "=== $(date -Is) $*"; }
for v in v5 v5r2; do
  log "drb $v"; uv run python -m eval.run --candidate research-agent@$v --set drb --ids 51 57 87 --concurrency 1
done
for v in v5 v5r2; do
  log "judge drb $v"; uv run python -m eval.judge_drb --candidate research-agent@$v --ids 51 57 87
done
log "done"
