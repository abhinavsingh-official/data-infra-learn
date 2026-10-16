"""DDL for Auth.js's Postgres adapter tables (@auth/pg-adapter's own
documented schema - https://authjs.dev/getting-started/adapters/pg),
schema-qualified into `auth` rather than the adapter's default
unqualified names. Unqualified `accounts`/`sessions`/`users` would
collide directly with this project's own public.accounts/public.users
tables, which mean something completely different (fintech data, not
login sessions) - see docker/init/02_auth_role.sh for the role whose
search_path keeps the Next.js side's own unqualified queries resolving
into this schema."""

from psycopg import Connection

_DDL = """
CREATE TABLE IF NOT EXISTS auth.verification_token (
    identifier TEXT NOT NULL,
    expires TIMESTAMPTZ NOT NULL,
    token TEXT NOT NULL,
    PRIMARY KEY (identifier, token)
);

CREATE TABLE IF NOT EXISTS auth.users (
    id SERIAL,
    name VARCHAR(255),
    email VARCHAR(255),
    "emailVerified" TIMESTAMPTZ,
    image TEXT,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS auth.accounts (
    id SERIAL,
    "userId" INTEGER NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type VARCHAR(255) NOT NULL,
    provider VARCHAR(255) NOT NULL,
    "providerAccountId" VARCHAR(255) NOT NULL,
    refresh_token TEXT,
    access_token TEXT,
    expires_at BIGINT,
    id_token TEXT,
    scope TEXT,
    session_state TEXT,
    token_type TEXT,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS auth.sessions (
    id SERIAL,
    "userId" INTEGER NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    expires TIMESTAMPTZ NOT NULL,
    "sessionToken" VARCHAR(255) NOT NULL,
    PRIMARY KEY (id)
);
"""


def create_schema(conn: Connection) -> None:
    conn.execute(_DDL)
    conn.commit()


if __name__ == "__main__":
    # One-time setup - `python -m app.modules.auth.schema` - run once per
    # environment, not part of regular app startup.
    from app.core.db import get_admin_connection

    with get_admin_connection() as conn:
        create_schema(conn)
    print("auth schema created.")
