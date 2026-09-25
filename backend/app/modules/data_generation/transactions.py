"""Module 2.2: transaction generator, modeled on real ISO 8583 data
elements (see MODULE_2_PLAN.md) - not an invented schema."""

import itertools
import json
import random
from datetime import timedelta, timezone
from typing import Any, Iterator

from faker import Faker

_fake = Faker()

# processing_code (ISO 8583 field 3) per transaction type - a real subset,
# not the full standard.
_TYPE_TO_PROCESSING_CODE = {
    "purchase": "00",
    "withdrawal": "01",
    "refund": "20",
    "recurring": "00",
}
_CURRENCIES = ["USD", "INR", "EUR", "JPY", "GBP"]
_RESPONSE_CODES_WEIGHTED = [("00", 92), ("05", 3), ("51", 3), ("14", 1), ("91", 1)]
_MCC_POOL = ["5411", "5812", "5732", "4111", "5999", "5200", "7011", "4899"]

_rrn_counter = itertools.count(start=100_000_000_000)


def _next_rrn() -> str:
    """12-digit Retrieval Reference Number (ISO 8583 field 37) - a monotonic
    counter, not random, so uniqueness is guaranteed by construction rather
    than by hoping for no collisions."""
    return str(next(_rrn_counter))


def _stan() -> str:
    """System Trace Audit Number - real STANs cycle per-terminal per-day,
    not globally unique, so a random 6-digit value is realistic here."""
    return f"{random.randint(0, 999999):06d}"


def _response_code() -> str:
    codes, weights = zip(*_RESPONSE_CODES_WEIGHTED)
    return random.choices(codes, weights=weights)[0]


def generate_transaction_batches(
    account_ids: list[int], total_count: int, batch_size: int
) -> Iterator[list[dict[str, Any]]]:
    """Yields batches rather than one big list - 1M rows of this many
    fields shouldn't all sit in memory at once."""
    produced = 0
    while produced < total_count:
        this_batch = min(batch_size, total_count - produced)
        batch = []
        for _ in range(this_batch):
            # transaction_type and channel are correlated, not independent -
            # a "recurring" type IS a "recurring" channel, and vice versa.
            # Sampling them separately produced nonsense like a recurring
            # payment on a POS channel; caught by inspecting real output,
            # not assumed correct just because it ran without error.
            if random.random() < 0.10:
                txn_type = "recurring"
                channel = "recurring"
            else:
                txn_type = random.choices(["purchase", "withdrawal", "refund"], weights=[70, 10, 10])[0]
                channel = random.choices(["POS", "online", "ATM"], weights=[45, 35, 10])[0]
            is_international = random.random() < 0.08
            txn_time = _fake.date_time_between(start_date="-2y", end_date="now", tzinfo=timezone.utc)
            # Settlement lag - real, and reused conceptually by Module 3's
            # late-arriving-record edge case later.
            posted_time = txn_time + timedelta(hours=random.randint(0, 48))

            device_fp = None
            if channel == "online":
                device_fp = json.dumps(
                    {"browser": "Chrome/128.0", "os": random.choice(["Windows 11", "Android 14", "iOS 17"])}
                )

            geolocation = None
            if channel != "recurring":
                geolocation = json.dumps(
                    {"lat": round(random.uniform(-60, 60), 6), "lng": round(random.uniform(-180, 180), 6)}
                )

            batch.append(
                {
                    "retrieval_reference_number": _next_rrn(),
                    "system_trace_audit_number": _stan(),
                    "account_id": random.choice(account_ids),
                    "message_type_indicator": "0200",
                    "processing_code": _TYPE_TO_PROCESSING_CODE[txn_type],
                    "transaction_amount": round(random.uniform(1, 5000), 2),
                    "currency_code": random.choice(_CURRENCIES) if is_international else "USD",
                    "merchant_name": _fake.company(),
                    "merchant_category_code": random.choice(_MCC_POOL),
                    "terminal_id": _fake.bothify(text="TID#######").upper(),
                    "transaction_type": txn_type,
                    "response_code": _response_code(),
                    "transaction_timestamp": txn_time,
                    "posted_timestamp": posted_time,
                    "channel": channel,
                    "device_fingerprint": device_fp,
                    "geolocation": geolocation,
                    "is_international": is_international,
                    "notes": None if random.random() > 0.1 else _fake.sentence(nb_words=6),
                }
            )
        produced += this_batch
        yield batch
