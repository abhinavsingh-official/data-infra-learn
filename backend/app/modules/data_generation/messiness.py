"""Baseline realistic variance - always on, low rate (~2-5%). This is NOT
Module 3's deliberate edge-case injection; see MODULE_2_PLAN.md for the
distinction. This module answers "real fintech data is messy even with
zero pipeline faults", not "here are the graded edge cases"."""

import random

MESSY_RATE = 0.03


def messy_name(name: str) -> str:
    """Occasional casing variance / stray whitespace, as if manually typed."""
    if random.random() >= MESSY_RATE:
        return name
    variant = random.choice(["upper", "lower", "pad", "double_space"])
    if variant == "upper":
        return name.upper()
    if variant == "lower":
        return name.lower()
    if variant == "pad":
        return f"  {name}  "
    return name.replace(" ", "  ", 1)


def messy_phone(raw_digits: str) -> str:
    """Real phone numbers arrive in inconsistent formats depending on how
    they were entered - with/without country code, dashes, spaces, parens."""
    fmt = random.choice(["plain", "dashed", "spaced", "parens", "intl"])
    if fmt == "plain":
        return raw_digits
    if fmt == "dashed":
        return f"{raw_digits[:3]}-{raw_digits[3:6]}-{raw_digits[6:]}"
    if fmt == "spaced":
        return f"{raw_digits[:3]} {raw_digits[3:6]} {raw_digits[6:]}"
    if fmt == "parens":
        return f"({raw_digits[:3]}) {raw_digits[3:6]}-{raw_digits[6:]}"
    return f"+1{raw_digits}"


def maybe_empty_or_none(value: str) -> str | None:
    """Optional free-text fields are sometimes NULL, sometimes an empty
    string, sometimes just whitespace - three genuinely different real
    states, not interchangeable."""
    roll = random.random()
    if roll < MESSY_RATE / 3:
        return None
    if roll < (MESSY_RATE / 3) * 2:
        return ""
    if roll < MESSY_RATE:
        return "   "
    return value
