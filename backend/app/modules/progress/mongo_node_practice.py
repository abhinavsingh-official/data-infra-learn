"""Node-scoped grading for the MongoDB Databases track - the Mongo-shaped
sibling of node_practice.py (Postgres/SQL). Same contract (ephemeral,
provision -> run -> diff -> teardown, never raises), kept as its own
small module rather than folded into node_practice.py, same as
nosql_phase vs. postgres_phase: the isolation mechanism is a throwaway
Mongo database + scoped user (Mongo's own native per-database auth), not
a Postgres role+schema, so the provisioning code has nothing in common
with node_practice's beyond the overall shape.

A submitted "SQL" text field is actually a JSON Mongo command document
here (`{"find": ..., "filter": {...}}` / `{"aggregate": ..., "pipeline":
[...], "cursor": {}}`) - the frontend's generic textarea and CheckRequest
model are reused unchanged (see skill_tree.py's docstring); this module
is what parses that text back into a command dict before running it."""

import json
import math
import secrets
import string
from typing import Any

from pymongo import MongoClient
from pymongo.errors import OperationFailure

from app.core.db import get_mongo_admin_client
from app.core.session_ids import validate_session_id
from app.modules.nosql_phase.mongo_execution import execute_submission
from app.modules.progress.node_practice import find_skill_node

# Mongo's error code for "no such user" on a dropUser call.
_USER_NOT_FOUND = 11


def _db_name(check_id: str) -> str:
    return f"practice_{check_id}"


def _generate_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def _practice_collections(practice: dict) -> list[dict]:
    """Same single-vs-multi shorthand as node_practice._practice_tables,
    reading the identical dict keys (tables / table_name+example_rows) -
    see skill_tree.py's docstring on why these keys are shared verbatim
    rather than renamed for "documents"."""
    if "tables" in practice:
        return practice["tables"]
    table_name = practice.get("table_name", "accounts")
    return [{"name": table_name, "rows": practice["example_rows"]}]


def _provision_practice_db(admin_client: MongoClient, check_id: str, collections: list[dict]) -> str:
    validate_session_id(check_id)
    name = _db_name(check_id)
    password = _generate_password()
    admin_client[name].command(
        "createUser", name, pwd=password, roles=[{"role": "readWrite", "db": name}]
    )
    # Seeded via the admin client directly - the scoped user already has
    # readWrite on this exact database, so there's no access gap, and it
    # avoids opening a second (throwaway) connection just to insert.
    db = admin_client[name]
    for collection in collections:
        docs = [dict(doc) for doc in collection["rows"]]
        if docs:
            db[collection["name"]].insert_many(docs)
    return password


def _deprovision_practice_db(admin_client: MongoClient, check_id: str) -> None:
    validate_session_id(check_id)
    name = _db_name(check_id)
    try:
        admin_client[name].command("dropUser", name)
    except OperationFailure as e:
        if e.code != _USER_NOT_FOUND:
            raise
    admin_client.drop_database(name)


def _extract_docs(result: dict[str, Any]) -> list[dict] | None:
    """find and aggregate command replies share this exact shape - the
    documents to grade live in cursor.firstBatch. Any other command
    shape (insert/update acknowledgements, etc.) has nothing there to
    diff against expected_output_rows."""
    cursor = result.get("cursor")
    if isinstance(cursor, dict) and isinstance(cursor.get("firstBatch"), list):
        return cursor["firstBatch"]
    return None


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def _values_match(actual: Any, expected: Any) -> bool:
    actual, expected = _normalize(actual), _normalize(expected)
    if isinstance(actual, dict) and isinstance(expected, dict):
        return set(actual) == set(expected) and all(_values_match(actual[k], expected[k]) for k in expected)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(_values_match(a, e) for a, e in zip(actual, expected))
    if isinstance(actual, (int, float)) or isinstance(expected, (int, float)):
        try:
            return math.isclose(float(actual), float(expected), rel_tol=1e-6, abs_tol=1e-6)
        except (TypeError, ValueError):
            return actual == expected
    return actual == expected


def _doc_matches(actual_doc: dict, expected_doc: dict) -> bool:
    return set(actual_doc) == set(expected_doc) and all(
        _values_match(actual_doc[key], expected_doc[key]) for key in expected_doc
    )


def _docs_match(actual: list[dict], expected: list[dict]) -> tuple[bool, str | None]:
    if len(actual) != len(expected):
        return False, f"Expected {len(expected)} document(s), got {len(actual)}."
    remaining = list(expected)
    for doc in actual:
        match_index = next((i for i, exp in enumerate(remaining) if _doc_matches(doc, exp)), None)
        if match_index is None:
            return False, f"No expected document matches this output document: {doc}"
        remaining.pop(match_index)
    return True, None


def check_mongo_node_submission(paradigm: str, node_id: str, command_text: str) -> dict:
    node = find_skill_node(paradigm, node_id)
    if node is None or node.get("type") != "skill" or "practice" not in node:
        raise ValueError(f"No gradable practice node '{node_id}' for paradigm '{paradigm}'")

    practice = node["practice"]
    try:
        command = json.loads(command_text)
    except json.JSONDecodeError as e:
        return {
            "passed": False,
            "error_code": "ERR_INVALID_JSON",
            "error_message": f"Not valid JSON: {e}",
            "actual_rows": [],
            "expected_rows": practice["expected_output_rows"],
            "mismatch": None,
        }
    if not isinstance(command, dict):
        return {
            "passed": False,
            "error_code": "ERR_INVALID_JSON",
            "error_message": "A Mongo command must be a JSON object, e.g. {\"find\": ..., \"filter\": {...}}.",
            "actual_rows": [],
            "expected_rows": practice["expected_output_rows"],
            "mismatch": None,
        }

    check_id = secrets.token_hex(16)
    with get_mongo_admin_client() as admin_client:
        password = _provision_practice_db(admin_client, check_id, _practice_collections(practice))
    try:
        result = execute_submission(_db_name(check_id), password, command)
        if not result.success:
            return {
                "passed": False,
                "error_code": result.error_code,
                "error_message": result.error_message,
                "actual_rows": [],
                "expected_rows": practice["expected_output_rows"],
                "mismatch": None,
            }
        actual_docs = _extract_docs(result.result)
        if actual_docs is None:
            return {
                "passed": False,
                "error_code": "ERR_NOT_A_QUERY_COMMAND",
                "error_message": (
                    "This command didn't return a document batch to grade - submit a `find` or "
                    "`aggregate` command (grading reads its cursor.firstBatch)."
                ),
                "actual_rows": [],
                "expected_rows": practice["expected_output_rows"],
                "mismatch": None,
            }
        passed, mismatch = _docs_match(actual_docs, practice["expected_output_rows"])
        return {
            "passed": passed,
            "error_code": None,
            "error_message": None,
            "actual_rows": actual_docs,
            "expected_rows": practice["expected_output_rows"],
            "mismatch": mismatch,
        }
    finally:
        with get_mongo_admin_client() as admin_client:
            _deprovision_practice_db(admin_client, check_id)
