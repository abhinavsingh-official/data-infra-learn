#!/usr/bin/env bash
# One-command local start: databases (Docker) + backend (FastAPI) + frontend
# (Next.js), all in the background, logging to logs/. Run ./stop.sh to tear
# everything back down. Safe to re-run - setup.sh is itself idempotent, and
# this script refuses to double-start a piece that's already running.
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p logs
API_PORT="$(grep -m1 '^API_PORT=' .env 2>/dev/null | cut -d= -f2)"
API_PORT="${API_PORT:-8000}"

echo "==> Databases (Postgres + MongoDB)"
./setup.sh

echo "==> Backend (FastAPI, port ${API_PORT})"
if curl -s -m 2 "http://localhost:${API_PORT}/health" >/dev/null 2>&1; then
  echo "    already running."
else
  (cd backend && nohup .venv/bin/python -m app.main > ../logs/backend.log 2>&1 &)
  for _ in $(seq 1 30); do
    curl -s -m 2 "http://localhost:${API_PORT}/health" >/dev/null 2>&1 && break
    sleep 1
  done
  if ! curl -s -m 2 "http://localhost:${API_PORT}/health" >/dev/null 2>&1; then
    echo "    Backend didn't come up - check logs/backend.log" >&2
    exit 1
  fi
  echo "    started - logs/backend.log"
fi

echo "==> Frontend (Next.js, port 3000)"
if curl -s -m 2 -o /dev/null http://localhost:3000/ 2>&1; then
  echo "    already running."
else
  if [ ! -d frontend/node_modules ]; then
    echo "    Installing frontend dependencies (first run only)..."
    (cd frontend && npm install --silent)
  fi
  (cd frontend && nohup npm run dev > ../logs/frontend.log 2>&1 &)
  for _ in $(seq 1 30); do
    curl -s -m 2 -o /dev/null http://localhost:3000/ 2>&1 && break
    sleep 1
  done
  echo "    started - logs/frontend.log"
fi

echo ""
echo "Ready:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:${API_PORT}/health"
echo ""
echo "Run ./stop.sh to stop the backend/frontend (databases keep running - see stop.sh --all)."
