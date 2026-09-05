"""Apply approved deterministic remediation choices to a copied workbook."""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from openpyxl import load_workbook
from openpyxl.styles import Font

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


# Actions that require manual Excel handling — not auto-applied
_MANUAL_ACTIONS = {"leave_open"}

# Actions that need a text input value
_TEXT_INPUT_ACTIONS = {"enter_value", "replace_with_value", "enter_source", "rename_sheet"}


def apply_remediation(source_path: str, target_path: str, finding: Finding,
                      option_id: str, value: Optional[str], target_cell: Optional[str] = None) -> RemediationResult:
    """Create target_path from source_path and apply one approved choice.

    The source is never opened for writing. Unsupported/no-op choices return
    before creating the target file.
    """
    if option_id in _MANUAL_ACTIONS:
        return RemediationResult(False, "This choice requires reviewer handling in Excel and was not auto-applied.")

    # Text-input actions require a value
    if option_id in _TEXT_INPUT_ACTIONS and (value is None or value == ""):
        return RemediationResult(False, "A value is required for this action.")
    if option_id == "select_symbol" and value not in APPROVED_SYMBOLS:
        return RemediationResult(False, "The selected symbol is not in the approved catalogue.")

    # Validate supported actions
    supported = {
        "enter_value", "replace_with_value", "select_symbol",
        "remove_fill", "use_indent", "turn_on",
        "enter_source", "rename_sheet", "unmerge",
        "apply_superscript", "fix_number_format",
        "strip_title_superscript", "resize_chart",
        "remove_series", "remove_data_labels",
    }
    if option_id not in supported:
        return RemediationResult(False, "Unsupported remediation choice.")

    # For cell-based actions, refresh affected cells from source
    cell_based_actions = {"enter_value", "replace_with_value", "select_symbol",
                          "remove_fill", "use_indent", "apply_superscript",
                          "fix_number_format", "unmerge"}
    affected_cells = []
    if option_id in cell_based_actions:
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

    if ws is None and option_id not in ("resize_chart", "remove_series", "strip_title_superscript", "remove_data_labels"):
        return RemediationResult(False, "This finding has no writable worksheet.")

    # ---- Cell-value actions ----
    if option_id in ("enter_value", "replace_with_value", "select_symbol"):
        if not affected_cells:
            return RemediationResult(False, "This finding has no writable cell locations.")
        replacement = _number_or_text(value or "")
        for coordinate in affected_cells:
            ws[coordinate] = replacement

    elif option_id == "remove_fill":
        from openpyxl.styles import PatternFill
        for coordinate in affected_cells:
            ws[coordinate].fill = PatternFill(fill_type=None)

    elif option_id == "use_indent":
        for coordinate in affected_cells:
            cell = ws[coordinate]
            cell.value = str(cell.value).lstrip()
            cell.alignment = cell.alignment.copy(indent=1)

    elif option_id == "turn_on":
        ws.sheet_view.showGridLines = True

    elif option_id == "enter_source":
        # Write a source line in the first empty row after the data region
        max_row = ws.max_row or 1
        # Find the last populated row
        last_row = max_row
        for row_idx in range(max_row, 0, -1):
            if any(ws.cell(row=row_idx, column=c).value for c in range(1, ws.max_column + 1)):
                last_row = row_idx
                break
        source_row = last_row + 1
        ws.cell(row=source_row, column=1, value=value or "Source: Statistics Canada")

    elif option_id == "rename_sheet":
        # Rename the sheet to the provided tblXX name. Excel forbids
        # : \ / ? * [ ] in sheet titles and caps length at 31; refuse these
        # BEFORE touching the workbook so the reviewer gets a friendly
        # message instead of an openpyxl traceback.
        new_name = (value or "tbl1").strip()
        if any(ch in new_name for ch in ':\\/?*[]'):
            return RemediationResult(
                False,
                "Invalid sheet name. Avoid : \\ / ? * [ ] and keep it short.",
            )
        if len(new_name) > 31:
            return RemediationResult(
                False,
                "Sheet names are limited to 31 characters.",
            )
        ws.title = new_name

    elif option_id == "unmerge":
        # Unmerge any row-spanning merged cells in the finding's sheet
        for mc in list(ws.merged_cells.ranges):
            if mc.min_row != mc.max_row:
                ws.unmerge_cells(str(mc))

    elif option_id == "apply_superscript":
        # Apply superscript font to the affected cells (symbol cells)
        for coordinate in affected_cells:
            cell = ws[coordinate]
            cell.font = Font(vertAlign="superscript", bold=cell.font.bold,
                             size=cell.font.size, name=cell.font.name)

    elif option_id == "fix_number_format":
        # Convert French decimal commas to periods in affected cells
        for coordinate in affected_cells:
            cell = ws[coordinate]
            if isinstance(cell.value, str):
                converted = re.sub(r'(\d),(\d)', r'\1.\2', cell.value)
                ws[coordinate] = _number_or_text(converted)

    # ---- Chart-specific actions ----
    elif option_id == "strip_title_superscript":
        # Strip ^ and superscript markers from chart title text
        charts = list(getattr(ws, "_charts", []) or []) if ws else []
        for ch in charts:
            try:
                title = getattr(ch, 'title', None)
                if title and hasattr(title, 'tx'):
                    tx = title.tx
                    if hasattr(tx, 'rich'):
                        for p in tx.rich.paragraphs:
                            runs = getattr(p, 'r', None) or getattr(p, 'runs', [])
                            for r in runs:
                                t = getattr(r, 't', '') or ''
                                # Strip ^ markers and superscript text indicators
                                cleaned = t.replace('^', '')
                                r.t = cleaned
            except (AttributeError, TypeError):
                pass

    elif option_id == "resize_chart":
        # Resize all charts on the sheet to valid dimensions
        # Width: 25cm, Height: 14cm (both within Charts 101 bounds)
        # Must update both chart.width/height AND the anchor ext (EMU units)
        # because the inspector reads from the anchor ext
        CM_TO_EMU = 914400.0 / 2.54  # 1 cm in EMU
        target_width_emu = int(25 * CM_TO_EMU)
        target_height_emu = int(14 * CM_TO_EMU)
        charts = list(getattr(ws, "_charts", []) or []) if ws else []
        for ch in charts:
            ch.width = 25
            ch.height = 14
            anchor = getattr(ch, "anchor", None)
            if anchor is not None:
                ext = getattr(anchor, "ext", None)
                if ext is not None:
                    ext.cx = target_width_emu
                    ext.cy = target_height_emu

    elif option_id == "remove_series":
        # Remove excess series beyond the 6th
        charts = list(getattr(ws, "_charts", []) or []) if ws else []
        for ch in charts:
            series = getattr(ch, 'series', None) or []
            if len(series) > 6:
                ch.series = series[:6]

    elif option_id == "remove_data_labels":
        # Remove data labels from all charts on the sheet
        charts = list(getattr(ws, "_charts", []) or []) if ws else []
        for ch in charts:
            ch.dataLabels = None

    wb.save(target_path)
    return RemediationResult(True, "A new workbook iteration was created.", target_path)
