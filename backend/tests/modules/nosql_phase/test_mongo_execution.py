import secrets

from app.core.db import get_mongo_admin_client
from app.modules.nosql_phase.mongo_execution import MAX_RETURNED_DOCS, execute_submission
from app.modules.nosql_phase.session_provisioning import (
    deprovision_mongo_session,
    mongo_db_name,
    provision_mongo_session,
)


def _new_session():
    session_id = secrets.token_hex(16)
    with get_mongo_admin_client() as admin_client:
        password = provision_mongo_session(admin_client, session_id)
    return session_id, password


def test_execute_runs_insert_and_find_commands():
    session_id, password = _new_session()
    db_name = mongo_db_name(session_id)
    try:
        result = execute_submission(
            db_name, password, {"insert": "docs", "documents": [{"_id": "1"}, {"_id": "2"}]}
        )
        assert result.success is True
        assert result.result["n"] == 2

        result = execute_submission(db_name, password, {"find": "docs", "filter": {}})
        assert result.success is True
        assert len(result.result["cursor"]["firstBatch"]) == 2
    finally:
        with get_mongo_admin_client() as admin_client:
            deprovision_mongo_session(admin_client, session_id)


def test_execute_returns_structured_error_for_bad_command_not_a_crash():
    session_id, password = _new_session()
    db_name = mongo_db_name(session_id)
    try:
        result = execute_submission(db_name, password, {"thisIsNotARealCommand": 1})
        assert result.success is False
        assert result.error_code is not None
        assert result.error_message
    finally:
        with get_mongo_admin_client() as admin_client:
            deprovision_mongo_session(admin_client, session_id)


def test_execute_truncates_a_batch_size_the_caller_set_themselves():
    """Regression: Mongo's own default 101-document first batch does NOT
    apply once a caller sets batchSize explicitly - the same unbounded-
    result-set risk the Postgres phase guards against, reachable here
    through a different knob. execute_submission must cap it regardless
    of what the submitted command asked for."""
    session_id, password = _new_session()
    db_name = mongo_db_name(session_id)
    try:
        documents = [{"_id": str(i)} for i in range(MAX_RETURNED_DOCS + 500)]
        insert_result = execute_submission(db_name, password, {"insert": "docs", "documents": documents})
        assert insert_result.success is True

        result = execute_submission(
            db_name, password, {"find": "docs", "filter": {}, "batchSize": MAX_RETURNED_DOCS + 500}
        )
        assert result.success is True
        assert len(result.result["cursor"]["firstBatch"]) == MAX_RETURNED_DOCS
        assert result.truncated is True
    finally:
        with get_mongo_admin_client() as admin_client:
            deprovision_mongo_session(admin_client, session_id)
