import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.excel_inspector import ExcelInspector

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_workbook.xlsx")


def test_inspect_workbook_produces_findings():
    inspector = ExcelInspector()
    findings = inspector.inspect_workbook(FIXTURE, language="en")
    assert len(findings) > 0
    rule_ids = {f.rule_id for f in findings}
    assert "T101-NO-EMPTY-CELLS" in rule_ids
    assert "T101-NO-FORMULAS" in rule_ids


def test_findings_have_bilingual_titles():
    inspector = ExcelInspector()
    findings = inspector.inspect_workbook(FIXTURE, language="en")
    for f in findings:
        assert f.title_en
        assert f.title_fr
        assert f.description_en
        assert f.description_fr
