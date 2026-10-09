#!/usr/bin/env bash
# After scripts/final.sh: (1) rerun GPT-Researcher German tasks that failed (writer context overflow),
# (2) wait for mcp.data.bs.ch (endpoint moved to /mcp on 2026-10-08), then rerun the data.bs.ch tasks for every
# approach that uses MCP, so all of them get the same conditions; judge, report, viewer.
set -uo pipefail
cd "$(dirname "$0")/.."
log() { echo "=== $(date -Is) $*"; }
DATABS="DE-G1 DE-G2 DE-G3 DE-S1 DE-ST1"
MCP_CANDS="research-agent baseline-agent gpt-researcher@patched nvidia-dra@lean"

until grep -q -E "=== .* done" logs/final.log; do sleep 120; done
log "final.sh finished"

log "rerun failed German tasks gpt-researcher@patched (outside data.bs.ch set)"
uv run python -m eval.run --candidate gpt-researcher@patched --set de --ids DE-R1 DE-R2 DE-R3 DE-W1 DE-W2 DE-W3 DE-S2 DE-S3 --concurrency 1
uv run python -m eval.judge_de --candidate gpt-researcher@patched --ids DE-R1 DE-R2 DE-R3 DE-W1 DE-W2 DE-W3 DE-S2 DE-S3

probe() {
  curl -s -m 20 -o /dev/null -w "%{http_code}" -X POST https://mcp.data.bs.ch/mcp -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
}
log "waiting for mcp.data.bs.ch"
for i in $(seq 1 288); do [ "$(probe)" = "200" ] && break; sleep 600; done
[ "$(probe)" = "200" ] || { log "mcp.data.bs.ch still down after 48h, giving up"; exit 1; }
log "mcp.data.bs.ch is back"

for cand in $MCP_CANDS; do
  # drop earlier results for these tasks (runs.jsonl keeps the history; latest run wins in reports)
  uv run python - "$cand" $DATABS <<'PY'
import json, sys
from eval.common import RESULTS, read_jsonl
cand, ids = sys.argv[1], set(sys.argv[2:])
for f in ("raw.jsonl", "judge.jsonl"):
    p = RESULTS / cand / "de" / f
    rows = [r for r in read_jsonl(p) if str(r["id"]) not in ids]
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
PY
  log "rerun data.bs.ch tasks $cand"
  uv run python -m eval.run --candidate "$cand" --set de --ids $DATABS --concurrency 1
  uv run python -m eval.judge_de --candidate "$cand" --ids $DATABS
done

log "report"
uv run python -m eval.report --ids 51 53 57 59 66 68 69 71 72 77 78 81 82 87 90 93 94 96 97 100 | tee results/final-report-all20.md
uv run python -m eval.report --ids 90 51 53 57 68 72 82 87 94 97 | tee results/final-report-stage1.md
uv run python -m eval.viewer
log "done"
