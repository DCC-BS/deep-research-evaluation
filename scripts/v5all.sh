#!/usr/bin/env bash
# v5 on all 20 DRB tasks (51, 57, 87 already done), then RACE + FACT for the new ones and the summary table.
set -uo pipefail
cd "$(dirname "$0")/.."
log() { echo "=== $(date -Is) $*"; }
IDS="51 53 57 59 66 68 69 71 72 77 78 81 82 87 90 93 94 96 97 100"
NEW="53 59 66 68 69 71 72 77 78 81 82 90 93 94 96 97 100"
log "drb v5 all 20"; uv run python -m eval.run --candidate research-agent@v5 --set drb --ids $IDS --concurrency 1
log "judge drb v5 (17 new)"; uv run python -m eval.judge_drb --candidate research-agent@v5 --ids $NEW
uv run python -m eval.report --ids $IDS > results/v5-report-all20.md
log "done"
