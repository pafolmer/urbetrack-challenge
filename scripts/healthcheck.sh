#!/usr/bin/env bash
set -euo pipefail

# MAX_RETRIES=0 (default): loop infinito para monitoreo local
# MAX_RETRIES=12: 12 intentos x 5s = 60s timeout (para CI)
MAX_RETRIES="${MAX_RETRIES:-0}"
INTERVAL="${INTERVAL:-5}"
URL="${HEALTH_URL:-http://localhost:8080/health}"

count=0

while true; do
    if curl -sf "$URL" > /dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] OK - $URL"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] FAIL - $URL"
        if [[ "$MAX_RETRIES" -gt 0 ]]; then
            count=$((count + 1))
            if [[ "$count" -ge "$MAX_RETRIES" ]]; then
                echo "Health check failed after $MAX_RETRIES attempts."
                exit 1
            fi
            echo "  Retry $count/$MAX_RETRIES..."
        fi
    fi
    sleep "$INTERVAL"
done
