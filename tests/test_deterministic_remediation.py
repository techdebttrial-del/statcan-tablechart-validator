from pathlib import Path

from core.excel_inspector import ExcelInspector
from core.remediation_catalog import remediation_options


FIXTURES = Path(__file__).parent / "fixtures" / "test_cases"


def test_empty_cell_finding_retains_every_affected_cell():
    findings = ExcelInspector().inspect_workbook(str(FIXTURES / "t101_fail_all.xlsx"))
    finding = next(f for f in findings if f.rule_id == "T101-NO-EMPTY-CELLS")

    assert finding.affected_cells == ["C2", "C3"]
    assert "C2" in finding.location and "C3" in finding.location


def test_deterministic_catalog_has_bounded_choices_for_empty_cells():
    options = remediation_options("T101-NO-EMPTY-CELLS")
    ids = [option["id"] for option in options]

    assert ids == ["enter_value", "select_symbol", "leave_open"]
    assert all(option["input"] in {"text", "select", "none"} for option in options)


def test_catalog_is_defined_for_each_supported_finding_family():
    rule_ids = {
        "T101-NO-FORMULAS", "T101-NO-COLOR-FILL", "T101-NO-EMPTY-CELLS",
        "T101-INDENT-FEATURE", "T101-GRIDLINES-ON", "T101-SOURCE-PRESENT",
        "C101-NO-EMPTY-CELLS", "C101-NO-EXTRA-CALCULATIONS", "C101-SIZE-WIDTH",
        "C101-SIZE-HEIGHT-MIN", "C101-MAX-SIX-SERIES", "C101-SOURCE-PRESENT",
    }
    for rule_id in rule_ids:
        opts = remediation_options(rule_id)
        assert len(opts) >= 1, f"{rule_id} has no remediation options"
        assert all("label_en" in o and "label_fr" in o for o in opts), \
            f"{rule_id} options missing bilingual labels"
