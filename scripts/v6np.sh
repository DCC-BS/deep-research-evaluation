#!/usr/bin/env bash
# v6 without plan step (grossrat preset) on the 6 Grossrat full-text tasks, 2 runs, then judges.
set -uo pipefail
cd "$(dirname "$0")/.."
log() { echo "=== $(date -Is) $*"; }
NEW="DE-G4 DE-G5 DE-G6 DE-G7 DE-G8 DE-G9"
for c in research-agent@v6np research-agent@v6npr2; do log "run $c"; uv run python -m eval.run --candidate $c --set de --ids $NEW --concurrency 2; done
for c in research-agent@v6np research-agent@v6npr2; do log "judge $c"; uv run python -m eval.judge_de --candidate $c --ids $NEW; done
log "done"
