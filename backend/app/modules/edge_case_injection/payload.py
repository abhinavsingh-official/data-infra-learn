"""Renders a clean transaction (from the `transactions` table) into
the baseline raw webhook-style payload shape - before any fault is
injected. Amounts are represented as decimal strings at baseline
(a common simpler webhook convention); the schema-drift type-change
injector later switches some rows to integer-smallest-unit (cents/paise),
mirroring the real, well-known "forgot the amount is in cents" class of
integration bug."""

from datetime import datetime
from typing import Any


def to_baseline_payload(txn: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": txn["retrieval_reference_number"],
        "amount": str(txn["transaction_amount"]),
        "currency": txn["currency_code"],
        "merchant": txn["merchant_name"],
        "card_last4": txn["card_last4"],
        "channel": txn["channel"],
        "timestamp": txn["transaction_timestamp"].isoformat()
        if isinstance(txn["transaction_timestamp"], datetime)
        else txn["transaction_timestamp"],
    }


def baseline_received_at(txn: dict[str, Any]) -> datetime:
    """Normal (non-late) arrival: shortly after the event, matching
    the existing settlement-lag pattern (0-48h)."""
    posted = txn["posted_timestamp"]
    return posted if isinstance(posted, datetime) else datetime.fromisoformat(posted)
