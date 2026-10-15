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

echo "Starting Postgres and MongoDB..."
docker compose --env-file .env -f docker/docker-compose.yml up -d

for service in postgres mongo; do
  echo "Waiting for ${service} to be healthy..."
  max_attempts=30
  attempt=0
  until docker compose --env-file .env -f docker/docker-compose.yml ps "$service" --format '{{.Health}}' | grep -q healthy; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge "$max_attempts" ]; then
      echo "${service} didn't become healthy after ${max_attempts}s. Check 'docker compose -f docker/docker-compose.yml logs ${service}'." >&2
      exit 1
    fi
    sleep 1
  done
done

if ! command -v java >/dev/null 2>&1; then
  echo "Java isn't installed - PySpark (Module 19, Warehouse/Lake/Lakehouse phases) needs a JRE/JDK." >&2
  echo "Install one, e.g.: brew install openjdk@17" >&2
  echo "Then set spark_java_home in .env to its install path if it's not auto-detected." >&2
  exit 1
fi

# PySpark 3.5.x doesn't support Python 3.13+ yet (its bundled cloudpickle
# can't serialize closures under the newer interpreter - confirmed by
# actually hitting this during Module 19, not assumed from a compat
# table). python3.12 specifically, not just "python3" - found via `brew
# install python@3.12` if this exact command isn't already on PATH.
PYTHON_BIN="python3.12"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python3.12 isn't on PATH - PySpark doesn't yet support newer Python versions." >&2
  echo "Install it, e.g.: brew install python@3.12" >&2
  exit 1
fi

if [ ! -d backend/.venv ]; then
  echo "Creating Python virtualenv (${PYTHON_BIN})..."
  "$PYTHON_BIN" -m venv backend/.venv
fi

echo "Installing backend dependencies..."
backend/.venv/bin/pip install --quiet --upgrade pip
backend/.venv/bin/pip install --quiet -r backend/requirements.txt

echo "Done. Run the backend with:"
echo "  cd backend && source .venv/bin/activate && python -m app.main"
