"""Progress/XP/badge persistence - a `progress` Postgres schema,
parallel to `auth` and separate from the fintech simulation data in
`public`. Owned by app_role - the backend writes this
data itself, directly, unlike postgres_phase's per-session roles where
untrusted user SQL runs; no user-submitted SQL ever touches these
tables. Cross-schema foreign keys into auth.users since a user must
exist via real sign-in before they have any progress. Also grants
app_role read access to auth.sessions/auth.users, needed to resolve a
session token to a user id (see core/session_auth.py) - app_role never
had any reason to read the auth schema before this module."""

from psycopg import Connection

_DDL = """
CREATE SCHEMA IF NOT EXISTS progress;

CREATE TABLE IF NOT EXISTS progress.user_stats (
    user_id INTEGER PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    xp_total INTEGER NOT NULL DEFAULT 0,
    current_streak INTEGER NOT NULL DEFAULT 0,
    longest_streak INTEGER NOT NULL DEFAULT 0,
    last_activity_date DATE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS progress.node_completions (
    user_id INTEGER NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    paradigm TEXT NOT NULL,
    node_id TEXT NOT NULL,
    xp_awarded INTEGER NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, paradigm, node_id)
);

CREATE TABLE IF NOT EXISTS progress.badges (
    user_id INTEGER NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    badge_id TEXT NOT NULL,
    earned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, badge_id)
);

GRANT USAGE ON SCHEMA progress TO app_role;
GRANT ALL ON ALL TABLES IN SCHEMA progress TO app_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA progress GRANT ALL ON TABLES TO app_role;

GRANT USAGE ON SCHEMA auth TO app_role;
GRANT SELECT ON auth.users, auth.sessions TO app_role;
"""


def create_schema(conn: Connection) -> None:
    conn.execute(_DDL)
    conn.commit()


if __name__ == "__main__":
    from app.core.db import get_admin_connection

    with get_admin_connection() as conn:
        create_schema(conn)
    print("progress schema created.")
