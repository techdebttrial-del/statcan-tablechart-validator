from pathlib import Path

from core.excel_inspector import ExcelInspector
from core.remediation_catalog import remediation_options


FIXTURES = Path(__file__).parent / "fixtures" / "test_cases"


def test_empty_cell_finding_retains_every_affected_cell():
    findings = ExcelInspector().inspect_workbook(str(FIXTURES / "t101_fail_all.xlsx"))
    finding = next(f for f in findings if f.rule_id == "T101-NO-EMPTY-CELLS")

    assert finding.affected_cells == ["B2", "B3", "B5"]
    assert "B2" in finding.location and "B3" in finding.location and "B5" in finding.location


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
    assert rule_ids <= {rule_id for rule_id in remediation_options.registry()}


def test_app_renders_remediation_catalog_without_llm_dependency():
    source = (Path(__file__).parents[1] / "app" / "main.py").read_text()
    assert "remediation_options(f.rule_id)" in source
    assert "st.text_input" in source
    assert "st.selectbox" in source
    assert "suggest_fixes" not in source.split("remediation_options(f.rule_id)", 1)[0]
