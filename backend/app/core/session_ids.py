"""Session-id validation, shared across every storage-phase module. This
is a security invariant, not phase-specific business logic -
duplicating it per module would risk the copies drifting (e.g. one
module's regex loosening without the others'), so it lives here once."""

import re

# Deliberately short of 64: Postgres silently truncates identifiers past
# 63 bytes, so any prefixed name (role_name, db_name, etc.) derived from
# a session_id must leave headroom for its own prefix. The longest
# prefix in use is "lakehouse_session_" (19 chars) - 40 hex chars plus
# that still stays under the 63-byte limit with 4 bytes to spare, but
# actual usage only ever needs 32 (secrets.token_hex(16)), which leaves
# a comfortable 12 bytes of real headroom against today's longest
# prefix. Re-check this margin before adding a phase whose prefix is
# longer than "lakehouse_session_".
SAFE_SESSION_ID = re.compile(r"^[a-f0-9]{16,40}$")


class UnsafeSessionId(ValueError):
    pass


def validate_session_id(session_id: str) -> None:
    """Defense in depth alongside parameterized identifiers - reject
    anything that isn't a plain hex token *before* it ever reaches a
    database identifier, rather than relying solely on quoting/escaping
    to make arbitrary input safe."""
    if not SAFE_SESSION_ID.match(session_id):
        raise UnsafeSessionId(f"session_id must be a 16-40 char lowercase hex token, got: {session_id!r}")
