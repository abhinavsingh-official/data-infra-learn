import re
from pathlib import Path

from app.modules.lake_phase.remediation import REMEDIATION

_REPORT_PATH = Path(__file__).resolve().parents[3] / "app" / "modules" / "lake_phase" / "report.py"


def test_every_lake_specific_error_code_emitted_by_report_has_a_remediation_entry():
    source = _REPORT_PATH.read_text()
    codes_in_source = set(re.findall(r'_make_lake_finding\(\s*"([A-Z_]+)"', source))
    assert codes_in_source, "expected to find at least one _make_lake_finding call in report.py"
    assert codes_in_source <= REMEDIATION.keys()
    assert codes_in_source == REMEDIATION.keys()  # no orphaned remediation entries either


def test_every_remediation_entry_has_why_fix_and_tradeoffs():
    for code, entry in REMEDIATION.items():
        assert entry["why"], f"{code} missing why"
        assert entry["fix"], f"{code} missing fix"
        assert entry["fix_sql"], f"{code} missing fix_sql"
        assert entry["tradeoffs"], f"{code} missing tradeoffs"
