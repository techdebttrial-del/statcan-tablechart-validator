"""Apply approved deterministic remediation choices to a copied workbook."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from openpyxl import load_workbook

from core.models import Finding
from core.remediation_catalog import APPROVED_SYMBOLS


@dataclass
class RemediationResult:
    success: bool
    message: str
    output_path: Optional[str] = None


def _number_or_text(value: str):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def apply_remediation(source_path: str, target_path: str, finding: Finding,
                      option_id: str, value: Optional[str]) -> RemediationResult:
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

    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    wb = load_workbook(target_path, data_only=False)
    ws = wb[finding.sheet_name] if finding.sheet_name in wb.sheetnames else None

    if option_id in {"enter_value", "replace_with_value", "select_symbol"}:
        if ws is None or not finding.affected_cells:
            return RemediationResult(False, "This finding has no writable cell locations.")
        replacement = _number_or_text(value or "")
        for coordinate in finding.affected_cells:
            ws[coordinate] = replacement
    elif option_id == "remove_fill":
        if ws is None:
            return RemediationResult(False, "This finding has no writable worksheet.")
        from openpyxl.styles import PatternFill
        for coordinate in finding.affected_cells:
            ws[coordinate].fill = PatternFill(fill_type=None)
    elif option_id == "use_indent":
        if ws is None:
            return RemediationResult(False, "This finding has no writable worksheet.")
        for coordinate in finding.affected_cells:
            cell = ws[coordinate]
            cell.value = str(cell.value).lstrip()
            cell.alignment = cell.alignment.copy(indent=1)
    elif option_id == "turn_on":
        if ws is None:
            return RemediationResult(False, "This finding has no writable worksheet.")
        ws.sheet_view.showGridLines = True

    wb.save(target_path)
    return RemediationResult(True, "A new workbook iteration was created.", target_path)
