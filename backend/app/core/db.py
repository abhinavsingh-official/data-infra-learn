from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg import Connection
from pymongo import MongoClient

from app.core.config import get_settings


@contextmanager
def get_connection() -> Iterator[Connection]:
    settings = get_settings()
    conn = psycopg.connect(settings.postgres_dsn)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_admin_connection() -> Iterator[Connection]:
    """Superuser connection - only for provisioning (CREATE ROLE/SCHEMA),
    never regular request handling."""
    settings = get_settings()
    conn = psycopg.connect(settings.postgres_admin_dsn)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_mongo_admin_client() -> Iterator[MongoClient]:
    """Mongo's root user - provisioning, plus grading reads that need
    access a restricted session user doesn't have."""
    settings = get_settings()
    client: MongoClient = MongoClient(settings.mongo_admin_uri)
    try:
        yield client
    finally:
        client.close()
