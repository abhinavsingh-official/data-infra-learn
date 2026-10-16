from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg import Connection
from pymongo import MongoClient

from app.core.config import get_settings


@contextmanager
def get_connection() -> Iterator[Connection]:
    """A raw psycopg connection, not an ORM session.

    Deliberate choice: this platform's core operation is executing and
    inspecting arbitrary SQL (data generation, grading, user submissions),
    not typical ORM-style CRUD - an ORM would add a layer to explain away
    rather than one that helps.
    """
    settings = get_settings()
    conn = psycopg.connect(settings.postgres_dsn)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_admin_connection() -> Iterator[Connection]:
    """Superuser connection - ONLY for session provisioning (creating/
    dropping per-session roles and schemas), never for regular request
    handling. The data-plane connection above stays maximally restricted,
    and this narrowly-used control-plane connection is what's allowed to
    do things app_role deliberately cannot (CREATE ROLE, CREATE SCHEMA for
    another role's ownership)."""
    settings = get_settings()
    conn = psycopg.connect(settings.postgres_admin_dsn)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_mongo_admin_client() -> Iterator[MongoClient]:
    """Mongo's own root user - provisioning only (creating/dropping
    per-session scoped users and databases), same two-tier split as the
    Postgres admin connection above. Never used to touch a session's own
    data directly except by the grader, which legitimately needs the
    answer key a session's own restricted user can't see."""
    settings = get_settings()
    client: MongoClient = MongoClient(settings.mongo_admin_uri)
    try:
        yield client
    finally:
        client.close()
