"""Core entity generator - users and accounts."""

import json
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Any

from faker import Faker

from app.modules.data_generation.messiness import maybe_empty_or_none, messy_name, messy_phone

# Multi-locale, not just en_US - real name diversity rather than hand-rolled
# unicode handling.
_LOCALES = ["en_US", "en_IN", "hi_IN", "ja_JP", "es_ES", "de_DE"]
_fake = Faker(_LOCALES)

_KYC_STATUSES = ["verified", "pending", "rejected"]
_CARD_NETWORKS = ["Visa", "Mastercard", "Amex", "RuPay"]
_ACCOUNT_STATUSES = ["active", "frozen", "closed", "delinquent"]
_BROWSERS = ["Chrome/128.0", "Safari/17.5", "Firefox/129.0", "Edge/127.0"]
_OS = ["Windows 11", "macOS 14", "Android 14", "iOS 17", "Ubuntu 24.04"]
_SCREEN_RES = ["1920x1080", "1366x768", "390x844", "412x915", "2560x1440"]


def _device_fingerprint() -> dict[str, Any]:
    return {
        "browser": random.choice(_BROWSERS),
        "os": random.choice(_OS),
        "screen_resolution": random.choice(_SCREEN_RES),
        "device_type": random.choice(["mobile", "desktop", "tablet"]),
        "fonts": random.sample(
            ["Arial", "Helvetica", "Times New Roman", "Verdana", "Roboto", "Noto Sans"], k=3
        ),
    }


def _feature_flags_bits() -> str:
    """16-bit dense flag set (is_premium, is_frozen, is_flagged_fraud,
    autopay_enabled, ...) as a native Postgres BIT(16)."""
    return "".join(random.choice("01") for _ in range(16))


def generate_users(n: int) -> list[dict[str, Any]]:
    users = []
    for _ in range(n):
        name = _fake.name()
        raw_phone = "".join(_fake.msisdn()[-10:])
        users.append(
            {
                "external_user_id": uuid.uuid4(),
                "full_name": messy_name(name),
                "email": _fake.email(),
                "phone_number": messy_phone(raw_phone),
                "date_of_birth": _fake.date_of_birth(minimum_age=21, maximum_age=70),
                "tax_id": _fake.bothify(text="?????####??").upper(),
                "address_line1": _fake.street_address(),
                "address_line2": maybe_empty_or_none(_fake.secondary_address()),
                "city": _fake.city(),
                "state": _fake.state(),
                "postal_code": _fake.postcode(),
                "country": _fake.country(),
                "kyc_status": random.choices(_KYC_STATUSES, weights=[85, 10, 5])[0],
                "kyc_document": os.urandom(2048),
                "risk_score": round(random.uniform(0, 100), 2),
                "device_fingerprint": json.dumps(_device_fingerprint()),
                "signup_ip": _fake.ipv4_public(),
                "created_at": _fake.date_time_between(start_date="-3y", end_date="now", tzinfo=timezone.utc),
                "is_active": random.random() > 0.05,
            }
        )
    return users


def generate_accounts(user_ids: list[int], target_count: int) -> list[dict[str, Any]]:
    """~1.5 accounts per user on average - some users have multiple cards."""
    accounts = []
    for _ in range(target_count):
        user_id = random.choice(user_ids)
        card_number = _fake.credit_card_number()
        credit_limit = round(random.uniform(500, 25000), 2)
        accounts.append(
            {
                "external_account_id": uuid.uuid4(),
                "user_id": user_id,
                "card_number_masked": f"**** **** **** {card_number[-4:]}",
                "card_number_token": uuid.uuid4().hex,
                "card_network": random.choice(_CARD_NETWORKS),
                "credit_limit": credit_limit,
                "current_balance": round(random.uniform(0, credit_limit), 2),
                "billing_cycle_day": random.randint(1, 28),
                "account_status": random.choices(_ACCOUNT_STATUSES, weights=[80, 5, 10, 5])[0],
                "feature_flags": _feature_flags_bits(),
                "opened_at": _fake.date_between(start_date="-3y", end_date="today"),
                "interest_rate": round(random.uniform(12.0, 36.0), 2),
            }
        )
    return accounts
