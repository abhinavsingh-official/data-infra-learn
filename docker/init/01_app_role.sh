#!/bin/bash
# Local-run only: the FastAPI backend connects as this role, never as the
# postgres superuser, even in local development. Per-session restricted
# roles (ARCHITECTURE_DECISIONS.md §7) get created dynamically by the
# Postgres-phase module later (Module 4) - this is just the one, fixed
# role the app itself uses to manage schemas/tables.
#
# Shell script, not a .sql file, specifically so the role's credentials
# come from POSTGRES_APP_USER/POSTGRES_APP_PASSWORD (set in docker-compose.yml
# from .env) rather than being hardcoded here - a hardcoded password here
# would silently drift from whatever the app is actually configured to use.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE "${POSTGRES_APP_USER}" WITH LOGIN PASSWORD '${POSTGRES_APP_PASSWORD}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    GRANT ALL ON SCHEMA public TO "${POSTGRES_APP_USER}";
EOSQL
