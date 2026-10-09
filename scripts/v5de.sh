#!/usr/bin/env bash
# v5 (focus engine with short MCP tool descriptions) on the German set v0.3 (19 tasks) 3x; the agent loop with
# the Grossrat MCP on the 6 new full-text tasks; judges.
set -uo pipefail
cd "$(dirname "$0")/.."
log() { echo "=== $(date -Is) $*"; }
for v in v5 v5r2 v5r3; do
  log "de $v"; uv run python -m eval.run --candidate research-agent@$v --set de --concurrency 1
done
log "de baseline-agent@grossrat (new tasks)"
uv run python -m eval.run --candidate baseline-agent@grossrat --set de --ids DE-G4 DE-G5 DE-G6 DE-G7 DE-G8 DE-G9 --concurrency 1
for v in v5 v5r2 v5r3; do log "judge de $v"; uv run python -m eval.judge_de --candidate research-agent@$v; done
log "judge de baseline-agent@grossrat (new tasks)"
uv run python -m eval.judge_de --candidate baseline-agent@grossrat --ids DE-G4 DE-G5 DE-G6 DE-G7 DE-G8 DE-G9
log "done"
