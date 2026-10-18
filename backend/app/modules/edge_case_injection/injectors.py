"""The five fault injectors. Each is a pure function so it's independently
testable. Error codes follow an RFC 9457-inspired convention:
ERR_<CATEGORY>_<SPECIFIC>, not ad hoc naming."""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any

FaultRecord = dict[str, str]

WATERMARK_HOURS = 48


def inject_null(payload: dict[str, Any], rate: float) -> tuple[dict[str, Any], FaultRecord | None]:
    """A required field missing entirely from the payload."""
    if random.random() >= rate:
        return payload, None
    field = random.choice(["amount", "merchant", "currency", "timestamp"])
    mutated = dict(payload)
    del mutated[field]
    return mutated, {
        "fault_type": "null_required_field",
        "error_code": "ERR_NULL_REQUIRED_FIELD",
        "description": f"Required field '{field}' is missing from the payload entirely.",
    }


def maybe_build_duplicate(
    payload: dict[str, Any], received_at: datetime, rate: float
) -> tuple[str, datetime, FaultRecord] | None:
    """A webhook resend: same event_id, new delivery ID, arrives shortly
    after the original. Returns the new delivery_id/received_at for a
    second row the caller appends, or None."""
    if random.random() >= rate:
        return None
    resend_delivery_id = uuid.uuid4().hex
    resend_received_at = received_at + timedelta(seconds=random.randint(5, 600))
    return (
        resend_delivery_id,
        resend_received_at,
        {
            "fault_type": "duplicate_delivery",
            "error_code": "ERR_DUPLICATE_DELIVERY",
            "description": (
                f"Same event_id '{payload['event_id']}' redelivered with a new delivery ID "
                "- a real at-least-once retry, not a byte-identical duplicate."
            ),
        },
    )


def inject_late_arrival(
    received_at: datetime, event_timestamp: datetime, rate: float
) -> tuple[datetime, FaultRecord | None]:
    """received_at set past the 48h watermark relative to the event's
    own timestamp."""
    if random.random() >= rate:
        return received_at, None
    late_by_hours = WATERMARK_HOURS + random.randint(1, 240)
    late_received_at = event_timestamp + timedelta(hours=late_by_hours)
    return late_received_at, {
        "fault_type": "late_arrival",
        "error_code": "ERR_LATE_ARRIVAL",
        "description": (
            f"Arrived {late_by_hours}h after its event timestamp, past the {WATERMARK_HOURS}h watermark."
        ),
    }


def inject_schema_drift(payload: dict[str, Any], rate: float) -> tuple[dict[str, Any], FaultRecord | None]:
    """Added field, renamed field, or type change. Skips a variant if
    inject_null already removed that field, instead of crashing - a real
    collision at 50k rows, not just a theoretical edge case."""
    if random.random() >= rate:
        return payload, None
    mutated = dict(payload)
    available_variants = ["added_field"]
    if "merchant" in mutated:
        available_variants.append("renamed_field")
    if "amount" in mutated:
        available_variants.append("type_change")
    variant = random.choice(available_variants)
    if variant == "added_field":
        mutated["risk_flag"] = random.choice(["low", "medium", "high"])
        return mutated, {
            "fault_type": "schema_drift_added_field",
            "error_code": "ERR_SCHEMA_DRIFT_ADDED_FIELD",
            "description": "Payload includes a new 'risk_flag' field not present in earlier events.",
        }
    if variant == "renamed_field":
        mutated["merchant_name"] = mutated.pop("merchant")
        return mutated, {
            "fault_type": "schema_drift_renamed_field",
            "error_code": "ERR_SCHEMA_DRIFT_RENAMED_FIELD",
            "description": "'merchant' was renamed to 'merchant_name' - a consumer still reading 'merchant' sees it as deleted.",
        }
    # type_change: amount as a decimal string -> integer cents/paise, the
    # classic "forgot the amount is in the smallest unit" bug.
    cents = round(float(mutated["amount"]) * 100)
    mutated["amount"] = cents
    return mutated, {
        "fault_type": "schema_drift_type_change",
        "error_code": "ERR_SCHEMA_DRIFT_TYPE_CHANGE",
        "description": f"'amount' changed from a decimal string to an integer in the smallest currency unit ({cents}).",
    }


def inject_malformed(payload: dict[str, Any], rate: float) -> tuple[dict[str, Any], FaultRecord | None]:
    """Excel-style ID corruption, or an ambiguous regional date string.

    'ambiguous_date' only runs if 'timestamp' still exists - otherwise it
    silently re-adds a field inject_null already deleted. The
    event_id/card_last4 choice is precondition-checked rather than an
    if/else that was always true for event_id - card_last4 used to be
    dead code that logged a fault with no actual change."""
    if random.random() >= rate:
        return payload, None
    mutated = dict(payload)
    available_variants = []
    if "event_id" in mutated and mutated["event_id"].isdigit() and len(mutated["event_id"]) >= 10:
        available_variants.append("scientific_notation")
    if "card_last4" in mutated and mutated["card_last4"].startswith("0"):
        available_variants.append("leading_zero_strip")
    if "timestamp" in mutated:
        available_variants.append("ambiguous_date")
    if not available_variants:
        return payload, None
    variant = random.choice(available_variants)
    if variant == "scientific_notation":
        raw_id = mutated["event_id"]
        mutated["event_id"] = f"{float(raw_id[:3]):.0f}E+{len(raw_id) - 3}"
        return mutated, {
            "fault_type": "malformed_excel_corruption",
            "error_code": "ERR_MALFORMED_EXCEL_CORRUPTION",
            "description": "A long numeric ID was corrupted into scientific notation, the way Excel corrupts long numeric IDs opened from a CSV.",
        }
    if variant == "leading_zero_strip":
        mutated["card_last4"] = mutated["card_last4"].lstrip("0") or "0"
        return mutated, {
            "fault_type": "malformed_excel_corruption",
            "error_code": "ERR_MALFORMED_EXCEL_CORRUPTION",
            "description": "A leading zero was stripped from an ID-like field, the way Excel strips leading zeros from numeric-looking text.",
        }
    day, month, year = random.randint(1, 12), random.randint(1, 12), 2025
    mutated["timestamp"] = f"{day:02d}/{month:02d}/{year}"
    return mutated, {
        "fault_type": "malformed_ambiguous_date",
        "error_code": "ERR_MALFORMED_AMBIGUOUS_DATE",
        "description": f"'timestamp' is an ambiguous DD/MM vs MM/DD string ('{mutated['timestamp']}'), not a proper ISO timestamp.",
    }
