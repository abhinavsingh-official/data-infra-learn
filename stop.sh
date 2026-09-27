#!/usr/bin/env bash
# Stops the backend and frontend processes started by start.sh. Databases
# keep running by default (they're cheap to leave up - see docker-compose.yml's
# resource limits); pass --all to also stop the Postgres/MongoDB containers.
set -euo pipefail
cd "$(dirname "$0")"

pkill -f "app.main" 2>/dev/null && echo "Stopped backend." || echo "Backend wasn't running."
pkill -f "next dev" 2>/dev/null && echo "Stopped frontend." || echo "Frontend wasn't running."

if [ "${1:-}" = "--all" ]; then
  echo "Stopping databases too..."
  docker compose --env-file .env -f docker/docker-compose.yml down
fi
