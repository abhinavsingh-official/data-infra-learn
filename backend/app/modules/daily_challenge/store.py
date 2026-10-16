"""Module 21: Daily Challenge persistence - deliberately zero new tables.
Each track (SQL, Python) is recorded as a normal progress.node_completions
row under its own paradigm ("daily-sql" / "daily-python") with a
date-namespaced node_id (selection.daily_node_id) - this reuses
store.record_node_completion exactly as-is, which means XP, the shared
streak, and the existing node-count/streak/XP badge thresholds all already
work for the Daily Challenge with no schema change and no new logic."""

from datetime import date

from psycopg import Connection
from psycopg.rows import dict_row

from app.modules.daily_challenge.selection import daily_node_id
from app.modules.progress.store import record_node_completion

SQL_PARADIGM = "daily-sql"
PYTHON_PARADIGM = "daily-python"


def completed_count(conn: Connection, user_id: int, paradigm: str) -> int:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM progress.node_completions WHERE user_id = %s AND paradigm = %s",
            (user_id, paradigm),
        )
        return cur.fetchone()["n"]


def already_completed_today(conn: Connection, user_id: int, paradigm: str, problem_id: str, today: date) -> bool:
    node_id = daily_node_id(problem_id, today)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT 1 FROM progress.node_completions WHERE user_id = %s AND paradigm = %s AND node_id = %s",
            (user_id, paradigm, node_id),
        )
        return cur.fetchone() is not None


def record_daily_completion(conn: Connection, user_id: int, paradigm: str, problem_id: str, today: date) -> dict:
    node_id = daily_node_id(problem_id, today)
    return record_node_completion(conn, user_id, paradigm, node_id, node_type="skill")
