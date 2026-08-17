from pathlib import Path

from core.excel_inspector import ExcelInspector


FIXTURES = Path(__file__).parent / "fixtures" / "test_cases"


def test_table_findings_include_actionable_cell_or_header_locations():
    findings = ExcelInspector().inspect_workbook(str(FIXTURES / "t101_fail_all.xlsx"))
    by_rule = {f.rule_id: f.location for f in findings}

    assert "A3" in by_rule["T101-NO-FORMULAS"]
    assert "B2" in by_rule["T101-NO-EMPTY-CELLS"]
    assert "A2" in by_rule["T101-INDENT-FEATURE"]
    assert "footer" in by_rule["T101-SOURCE-PRESENT"]


def test_deterministic_remediation_is_substituted_for_llm_suggestions():
    # The LLM suggestion path was removed outright — findings are exclusively
    # resolved through deterministic remediation options in the UI.
    source = (Path(__file__).parents[1] / "app" / "main.py").read_text()
    assert "remediation_options(f.rule_id)" in source
    assert "suggest_fixes" not in source
    assert "mode_mgr" not in source


def test_chart_findings_identify_chart_anchor_and_data_context():
    findings = ExcelInspector().inspect_workbook(str(FIXTURES / "c101_fail_all.xlsx"))
    by_rule = {f.rule_id: f.location for f in findings}

    assert "chart" in by_rule["C101-SIZE-WIDTH"]
    assert "anchor" in by_rule["C101-SIZE-WIDTH"]
    assert "series" in by_rule["C101-MAX-SIX-SERIES"]
    assert "footer" in by_rule["C101-SOURCE-PRESENT"]
