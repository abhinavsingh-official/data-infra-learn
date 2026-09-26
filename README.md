# data-infra-learn

A data-engineering learning platform: one company's data (fintech / digital lending / credit-card-rewards style), built end-to-end across five storage paradigms — Postgres, MongoDB (NoSQL), a DuckDB-based data warehouse, a DuckDB-based data lake, and a DuckDB-based lakehouse — connected under one frontend. Real ETL edge cases are injected into the data and graded with remediation-first feedback (why it broke, how to fix it, and the tradeoffs between valid fixes).

Planning, architecture decisions, and the component/repo inventory live in the companion repo: [AbhinavSingh189/Portfolio-Upgrade](https://github.com/AbhinavSingh189/Portfolio-Upgrade) — see `PLAN.md`, `ARCHITECTURE_DECISIONS.md`, and `SYSTEM_SPEC.md` there for the full picture. This repo holds the actual code.

**Status:** Modules 1-10 done — Postgres, NoSQL (MongoDB), Warehouse (DuckDB, SCD Type 2), Data Lake (DuckDB, partitioned Parquet, schema-on-read), and Lakehouse (real Delta table via `deltalake`, incremental commits, ACID/time travel) phases all working end-to-end behind a shared frontend. Module 11 (Cross-platform comparison view) is next.

## Running locally

Backend + database:

```
./setup.sh
cd backend && source .venv/bin/activate && python -m app.main
```

Then `curl http://localhost:8000/health` should return `{"status":"ok","database":"reachable"}`. Host/port come from `.env` (`API_PORT`), not hardcoded.

Note: Postgres runs on host port **5433**, not 5432 — deliberately, to avoid colliding with a native/Homebrew Postgres install that might already be running on the default port. MongoDB runs on the default **27017**.

Frontend (separate terminal, with the backend already running):

```
cd frontend
npm install
npm run dev
```

Then open `http://localhost:3000`. It talks to the backend at `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000` - see `frontend/.env.local.example`).
