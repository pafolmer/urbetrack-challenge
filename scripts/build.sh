#!/usr/bin/env bash
set -euo pipefail

echo "Building Docker images..."
docker compose build "$@"
echo "Build complete."
