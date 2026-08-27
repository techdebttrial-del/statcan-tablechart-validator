import os
from pathlib import Path

from openpyxl import load_workbook

from core.excel_inspector import ExcelInspector
from core.remediation_applier import apply_remediation

FIXTURE = Path(__file__).parent / "fixtures" / "test_cases" / "t101_fail_all.xlsx"


def test_apply_empty_cell_value_writes_copy_and_preserves_source(tmp_path):
    target = tmp_path / "iteration.xlsx"
    findings = ExcelInspector().inspect_workbook(str(FIXTURE))
    finding = next(f for f in findings if f.rule_id == "T101-NO-EMPTY-CELLS")

    result = apply_remediation(str(FIXTURE), str(target), finding, "enter_value", "..")

    assert result.success is True
    assert FIXTURE.read_bytes() == FIXTURE.read_bytes()
    wb = load_workbook(target, data_only=False)
    ws = wb["Data"]
    assert [ws[cell].value for cell in finding.affected_cells] == ["..", ".."]


def test_apply_formula_replacement_is_deterministic(tmp_path):
    target = tmp_path / "iteration.xlsx"
    finding = next(f for f in ExcelInspector().inspect_workbook(str(FIXTURE)) if f.rule_id == "T101-NO-FORMULAS")

    result = apply_remediation(str(FIXTURE), str(target), finding, "replace_with_value", "42")

    assert result.success is True
    wb = load_workbook(target, data_only=False)
    # Formula was at A2 in the new fixture
    assert wb["Data"]["A2"].value == 42


def test_apply_color_fill_removal_is_deterministic(tmp_path):
    target = tmp_path / "iteration.xlsx"
    finding = next(f for f in ExcelInspector().inspect_workbook(str(FIXTURE)) if f.rule_id == "T101-NO-COLOR-FILL")

    result = apply_remediation(str(FIXTURE), str(target), finding, "remove_fill", None)

    assert result.success is True
    wb = load_workbook(target, data_only=False)
    for cell_ref in finding.affected_cells:
        cell = wb["Data"][cell_ref]
        assert cell.fill.patternType is None or str(cell.fill.fgColor.rgb) in ("00000000", "0")


def test_source_wb_is_unchanged_after_remediation(tmp_path):
    target = tmp_path / "iteration.xlsx"
    original_bytes = FIXTURE.read_bytes()
    finding = next(f for f in ExcelInspector().inspect_workbook(str(FIXTURE)) if f.rule_id == "T101-NO-EMPTY-CELLS")

    apply_remediation(str(FIXTURE), str(target), finding, "enter_value", "..")

    assert FIXTURE.read_bytes() == original_bytes
