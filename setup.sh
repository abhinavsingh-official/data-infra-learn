#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon isn't running. Start Docker Desktop (or your Docker daemon) and re-run this script." >&2
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "Starting Postgres..."
docker compose --env-file .env -f docker/docker-compose.yml up -d

echo "Waiting for Postgres to be healthy..."
max_attempts=30
attempt=0
until docker compose --env-file .env -f docker/docker-compose.yml ps postgres --format '{{.Health}}' | grep -q healthy; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Postgres didn't become healthy after ${max_attempts}s. Check 'docker compose -f docker/docker-compose.yml logs postgres'." >&2
    exit 1
  fi
  sleep 1
done

if [ ! -d backend/.venv ]; then
  echo "Creating Python virtualenv..."
  python3 -m venv backend/.venv
fi

echo "Installing backend dependencies..."
backend/.venv/bin/pip install --quiet --upgrade pip
backend/.venv/bin/pip install --quiet -r backend/requirements.txt

echo "Done. Run the backend with:"
echo "  cd backend && source .venv/bin/activate && python -m app.main"
