#!/bin/bash
# Module 15: Auth.js's own role, kept deliberately separate from app_role.
# Scoped to its own `auth` schema, not `public` - Auth.js's adapter table
# names (accounts, sessions, users) would otherwise collide with this
# project's own public.accounts/public.users tables, which mean something
# completely different (fintech data, not login sessions). The role's own
# search_path is pinned to `auth` so the Next.js side's unqualified queries
# (SELECT * FROM accounts, etc.) resolve into the right schema automatically.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS auth;
    CREATE ROLE "${AUTH_DB_USER}" WITH LOGIN PASSWORD '${AUTH_DB_PASSWORD}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    ALTER ROLE "${AUTH_DB_USER}" SET search_path TO auth;
    GRANT ALL ON SCHEMA auth TO "${AUTH_DB_USER}";
    -- The tables themselves don't exist yet at this point (they're created
    -- later, once, by app/modules/auth/schema.py run as the superuser) - so
    -- table-level grants have to be deferred via ALTER DEFAULT PRIVILEGES
    -- rather than granted directly here.
    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA auth GRANT ALL ON TABLES TO "${AUTH_DB_USER}";
    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA auth GRANT ALL ON SEQUENCES TO "${AUTH_DB_USER}";
EOSQL
