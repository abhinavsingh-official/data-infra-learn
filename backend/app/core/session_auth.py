"""Module 16: resolves an Auth.js database-session token to the real
user behind it. Auth.js's database strategy (Module 15's deliberate
choice over JWT) stores the session token in Postgres unencrypted - the
cookie's raw value *is* auth.sessions."sessionToken", so this is a plain
lookup, no JWE decryption needed. The frontend is responsible for
forwarding its own session-token cookie value to the backend (Module 17+
wiring); this module only does the lookup once it receives it."""

from dataclasses import dataclass

from app.core.db import get_connection


@dataclass
class CurrentUser:
    id: int
    name: str | None
    email: str | None


def resolve_user(session_token: str | None) -> CurrentUser | None:
    if not session_token:
        return None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT u.id, u.name, u.email '
                'FROM auth.sessions s JOIN auth.users u ON u.id = s."userId" '
                'WHERE s."sessionToken" = %s AND s.expires > now()',
                (session_token,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return CurrentUser(id=row[0], name=row[1], email=row[2])
