# data-infra-learn

A data-engineering learning platform: one company's data (fintech / digital lending / credit-card-rewards style), built end-to-end across five storage paradigms — Postgres, MongoDB (NoSQL), a DuckDB-based data warehouse, a DuckDB-based data lake, and a DuckDB-based lakehouse — connected under one frontend. Real ETL edge cases are injected into the data and graded with remediation-first feedback (why it broke, how to fix it, and the tradeoffs between valid fixes).

Planning, architecture decisions, and the component/repo inventory live in the companion repo: [AbhinavSingh189/Portfolio-Upgrade](https://github.com/AbhinavSingh189/Portfolio-Upgrade) — see `PLAN.md`, `ARCHITECTURE_DECISIONS.md`, and `SYSTEM_SPEC.md` there for the full picture. This repo holds the actual code.

**Status:** All 12 modules of the original plan are done — all five storage paradigms working end-to-end behind a shared frontend, a cross-platform comparison view (`/compare`), and a Learn page (`/learn`) aggregating every phase's remediation content. A full five-pass codebase review is complete, and a comprehensive walkthrough PDF lives in the companion repo at `Portfolio-Upgrade/docs/data-infra-learn-documentation.pdf`.

## Running locally

**One command, from the repo root:**

```
./start.sh
```

This starts the databases (Docker), the backend, and the frontend - each only if it isn't already running - and prints the URLs once everything is healthy. Logs go to `logs/backend.log` and `logs/frontend.log`. Run `./stop.sh` to stop the backend/frontend (the databases are cheap to leave running; `./stop.sh --all` also stops them).

There's no single process underneath this - it's genuinely three separate things (two Docker containers, a Python process, a Node process), which `start.sh` just launches and health-checks in sequence for you. The manual, step-by-step version, if you want to run or watch any piece individually:

```
./setup.sh                                            # databases + Python venv
cd backend && source .venv/bin/activate && python -m app.main   # backend, foreground
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
