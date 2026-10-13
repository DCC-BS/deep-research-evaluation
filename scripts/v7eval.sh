#!/usr/bin/env bash
# DE-ST1 3x with the deployed data.bs fixes; v7 (shorter grossrat reports) 2x on the 6 full-text tasks; judges.
set -uo pipefail
cd "$(dirname "$0")/.."
log() { echo "=== $(date -Is) $*"; }
NEW="DE-G4 DE-G5 DE-G6 DE-G7 DE-G8 DE-G9"
for c in research-agent@v6st research-agent@v6str2 research-agent@v6str3; do
  log "run $c"; uv run python -m eval.run --candidate $c --set de --ids DE-ST1 --concurrency 1
done
for c in research-agent@v7 research-agent@v7r2; do log "run $c"; uv run python -m eval.run --candidate $c --set de --ids $NEW --concurrency 2; done
for c in research-agent@v6st research-agent@v6str2 research-agent@v6str3; do log "judge $c"; uv run python -m eval.judge_de --candidate $c --ids DE-ST1; done
for c in research-agent@v7 research-agent@v7r2; do log "judge $c"; uv run python -m eval.judge_de --candidate $c --ids $NEW; done
log "done"
