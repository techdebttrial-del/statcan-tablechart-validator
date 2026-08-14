from pathlib import Path

from openpyxl import load_workbook

from core.excel_inspector import ExcelInspector
from core.remediation_applier import apply_remediation, resolve_affected_cells

FIXTURE = Path(__file__).parent / "fixtures" / "test_cases" / "t101_fail_all.xlsx"


def test_legacy_finding_locations_are_recovered_for_display():
    finding = next(f for f in ExcelInspector().inspect_workbook(str(FIXTURE)) if f.rule_id == "T101-NO-EMPTY-CELLS")
    finding.affected_cells = []
    assert resolve_affected_cells(str(FIXTURE), finding) == ["B2", "B3", "B5"]


def test_symbol_iteration_has_no_empty_data_cells(tmp_path):
    finding = next(f for f in ExcelInspector().inspect_workbook(str(FIXTURE)) if f.rule_id == "T101-NO-EMPTY-CELLS")
    target = tmp_path / "iteration.xlsx"
    result = apply_remediation(str(FIXTURE), str(target), finding, "select_symbol", "r", "B2")

    assert result.success
    remaining = [f for f in ExcelInspector().inspect_workbook(str(target)) if f.rule_id == "T101-NO-EMPTY-CELLS"]
    assert any("B3" in f.location and "B5" in f.location for f in remaining)
    ws = load_workbook(target)["Data"]
    assert ws["B2"].value == "r"
    assert ws["B3"].value is None
    assert ws["B5"].value is None


def test_gridline_iteration_is_revalidated(tmp_path):
    finding = next(f for f in ExcelInspector().inspect_workbook(str(FIXTURE)) if f.rule_id == "T101-GRIDLINES-ON")
    target = tmp_path / "iteration.xlsx"
    result = apply_remediation(str(FIXTURE), str(target), finding, "turn_on", None)

    assert result.success
    assert not any(f.rule_id == "T101-GRIDLINES-ON" and f.sheet_name == "Data" for f in ExcelInspector().inspect_workbook(str(target)))
    assert load_workbook(target)["Data"].sheet_view.showGridLines is True
