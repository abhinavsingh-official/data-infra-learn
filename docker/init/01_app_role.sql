-- Local-run only: the FastAPI backend connects as this role, never as the
-- postgres superuser, even in local development. Per-session restricted
-- roles (ARCHITECTURE_DECISIONS.md §7) get created dynamically by the
-- Postgres-phase module later (Module 4) - this is just the one, fixed
-- role the app itself uses to manage schemas/tables.

CREATE ROLE app_role WITH LOGIN PASSWORD 'app_role_dev_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;

GRANT ALL ON SCHEMA public TO app_role;
