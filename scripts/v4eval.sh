#!/usr/bin/env bash
# research-agent v4 (focus engine for the administrative presets, Grossrat MCP, survey pipeline with the v3
# sentence dropping undone): German set 3x, DRB tuning tasks 2x, baseline-agent with the Grossrat MCP 1x.
set -uo pipefail
cd "$(dirname "$0")/.."
log() { echo "=== $(date -Is) $*"; }
log "drb v4";   uv run python -m eval.run --candidate research-agent@v4   --set drb --ids 51 57 87 --concurrency 1
log "de v4";    uv run python -m eval.run --candidate research-agent@v4   --set de --concurrency 2
log "de v4r2";  uv run python -m eval.run --candidate research-agent@v4r2 --set de --concurrency 2
log "de v4r3";  uv run python -m eval.run --candidate research-agent@v4r3 --set de --concurrency 2
log "de baseline-agent@grossrat"; uv run python -m eval.run --candidate baseline-agent@grossrat --set de --concurrency 2
log "drb v4r2"; uv run python -m eval.run --candidate research-agent@v4r2 --set drb --ids 51 57 87 --concurrency 1
for c in research-agent@v4 research-agent@v4r2 research-agent@v4r3 baseline-agent@grossrat; do
  log "judge de $c"; uv run python -m eval.judge_de --candidate "$c"
done
for c in research-agent@v4 research-agent@v4r2; do
  log "judge drb $c"; uv run python -m eval.judge_drb --candidate "$c" --ids 51 57 87
done
uv run python -m eval.report --ids 51 57 87 > results/v4-report-tuning3.md
log "done"
