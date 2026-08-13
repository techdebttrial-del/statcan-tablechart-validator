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
    assert [ws[cell].value for cell in finding.affected_cells] == ["..", "..", ".."]


def test_apply_formula_replacement_is_deterministic(tmp_path):
    target = tmp_path / "iteration.xlsx"
    finding = next(f for f in ExcelInspector().inspect_workbook(str(FIXTURE)) if f.rule_id == "T101-NO-FORMULAS")

    result = apply_remediation(str(FIXTURE), str(target), finding, "replace_with_value", "42")

    assert result.success is True
    assert load_workbook(target, data_only=False)["Data"][finding.affected_cells[0]].value == 42


def test_unsupported_choice_does_not_write_output(tmp_path):
    target = tmp_path / "iteration.xlsx"
    finding = next(f for f in ExcelInspector().inspect_workbook(str(FIXTURE)) if f.rule_id == "T101-NO-EMPTY-CELLS")

    result = apply_remediation(str(FIXTURE), str(target), finding, "leave_open", None)

    assert result.success is False
    assert not target.exists()
