"""Baseline realistic variance - always on, low rate (~2-5%). This is
separate from deliberate edge-case/fault injection elsewhere in the
pipeline: this module answers "real fintech data is messy even with
zero pipeline faults", not "here are the graded edge cases"."""

import random

MESSY_RATE = 0.03


def _typo(text: str) -> str:
    """Genuine human data-entry mistakes - transposed, doubled, or missing
    letters - not just casing/whitespace. Treated as a distinct failure
    mode from formatting variance, so it gets its own function rather
    than being folded into messy_name's cosmetic variants."""
    if len(text) < 3:
        return text
    i = random.randint(0, len(text) - 2)
    kind = random.choice(["transpose", "double", "drop"])
    if kind == "transpose" and text[i] != " " and text[i + 1] != " ":
        return text[:i] + text[i + 1] + text[i] + text[i + 2 :]
    if kind == "double":
        return text[: i + 1] + text[i] + text[i + 1 :]
    return text[:i] + text[i + 1 :]


def messy_name(name: str) -> str:
    """Occasional casing variance, stray whitespace, or a genuine typo -
    as if manually typed and never double-checked."""
    if random.random() >= MESSY_RATE:
        return name
    variant = random.choice(["upper", "lower", "pad", "double_space", "typo"])
    if variant == "upper":
        return name.upper()
    if variant == "lower":
        return name.lower()
    if variant == "pad":
        return f"  {name}  "
    if variant == "typo":
        return _typo(name)
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
