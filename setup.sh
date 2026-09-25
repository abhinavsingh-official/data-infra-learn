#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "Starting Postgres..."
docker compose --env-file .env -f docker/docker-compose.yml up -d

echo "Waiting for Postgres to be healthy..."
until docker compose --env-file .env -f docker/docker-compose.yml ps postgres --format '{{.Health}}' | grep -q healthy; do
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
echo "  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
