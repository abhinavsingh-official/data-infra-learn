"""Module 16: node-scoped grading - runs a learner's single SQL
statement against a private, per-check copy of just that node's own
example rows (not the real 51,495-row shared feed), then diffs the
result against the node's recorded expected_output_rows. Reuses
postgres_phase's own role-isolation mechanics (session_provisioning's
pattern) and execute_submission directly rather than reinventing them -
the only real difference is this role's raw_transaction_events table is
a small private copy it owns, loaded with just this node's example rows,
instead of a GRANT onto the real shared table."""

import json
import math
import re
import secrets
import string
from datetime import datetime
from typing import Any

import psycopg
from psycopg import Connection, sql

from app.core.config import get_settings
from app.core.db import get_admin_connection
from app.core.session_ids import validate_session_id
from app.modules.postgres_phase.session_provisioning import STATEMENT_TIMEOUT
from app.modules.postgres_phase.skill_tree import POSTGRES_SKILL_TREE
from app.modules.postgres_phase.sql_execution import execute_submission

# Only Postgres has a skill tree so far (Module 14) - other paradigms join
# this registry in Module 20 when their own trees are built, not before.
_SKILL_TREES: dict[str, dict] = {"postgres": POSTGRES_SKILL_TREE}


def find_skill_node(paradigm: str, node_id: str) -> dict | None:
    tree = _SKILL_TREES.get(paradigm)
    if tree is None:
        return None
    for node in tree["nodes"]:
        if node["id"] == node_id:
            return node
    return None


def _role_name(check_id: str) -> str:
    return f"practice_{check_id}"


def _generate_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def _dsn(role: str, password: str) -> str:
    settings = get_settings()
    return f"postgresql://{role}:{password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"


def _provision_practice_role(conn: Connection, check_id: str, example_rows: list[dict]) -> str:
    validate_session_id(check_id)
    role = _role_name(check_id)
    password = _generate_password()

    conn.execute(
        sql.SQL("CREATE ROLE {role} WITH LOGIN PASSWORD {password} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
            role=sql.Identifier(role), password=sql.Literal(password)
        )
    )
    conn.execute(sql.SQL("CREATE SCHEMA {schema} AUTHORIZATION {role}").format(
        schema=sql.Identifier(role), role=sql.Identifier(role)
    ))
    conn.execute(sql.SQL("ALTER ROLE {role} SET search_path = {schema}").format(
        role=sql.Identifier(role), schema=sql.Identifier(role)
    ))
    conn.execute(sql.SQL("ALTER ROLE {role} SET statement_timeout = {timeout}").format(
        role=sql.Identifier(role), timeout=sql.Literal(STATEMENT_TIMEOUT)
    ))
    conn.commit()

    # Owned by the role itself (its own schema), so no GRANT is needed -
    # unlike the real session flow, which grants SELECT onto the one
    # shared public.raw_transaction_events table instead.
    with psycopg.connect(_dsn(role, password)) as practice_conn:
        practice_conn.execute(
            "CREATE TABLE raw_transaction_events "
            "(id bigint, received_at timestamptz, source_delivery_id text, payload jsonb)"
        )
        with practice_conn.cursor() as cur:
            for row in example_rows:
                cur.execute(
                    "INSERT INTO raw_transaction_events (id, received_at, source_delivery_id, payload) "
                    "VALUES (%s, %s, %s, %s)",
                    (row["id"], row["received_at"], row.get("source_delivery_id"), json.dumps(row["payload"])),
                )
        practice_conn.commit()

    return password


def _deprovision_practice_role(conn: Connection, check_id: str) -> None:
    validate_session_id(check_id)
    role = _role_name(check_id)
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
        role_exists = cur.fetchone() is not None
    if role_exists:
        conn.execute(sql.SQL("DROP OWNED BY {role} CASCADE").format(role=sql.Identifier(role)))
    conn.execute(sql.SQL("DROP ROLE IF EXISTS {role}").format(role=sql.Identifier(role)))
    conn.commit()


# Postgres renders a UTC (or any zero-minute) offset in its default text
# output as a short "+00" / "-05", not the full "+00:00" / "-05:00" ISO
# form - that's exactly the format the skill-tree content's
# expected_output_rows were captured in (by actually running the query,
# per this project's own verify-by-running standard). Python's
# datetime.fromisoformat needs the full form, so pad it before parsing.
_SHORT_OFFSET = re.compile(r"([+-]\d{2})$")


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}T", value):
        padded = _SHORT_OFFSET.sub(r"\1:00", value) if _SHORT_OFFSET.search(value) else value
        try:
            return datetime.fromisoformat(padded)
        except ValueError:
            return value
    return value


def _row_matches(actual_row: dict, expected_row: dict) -> bool:
    if set(actual_row) != set(expected_row):
        return False
    for key, expected_value in expected_row.items():
        actual_value = _normalize(actual_row[key])
        expected_value = _normalize(expected_value)
        if isinstance(actual_value, (int, float)) or isinstance(expected_value, (int, float)):
            try:
                if not math.isclose(float(actual_value), float(expected_value), rel_tol=1e-6, abs_tol=1e-6):
                    return False
            except (TypeError, ValueError):
                return False
        elif actual_value != expected_value:
            return False
    return True


def _rows_match(actual: list[dict], expected: list[dict]) -> tuple[bool, str | None]:
    if len(actual) != len(expected):
        return False, f"Expected {len(expected)} row(s), got {len(actual)}."
    remaining = list(expected)
    for row in actual:
        match_index = next((i for i, exp in enumerate(remaining) if _row_matches(row, exp)), None)
        if match_index is None:
            return False, f"No expected row matches this output row: {row}"
        remaining.pop(match_index)
    return True, None


def check_node_submission(paradigm: str, node_id: str, sql_text: str) -> dict:
    node = find_skill_node(paradigm, node_id)
    if node is None or node.get("type") != "skill" or "practice" not in node:
        raise ValueError(f"No gradable practice node '{node_id}' for paradigm '{paradigm}'")

    practice = node["practice"]
    check_id = secrets.token_hex(16)

    with get_admin_connection() as conn:
        password = _provision_practice_role(conn, check_id, practice["example_rows"])
    try:
        result = execute_submission(_role_name(check_id), password, sql_text)
        if not result.success:
            return {
                "passed": False,
                "error_code": result.error_code,
                "error_message": result.error_message,
                "actual_rows": [],
                "expected_rows": practice["expected_output_rows"],
                "mismatch": None,
            }
        actual_rows = [dict(zip(result.columns, row)) for row in result.rows]
        passed, mismatch = _rows_match(actual_rows, practice["expected_output_rows"])
        return {
            "passed": passed,
            "error_code": None,
            "error_message": None,
            "actual_rows": actual_rows,
            "expected_rows": practice["expected_output_rows"],
            "mismatch": mismatch,
        }
    finally:
        with get_admin_connection() as conn:
            _deprovision_practice_role(conn, check_id)
