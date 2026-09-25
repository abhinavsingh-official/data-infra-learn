import random

from app.modules.data_generation.messiness import maybe_empty_or_none, messy_name


def test_messy_name_rate_matches_configured_rate():
    """Statistical, not exact - catches the class of bug where the rate
    silently drifts (e.g. from a bad condition), not single-run noise."""
    random.seed(42)
    n = 50_000
    changed = sum(1 for _ in range(n) if messy_name("John Smith") != "John Smith")
    rate = changed / n
    assert 0.02 < rate < 0.04


def test_maybe_empty_or_none_returns_all_three_distinct_states():
    random.seed(7)
    results = {maybe_empty_or_none("value") for _ in range(10_000)}
    assert "value" in results
    assert None in results
    assert "" in results
    assert "   " in results
