import secrets

import psycopg
import pytest
from pymongo import MongoClient
from pymongo.errors import OperationFailure

from app.core.config import get_settings
from app.core.db import get_admin_connection, get_mongo_admin_client
from app.core.session_ids import UnsafeSessionId
from app.modules.nosql_phase.session_provisioning import (
    deprovision_mongo_session,
    deprovision_pg_readonly_session,
    mongo_db_name,
    pg_role_name,
    provision_mongo_session,
    provision_pg_readonly_session,
)


@pytest.mark.parametrize("bad_id", ["", "not-hex!", "short", "'; DROP TABLE users; --", "a" * 65])
def test_rejects_unsafe_session_ids_before_touching_anything(bad_id):
    with get_admin_connection() as pg_conn:
        with pytest.raises(UnsafeSessionId):
            provision_pg_readonly_session(pg_conn, bad_id)
    with get_mongo_admin_client() as mongo_client:
        with pytest.raises(UnsafeSessionId):
            provision_mongo_session(mongo_client, bad_id)


def test_mongo_session_is_isolated_to_its_own_database_then_cleaned_up():
    session_id = secrets.token_hex(16)
    settings = get_settings()
    with get_mongo_admin_client() as admin_client:
        password = provision_mongo_session(admin_client, session_id)

        name = mongo_db_name(session_id)
        session_client = MongoClient(
            f"mongodb://{name}:{password}@{settings.mongo_host}:{settings.mongo_port}/{name}?authSource={name}"
        )
        session_client[name]["some_collection"].insert_one({"x": 1})
        assert session_client[name]["some_collection"].count_documents({}) == 1

        with pytest.raises(OperationFailure):
            session_client["admin"]["x"].insert_one({"x": 1})
        session_client.close()

        deprovision_mongo_session(admin_client, session_id)
        assert name not in admin_client.list_database_names()


def test_pg_readonly_session_can_select_source_tables_but_not_write():
    session_id = secrets.token_hex(16)
    settings = get_settings()
    with get_admin_connection() as admin_conn:
        password = provision_pg_readonly_session(admin_conn, session_id)

        role = pg_role_name(session_id)
        dsn = f"postgresql://{role}:{password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM accounts")
                assert cur.fetchone()[0] > 0

            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM accounts")
            conn.rollback()

        deprovision_pg_readonly_session(admin_conn, session_id)
        with admin_conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            assert cur.fetchone() is None
