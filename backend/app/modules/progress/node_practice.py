"""Module 16/18: node-scoped grading - runs a learner's single SQL
statement against a private, per-check copy of just that node's own
example rows (not a real shared dataset), then diffs the result against
the node's recorded expected_output_rows. Reuses postgres_phase's own
role-isolation mechanics (session_provisioning's pattern) and
execute_submission directly rather than reinventing them - the only real
difference is this role's own tables are small private copies it owns,
loaded with just this node's example rows, instead of a GRANT onto a
real shared table.

Module 18 generalized this from a single hardcoded raw_transaction_events
table (Module 16's original Postgres-only shape) to an arbitrary list of
tables, each driven entirely by its own `schema` list (column name + SQL
type) - needed for the new SQL Databases track's JOIN node, which needs
two small tables, not one. The schema list was already authored for
every node (originally just for UI display) and happens to describe
exactly the DDL needed, so this reuses it as the single source of truth
instead of maintaining a second, parallel column list."""

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
from app.modules.mongo_databases_track.skill_tree import MONGO_DATABASES_SKILL_TREE
from app.modules.postgres_phase.session_provisioning import STATEMENT_TIMEOUT
from app.modules.postgres_phase.skill_tree import POSTGRES_SKILL_TREE
from app.modules.postgres_phase.sql_execution import execute_submission
from app.modules.pipeline_architecture_track.skill_tree import PIPELINE_ARCHITECTURE_SKILL_TREE
from app.modules.sql_databases_track.skill_tree import SQL_DATABASES_SKILL_TREE
from app.modules.warehouse_databases_track.skill_tree import WAREHOUSE_DATABASES_SKILL_TREE

# Postgres (Module 14), SQL Databases (Module 18), MongoDB Databases, and
# Warehouse Databases (Module 20) have skill trees so far - the remaining
# paradigms join this registry as their own trees get built. Keyed by
# track slug, not literally "paradigm" anymore since Module 18 split SQL
# into two tracks under one umbrella - kept the param name for
# API-contract stability (POST /progress/nodes/{paradigm}/{node_id}/check),
# but it really means "track slug" today. Warehouse Databases runs through
# this same plain-Postgres engine despite the real warehouse_phase capstone
# running on Spark/Delta - the engine was never tied to the capstone's own
# engine (see sql_databases_track's own precedent against postgres_phase).
_SKILL_TREES: dict[str, dict] = {
    "postgres": POSTGRES_SKILL_TREE,
    "sql-databases": SQL_DATABASES_SKILL_TREE,
    "mongo-databases": MONGO_DATABASES_SKILL_TREE,
    "warehouse-databases": WAREHOUSE_DATABASES_SKILL_TREE,
    "pipeline-architecture": PIPELINE_ARCHITECTURE_SKILL_TREE,
}

# A submitted "sql" string means a raw JSON Mongo command document, not
# SQL text, for any track slug in this set - see mongo_node_practice.py.
# Kept here (next to _SKILL_TREES) since it's the same "which track is
# this" concern, just answered for a different reason.
MONGO_PARADIGMS: frozenset[str] = frozenset({"mongo-databases"})


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


def _practice_tables(practice: dict) -> list[dict]:
    """A practice block declares one or more tables. Module 16's original
    content only ever had one (always named raw_transaction_events) and
    never said so explicitly - `tables` lets new content (Module 18) name
    its own table(s) and have more than one, while this single-table
    fallback keeps every existing node working unchanged."""
    if "tables" in practice:
        return practice["tables"]
    table_name = practice.get("table_name", "raw_transaction_events")
    return [{"name": table_name, "schema": practice["schema"], "rows": practice["example_rows"]}]


def _provision_practice_role(conn: Connection, check_id: str, tables: list[dict]) -> str:
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
    # unlike the real session flow, which grants SELECT onto a real
    # shared table instead.
    with psycopg.connect(_dsn(role, password)) as practice_conn:
        for table in tables:
            columns = table["schema"]
            column_ddl = ", ".join(f'"{c["column"]}" {c["type"]}' for c in columns)
            practice_conn.execute(f'CREATE TABLE "{table["name"]}" ({column_ddl})')
            column_names = [c["column"] for c in columns]
            placeholders = ", ".join(["%s"] * len(column_names))
            quoted_names = ", ".join(f'"{name}"' for name in column_names)
            with practice_conn.cursor() as cur:
                for row in table["rows"]:
                    values = tuple(
                        json.dumps(row[name]) if isinstance(row.get(name), (dict, list)) else row.get(name)
                        for name in column_names
                    )
                    cur.execute(f'INSERT INTO "{table["name"]}" ({quoted_names}) VALUES ({placeholders})', values)
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
    return check_practice_submission(node["practice"], sql_text)


def check_practice_submission(practice: dict, sql_text: str) -> dict:
    """The actual provision -> run -> diff -> teardown grading logic,
    factored out of check_node_submission so a caller with a practice
    block that isn't a static skill-tree node lookup (the Daily
    Challenge's date-rotated problems, Module 21) can reuse it directly
    without inventing a parallel grading path."""
    check_id = secrets.token_hex(16)

    with get_admin_connection() as conn:
        password = _provision_practice_role(conn, check_id, _practice_tables(practice))
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
