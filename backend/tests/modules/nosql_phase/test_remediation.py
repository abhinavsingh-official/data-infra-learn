import re
from pathlib import Path

from app.modules.nosql_phase.remediation import REMEDIATION

_REPORT_PATH = Path(__file__).resolve().parents[3] / "app" / "modules" / "nosql_phase" / "report.py"


def test_every_error_code_emitted_by_report_has_a_remediation_entry():
    """Cross-checks against report.py's real source, not a hardcoded
    duplicate list - the same pattern as grading/test_remediation.py, for
    the same reason: a partial mapping (only the first-thought-of case
    handled) is worse than none."""
    source = _REPORT_PATH.read_text()
    codes_in_source = set(re.findall(r'_make_finding\(\s*"([A-Z_]+)"', source))
    assert codes_in_source, "expected to find at least one _make_finding call in report.py"
    assert codes_in_source <= REMEDIATION.keys()


def test_every_remediation_entry_has_why_fix_and_tradeoffs():
    for code, entry in REMEDIATION.items():
        assert entry["why"], f"{code} missing why"
        assert entry["fix"], f"{code} missing fix"
        assert entry["fix_sql"], f"{code} missing fix_sql"
        assert entry["tradeoffs"], f"{code} missing tradeoffs"
