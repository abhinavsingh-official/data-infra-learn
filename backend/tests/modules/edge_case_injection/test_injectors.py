import random
from datetime import datetime, timedelta, timezone

from app.modules.edge_case_injection import injectors

BASE_PAYLOAD = {
    "event_id": "100000000001",
    "amount": "1234.56",
    "currency": "USD",
    "merchant": "Acme Corp",
    "card_last4": "0042",
    "channel": "POS",
    "timestamp": "2026-01-01T12:00:00+00:00",
}


def test_inject_null_removes_a_required_field_entirely():
    random.seed(1)
    triggered = False
    for _ in range(1000):
        payload, fault = injectors.inject_null(dict(BASE_PAYLOAD), rate=1.0)
        if fault:
            triggered = True
            assert fault["error_code"] == "ERR_NULL_REQUIRED_FIELD"
            assert len(payload) == len(BASE_PAYLOAD) - 1
    assert triggered


def test_duplicate_shares_event_id_but_new_delivery_id():
    random.seed(2)
    received_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = injectors.maybe_build_duplicate(BASE_PAYLOAD, received_at, rate=1.0)
    assert result is not None
    delivery_id, resend_received_at, fault = result
    assert delivery_id != BASE_PAYLOAD["event_id"]
    assert resend_received_at > received_at
    assert fault["error_code"] == "ERR_DUPLICATE_DELIVERY"


def test_late_arrival_exceeds_the_stated_watermark():
    random.seed(3)
    event_timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    received_at = event_timestamp + timedelta(hours=2)  # normal, on-time
    new_received_at, fault = injectors.inject_late_arrival(received_at, event_timestamp, rate=1.0)
    assert fault is not None
    assert (new_received_at - event_timestamp) > timedelta(hours=injectors.WATERMARK_HOURS)


def test_schema_drift_renamed_field_removes_old_key_adds_new():
    random.seed(4)
    for _ in range(200):
        payload, fault = injectors.inject_schema_drift(dict(BASE_PAYLOAD), rate=1.0)
        if fault and fault["fault_type"] == "schema_drift_renamed_field":
            assert "merchant" not in payload
            assert payload["merchant_name"] == BASE_PAYLOAD["merchant"]
            return
    raise AssertionError("renamed_field variant never occurred in 200 tries")


def test_schema_drift_type_change_converts_amount_to_integer_cents():
    random.seed(5)
    for _ in range(200):
        payload, fault = injectors.inject_schema_drift(dict(BASE_PAYLOAD), rate=1.0)
        if fault and fault["fault_type"] == "schema_drift_type_change":
            assert isinstance(payload["amount"], int)
            assert payload["amount"] == round(float(BASE_PAYLOAD["amount"]) * 100)
            return
    raise AssertionError("type_change variant never occurred in 200 tries")


def test_schema_drift_does_not_crash_when_null_already_removed_its_target_field():
    """Found by running at real scale (50k rows) - inject_null removing
    'merchant' or 'amount' first, then inject_schema_drift trying to
    rename/convert a field that's already gone, crashed with a KeyError.
    A small smoke test never hit this combination; this test forces it."""
    random.seed(8)
    payload_missing_merchant = {k: v for k, v in BASE_PAYLOAD.items() if k != "merchant"}
    payload_missing_amount = {k: v for k, v in BASE_PAYLOAD.items() if k != "amount"}
    for _ in range(500):
        injectors.inject_schema_drift(dict(payload_missing_merchant), rate=1.0)
        injectors.inject_schema_drift(dict(payload_missing_amount), rate=1.0)
    # no exception raised across 500 tries with each precondition missing


def test_malformed_excel_corruption_mangles_a_long_numeric_id():
    random.seed(6)
    for _ in range(200):
        payload, fault = injectors.inject_malformed(dict(BASE_PAYLOAD), rate=1.0)
        if fault and fault["fault_type"] == "malformed_excel_corruption" and "E+" in payload.get("event_id", ""):
            assert payload["event_id"] != BASE_PAYLOAD["event_id"]
            return
    raise AssertionError("excel-corrupted event_id variant never occurred in 200 tries")


def test_malformed_does_not_resurrect_a_field_null_already_removed():
    """Found on review, not by running: 'ambiguous_date' unconditionally
    overwrote 'timestamp' even if inject_null had already deleted it,
    which would make the fault log claim a field is both entirely missing
    and present-but-ambiguous for the same row - a contradiction the
    grader would later check against a lying answer key."""
    random.seed(9)
    payload_missing_timestamp = {k: v for k, v in BASE_PAYLOAD.items() if k != "timestamp"}
    for _ in range(500):
        payload, fault = injectors.inject_malformed(dict(payload_missing_timestamp), rate=1.0)
        if fault:
            assert fault["fault_type"] != "malformed_ambiguous_date"
            assert "timestamp" not in payload


def test_malformed_leading_zero_strip_only_fires_when_it_actually_changes_something():
    """Found on review: the old code chose this variant based on an
    always-true condition on a DIFFERENT field (event_id), then applied
    lstrip('0') to card_last4 regardless of whether it had a leading zero
    - silently no-op'ing on ~90% of values while still logging a fault
    that produced no visible change."""
    random.seed(10)
    payload_no_leading_zero = dict(BASE_PAYLOAD)
    payload_no_leading_zero["card_last4"] = "5300"  # doesn't start with 0
    for _ in range(500):
        payload, fault = injectors.inject_malformed(dict(payload_no_leading_zero), rate=1.0)
        if fault and fault["fault_type"] == "malformed_excel_corruption":
            assert payload["card_last4"] == "5300" or "E+" in payload["event_id"]  # only via the OTHER sub-variant

    payload_with_leading_zero = dict(BASE_PAYLOAD)
    payload_with_leading_zero["card_last4"] = "0042"
    saw_leading_zero_strip = False
    for _ in range(500):
        payload, fault = injectors.inject_malformed(dict(payload_with_leading_zero), rate=1.0)
        if fault and payload.get("card_last4") == "42":
            saw_leading_zero_strip = True
    assert saw_leading_zero_strip
