#!/usr/bin/env bash
# Keep the Render free-tier backend warm so it never cold-starts (~50s) on stage.
# Run this on the presenter's laptop during the event for guaranteed warmth,
# independent of GitHub's scheduler (which can lag a few minutes).
#
#   bash keep-warm.sh                 # default backend, ping every 10 min
#   bash keep-warm.sh <url> <seconds> # custom endpoint / interval
#
# Ctrl-C to stop.
set -euo pipefail

URL="${1:-https://graded-memory-api.onrender.com/api/llm/status}"
INTERVAL="${2:-600}"   # seconds; 600 = 10 min, safely under Render's ~15-min sleep

echo "Keeping warm: $URL"
echo "Interval: every ${INTERVAL}s. Ctrl-C to stop."
while true; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 90 "$URL" || echo 000)
  ts=$(date '+%Y-%m-%d %H:%M:%S')
  if [ "$code" = "200" ]; then
    echo "$ts  OK ($code)"
  else
    echo "$ts  WARN got $code — retrying next cycle"
  fi
  sleep "$INTERVAL"
done
