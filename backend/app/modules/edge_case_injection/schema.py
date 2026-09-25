"""DDL for the raw staging layer (Module 3). See MODULE_3_PLAN.md for why
this is a separate JSONB staging table rather than corrupting the
already-typed clean tables from Module 2."""

from psycopg import Connection

_DDL = """
CREATE TABLE IF NOT EXISTS raw_transaction_events (
    id BIGSERIAL PRIMARY KEY,
    received_at TIMESTAMPTZ NOT NULL,
    source_delivery_id TEXT NOT NULL,
    payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS injected_fault_log (
    id BIGSERIAL PRIMARY KEY,
    raw_event_id BIGINT NOT NULL REFERENCES raw_transaction_events(id),
    fault_type TEXT NOT NULL,
    error_code TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fault_log_raw_event_id ON injected_fault_log(raw_event_id);
"""


def create_schema(conn: Connection) -> None:
    conn.execute(_DDL)
    conn.commit()


def drop_schema(conn: Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS injected_fault_log, raw_transaction_events CASCADE")
    conn.commit()
