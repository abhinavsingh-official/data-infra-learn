"""Module 2 orchestrator: creates the schema, generates all five tables in
the right dependency order, and writes each batch via psycopg3's native
copy() - not executemany or row-by-row INSERT. See MODULE_2_PLAN.md for why."""

import time
from typing import Any, Sequence

from psycopg import Connection

from app.core.db import get_connection
from app.modules.data_generation import entities, rewards, schema, transactions

DEFAULT_COUNTS = {
    "users": 10_000,
    "accounts": 15_000,
    "transactions": 1_000_000,
    "reward_events": 200_000,
    "repayments": 150_000,
}
BATCH_SIZE = 25_000


def _copy_rows(conn: Connection, table: str, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    col_list = ", ".join(columns)
    with conn.cursor() as cur:
        with cur.copy(f"COPY {table} ({col_list}) FROM STDIN") as copy:
            for row in rows:
                copy.write_row(tuple(row[c] for c in columns))
    conn.commit()


def _insert_returning_ids(conn: Connection, table: str, rows: Sequence[dict[str, Any]]) -> list[int]:
    """Used only for tables whose generated IDs the next step needs
    (users -> accounts FK, accounts -> transactions FK). COPY doesn't
    support RETURNING, so these smaller tables use a batched INSERT
    instead - fine at this scale (tens of thousands of rows, not millions)."""
    if not rows:
        return []
    columns = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(columns)
    ids: list[int] = []
    with conn.cursor() as cur:
        for row in rows:
            cur.execute(
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) RETURNING id",
                tuple(row[c] for c in columns),
            )
            ids.append(cur.fetchone()[0])
    conn.commit()
    return ids


def run(counts: dict[str, int] | None = None) -> dict[str, Any]:
    counts = counts or DEFAULT_COUNTS
    timings: dict[str, float] = {}

    with get_connection() as conn:
        t0 = time.perf_counter()
        schema.create_schema(conn)
        timings["schema"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        users = entities.generate_users(counts["users"])
        user_ids = _insert_returning_ids(conn, "users", users)
        timings["users"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        accounts = entities.generate_accounts(user_ids, counts["accounts"])
        account_ids = _insert_returning_ids(conn, "accounts", accounts)
        timings["accounts"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        for batch in transactions.generate_transaction_batches(account_ids, counts["transactions"], BATCH_SIZE):
            _copy_rows(conn, "transactions", batch)
        timings["transactions"] = time.perf_counter() - t0

        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM transactions ORDER BY random() LIMIT %s",
                (min(50_000, counts["transactions"]),),
            )
            transaction_id_sample = [r[0] for r in cur.fetchall()]

        t0 = time.perf_counter()
        reward_rows = rewards.generate_reward_events(account_ids, transaction_id_sample, counts["reward_events"])
        _copy_rows(conn, "reward_events", reward_rows)
        timings["reward_events"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        repayment_rows = rewards.generate_repayments(account_ids, counts["repayments"])
        _copy_rows(conn, "repayments", repayment_rows)
        timings["repayments"] = time.perf_counter() - t0

    return {"counts": counts, "timings": timings}


if __name__ == "__main__":
    result = run()
    print(f"Generated: {result['counts']}")
    print(f"Timings (seconds): {result['timings']}")
    print(f"Total: {sum(result['timings'].values()):.2f}s")
