#!/usr/bin/env bash
set -euo pipefail

# Desarrollo local con hot-reload:
# - Monta app/ como volumen (cambios reflejados instantáneamente)
# - Uvicorn con --reload detecta cambios y reinicia el proceso Python
# - No necesita rebuild de imagen para cambios en código

echo "Starting dev environment with hot-reload..."
echo "API available at http://localhost:8080"
echo "Swagger docs at http://localhost:8080/docs"
echo "Press Ctrl+C to stop."

docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build "$@"
