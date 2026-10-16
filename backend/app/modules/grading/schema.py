"""The structural contract for clean_transactions - see task_content.py's
required_output. Uses pandera's polars backend, not pandas."""

import pandera.polars as pa

CLEAN_TRANSACTIONS_SCHEMA = pa.DataFrameSchema(
    {
        "event_id": pa.Column(str, unique=True, nullable=False),
        "amount": pa.Column(float, pa.Check.greater_than(0), nullable=False),
        "merchant": pa.Column(str, nullable=True),
        "currency": pa.Column(str, nullable=True),
        "event_timestamp": pa.Column(nullable=True),
    },
    strict=False,  # extra columns the user added are fine - only these are required
)
