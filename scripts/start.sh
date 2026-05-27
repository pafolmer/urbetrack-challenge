#!/usr/bin/env bash
set -euo pipefail

echo "Starting stack..."
docker compose up -d "$@"
echo "Stack running. Access API at http://localhost:8080"
