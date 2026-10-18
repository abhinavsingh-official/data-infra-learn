"""Rewards and repayments generator."""

import random
import uuid
from datetime import timedelta, timezone
from typing import Any

from faker import Faker

_fake = Faker()

_REWARD_TYPES = ["cashback", "points", "miles"]
_PAYMENT_METHODS = ["bank_transfer", "debit_card", "upi", "autopay", "check"]
_REPAYMENT_STATUSES = ["paid", "pending", "overdue", "partial"]


def generate_reward_events(
    account_ids: list[int], transaction_id_sample: list[int], target_count: int
) -> list[dict[str, Any]]:
    events = []
    for _ in range(target_count):
        # Promotional bonuses aren't tied to a specific transaction.
        transaction_id = random.choice(transaction_id_sample) if random.random() > 0.15 else None
        redeemed = random.random() < 0.4
        earned_at = _fake.date_time_between(start_date="-2y", end_date="now", tzinfo=timezone.utc)
        points = round(random.uniform(1, 500), 2)
        events.append(
            {
                "account_id": random.choice(account_ids),
                "transaction_id": transaction_id,
                "reward_type": random.choice(_REWARD_TYPES),
                "points_earned": points,
                "cash_value": round(points * 0.01, 2),
                "redeemed": redeemed,
                "redeemed_at": earned_at + timedelta(days=random.randint(1, 300)) if redeemed else None,
                "expiry_date": (earned_at + timedelta(days=730)).date(),
            }
        )
    return events


def generate_repayments(account_ids: list[int], target_count: int) -> list[dict[str, Any]]:
    repayments = []
    for _ in range(target_count):
        due_date = _fake.date_between(start_date="-2y", end_date="+30d")
        amount_due = round(random.uniform(50, 3000), 2)
        status = random.choices(_REPAYMENT_STATUSES, weights=[75, 10, 10, 5])[0]
        paid = status in ("paid", "partial")
        amount_paid = amount_due if status == "paid" else round(amount_due * random.uniform(0.1, 0.9), 2) if status == "partial" else 0.0
        repayments.append(
            {
                "account_id": random.choice(account_ids),
                "due_date": due_date,
                "amount_due": amount_due,
                "amount_paid": amount_paid,
                "payment_method": random.choice(_PAYMENT_METHODS),
                "payment_reference": uuid.uuid4().hex,
                "paid_at": _fake.date_time_between(start_date=due_date, end_date="+15d", tzinfo=timezone.utc) if paid else None,
                "late_fee": round(random.uniform(10, 100), 2) if status == "overdue" else 0.0,
                "status": status,
            }
        )
    return repayments
