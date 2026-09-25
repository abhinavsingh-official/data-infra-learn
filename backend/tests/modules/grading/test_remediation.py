import re
from pathlib import Path

from app.modules.grading.remediation import REMEDIATION

_INJECTORS_PATH = Path(__file__).resolve().parents[3] / "app" / "modules" / "edge_case_injection" / "injectors.py"


def test_every_error_code_module_3_actually_produces_has_remediation():
    """Cross-checks against the real injectors.py rather than a hardcoded
    duplicate list, so this can't silently drift out of sync with Module 3."""
    injectors_source = _INJECTORS_PATH.read_text()
    error_codes_in_use = set(re.findall(r'"(ERR_[A-Z_]+)"', injectors_source))
    assert error_codes_in_use, "regex found nothing - check injectors.py still matches this pattern"
    for code in error_codes_in_use:
        assert code in REMEDIATION, f"{code} is injected by Module 3 but has no remediation entry"


def test_every_remediation_entry_has_why_fix_and_tradeoffs():
    for code, entry in REMEDIATION.items():
        for key in ("why", "fix", "tradeoffs"):
            assert entry.get(key), f"{code} is missing '{key}'"
