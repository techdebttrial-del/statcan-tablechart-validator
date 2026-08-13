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


def test_llm_suggestions_are_not_called_during_default_finding_render():
    source = (Path(__file__).parents[1] / "app" / "main.py").read_text()
    guarded = "if st.session_state.llm_suggestions_enabled and mode_mgr.use_llm"
    assert guarded in source
    assert source.index(guarded) < source.index("fix_suggester.suggest_fixes(f)")


def test_chart_findings_identify_chart_anchor_and_data_context():
    findings = ExcelInspector().inspect_workbook(str(FIXTURES / "c101_fail_all.xlsx"))
    by_rule = {f.rule_id: f.location for f in findings}

    assert "chart" in by_rule["C101-SIZE-WIDTH"]
    assert "anchor" in by_rule["C101-SIZE-WIDTH"]
    assert "series" in by_rule["C101-MAX-SIX-SERIES"]
    assert "footer" in by_rule["C101-SOURCE-PRESENT"]
