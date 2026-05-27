#!/usr/bin/env bash
set -euo pipefail

echo "Stopping stack..."
docker compose down "$@"
echo "Stack stopped."
