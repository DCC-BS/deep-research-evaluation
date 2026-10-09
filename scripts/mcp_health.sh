#!/usr/bin/env bash
# Log the HTTP status of every MCP host every 30 s until the given log file contains "=== ... done".
# Used during evaluation runs: bursts of 503 from the shared front proxy explain failed MCP calls.
until grep -q "=== .* done" "$1" 2>/dev/null; do
  line="$(date -Is)"
  for h in mcp.data.bs.ch mcp-grosserrat.statistik.bs.ch mcp.statistik.bs.ch mcp.opencaselaw.ch; do
    line="$line $h=$(curl -s -o /dev/null -m 10 -w '%{http_code}' https://$h/healthz)"
  done
  echo "$line"
  sleep 30
done
