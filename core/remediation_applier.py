"""Apply approved deterministic remediation choices to a copied workbook."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from openpyxl import load_workbook

from core.models import Finding
from core.remediation_catalog import APPROVED_SYMBOLS
from core.excel_inspector import ExcelInspector


@dataclass
class RemediationResult:
    success: bool
    message: str
    output_path: Optional[str] = None


def resolve_affected_cells(source_path: str, finding: Finding) -> list[str]:
    """Return locations still affected in the selected source workbook.

    Persisted findings describe the revision on which they were detected, not
    a later immutable iteration. Re-inspect the selected source first so an
    already-fixed cell cannot be selected or overwritten again. Fall back to
    persisted coordinates only when the rule is not observable in the source,
    preserving compatibility with older stored findings.
    """
    refreshed = ExcelInspector().inspect_workbook(source_path)
    match = next((item for item in refreshed
                  if item.rule_id == finding.rule_id and item.sheet_name == finding.sheet_name), None)
    if match is not None:
        return list(getattr(match, "affected_cells", None) or [])
    return list(getattr(finding, "affected_cells", None) or [])


def _number_or_text(value: str):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def apply_remediation(source_path: str, target_path: str, finding: Finding,
                      option_id: str, value: Optional[str], target_cell: Optional[str] = None) -> RemediationResult:
    """Create target_path from source_path and apply one approved choice.

    The source is never opened for writing. Unsupported/no-op choices return
    before creating the target file.
    """
    if option_id in {"leave_open", "enter_source", "remove_series", "resize_chart", "remove_calculation"}:
        return RemediationResult(False, "This choice requires reviewer handling in Excel and was not auto-applied.")
    if option_id in {"enter_value", "replace_with_value"} and (value is None or value == ""):
        return RemediationResult(False, "A replacement value is required.")
    if option_id == "select_symbol" and value not in APPROVED_SYMBOLS:
        return RemediationResult(False, "The selected symbol is not in the approved catalogue.")
    if option_id not in {"enter_value", "replace_with_value", "select_symbol", "remove_fill", "use_indent", "turn_on"}:
        return RemediationResult(False, "Unsupported remediation choice.")

    # Older persisted revisions do not have structured coordinates. Refresh
    # the deterministic finding from the unchanged source workbook so those
    # revisions remain repairable after the application is upgraded.
    affected_cells = resolve_affected_cells(source_path, finding)
    if target_cell and affected_cells:
        if target_cell not in affected_cells:
            return RemediationResult(False, "The selected cell is not an affected cell for this finding.")
        affected_cells = [target_cell]

    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    wb = load_workbook(target_path, data_only=False)
    ws = wb[finding.sheet_name] if finding.sheet_name in wb.sheetnames else None

    if option_id in {"enter_value", "replace_with_value", "select_symbol"}:
        if ws is None or not affected_cells:
            return RemediationResult(False, "This finding has no writable cell locations.")
        replacement = _number_or_text(value or "")
        for coordinate in affected_cells:
            ws[coordinate] = replacement
    elif option_id == "remove_fill":
        if ws is None:
            return RemediationResult(False, "This finding has no writable worksheet.")
        from openpyxl.styles import PatternFill
        for coordinate in affected_cells:
            ws[coordinate].fill = PatternFill(fill_type=None)
    elif option_id == "use_indent":
        if ws is None:
            return RemediationResult(False, "This finding has no writable worksheet.")
        for coordinate in affected_cells:
            cell = ws[coordinate]
            cell.value = str(cell.value).lstrip()
            cell.alignment = cell.alignment.copy(indent=1)
    elif option_id == "turn_on":
        if ws is None:
            return RemediationResult(False, "This finding has no writable worksheet.")
        ws.sheet_view.showGridLines = True

    wb.save(target_path)
    return RemediationResult(True, "A new workbook iteration was created.", target_path)
