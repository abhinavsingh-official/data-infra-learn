from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg import Connection

from app.core.config import get_settings


@contextmanager
def get_connection() -> Iterator[Connection]:
    """A raw psycopg connection, not an ORM session.

    Deliberate choice: this platform's core operation is executing and
    inspecting arbitrary SQL (data generation, grading, user submissions),
    not typical ORM-style CRUD - an ORM would add a layer to explain away
    rather than one that helps. See CODE_STANDARDS.md on avoiding
    premature abstraction.
    """
    settings = get_settings()
    conn = psycopg.connect(settings.postgres_dsn)
    try:
        yield conn
    finally:
        conn.close()
