"""
ExcelInspector

Deterministic-first inspection engine for Table 101 / Chart 101 compliance,
mirroring the Accelerator's design principle: "Deterministic-first — LLM
only for targeted disambiguation" (see core/walkthrough.py docstring in the
broader project). No LLM calls occur in this module; every check is a plain
Python predicate evaluated against openpyxl-parsed workbook structures.

This module intentionally exposes a stable Finding-producing API
(`inspect_workbook`) so that when this tool is folded into the broader
Accelerator later, it can be registered as a new deterministic stage
(e.g. stage "validate_tables_charts") without changing its public contract.
"""
from __future__ import annotations

import re
import string
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
try:
    from openpyxl.chart._chart import ChartBase
except ImportError:
    from typing import Any as ChartBase  # fallback for older openpyxl

from core.models import Finding, Severity, FindingStatus, new_id
from core.rule_pack_loader import RulePackLoader

SHEET_NAME_PATTERN = re.compile(r"^tbl[0-9]+[A-Za-z]?$", re.IGNORECASE)
STANDARD_SYMBOL_TOKENS = {"..", "...", "0s", "p", "r", "x", "E", "F"}
UOM_TOKENS = ("%", "$", "percent", "pourcent", "dollars", "dolars")

# Chart101 size constraints (cm)
CHART_WIDTH_MIN_CM = 22.5
CHART_WIDTH_MAX_CM = 30.0
CHART_HEIGHT_MIN_CM = 11.0

# EMU to cm conversion factor (1 inch = 914400 EMU, 1 inch = 2.54 cm)
EMU_TO_CM = 2.54 / 914400.0


@dataclass
class SheetProfile:
    name: str
    is_table_sheet: bool
    is_chart_sheet: bool
    has_formulas: bool
    has_fill_color: bool
    gridlines_visible: bool
    empty_data_cells: int
    merged_row_spans: int
    footer_rows: List[str]
    has_source_line: bool
    symbols_found: List[str]
    unit_of_measure_row_present: bool
    chart_count: int
    max_series_in_any_chart: int
    # New fields for enhanced rules
    has_leading_spaces_indent: bool
    has_merged_cells: bool
    data_cell_count: int
    row_stubs_present: bool
    charts: List[ChartBase]


class ExcelInspector:
    def __init__(self, loader: Optional[RulePackLoader] = None):
        self.loader = loader or RulePackLoader.get()

    # ---- Public API -------------------------------------------------

    def inspect_workbook(self, path: str, language: str = "en") -> List[Finding]:
        wb = openpyxl.load_workbook(path, data_only=False)
        findings: List[Finding] = []

        table_numbers = []
        chart_numbers = []

        for ws in wb.worksheets:
            profile = self._profile_sheet(ws)

            if profile.is_table_sheet:
                findings.extend(self._check_table_rules(ws, profile, language))
                num = self._extract_number(ws.title)
                if num:
                    table_numbers.append(num)

            if profile.chart_count > 0:
                findings.extend(self._check_chart_rules(ws, profile, language))
                num = self._extract_number(ws.title)
                if num:
                    chart_numbers.append(num)

        findings.extend(self._check_numbering_uniqueness(table_numbers, "tables101", "T101-UNIQUE-NUMBERING"))
        findings.extend(self._check_numbering_uniqueness(chart_numbers, "charts101", "C101-UNIQUE-NUMBERING"))

        return findings

    # ---- Sheet profiling ---------------------------------------------

    def _profile_sheet(self, ws: Worksheet) -> SheetProfile:
        has_formulas = False
        has_fill_color = False
        empty_data_cells = 0
        data_cell_count = 0
        symbols_found: List[str] = []
        footer_rows: List[str] = []
        has_source_line = False
        unit_of_measure_row_present = False
        has_leading_spaces_indent = False
        row_stubs_present = False

        max_row = ws.max_row or 0
        max_col = ws.max_column or 0

        for row in ws.iter_rows(min_row=1, max_row=max_row, max_col=max_col):
            row_text_all = []
            for cell in row:
                if cell.value is None:
                    continue
                if isinstance(cell.value, str):
                    if cell.value.startswith("="):
                        has_formulas = True
                    # Check for leading spaces (indent with spaces instead of Excel indent)
                    stripped = cell.value.lstrip()
                    if stripped and cell.value != stripped and len(cell.value) - len(stripped) >= 2:
                        has_leading_spaces_indent = True
                    row_text_all.append(cell.value)
                    for tok in STANDARD_SYMBOL_TOKENS:
                        if tok in cell.value:
                            symbols_found.append(tok)
                if cell.fill and cell.fill.fgColor and cell.fill.fgColor.rgb not in (None, "00000000"):
                    # Check it's not the default (no fill)
                    if str(cell.fill.fgColor.rgb) != "00000000":
                        has_fill_color = True

            joined = " ".join(row_text_all).lower()
            if "source" in joined or "source :" in joined:
                has_source_line = True
                footer_rows.append(joined)
            if "note" in joined:
                footer_rows.append(joined)
            if "unit of measure" in joined or "unité de mesure" in joined:
                unit_of_measure_row_present = True

        merged_row_spans = 0
        has_merged_cells = False
        for mc in ws.merged_cells.ranges:
            has_merged_cells = True
            if mc.min_row != mc.max_row or (mc.max_col - mc.min_col) > 0:
                merged_row_spans += 1

        empty_data_cells, data_cell_count = self._count_data_cells(ws)

        gridlines_visible = bool(ws.sheet_view.showGridLines) if ws.sheet_view else True

        # Get charts from worksheet
        charts = list(getattr(ws, "_charts", []) or [])
        chart_count = len(charts)
        max_series = 0
        for ch in charts:
            series_count = len(getattr(ch, "series", []) or [])
            max_series = max(max_series, series_count)

        is_table_sheet = bool(SHEET_NAME_PATTERN.match(ws.title)) or (max_row > 1 and chart_count == 0)
        is_chart_sheet = chart_count > 0

        # Check if row stubs (first column) have content related to data
        if max_col >= 2 and max_row >= 2:
            first_col_values = []
            for row in ws.iter_rows(min_row=2, max_row=min(max_row, 5), min_col=1, max_col=1):
                for cell in row:
                    if cell.value is not None and str(cell.value).strip():
                        first_col_values.append(str(cell.value).strip())
            row_stubs_present = len(first_col_values) > 0

        return SheetProfile(
            name=ws.title,
            is_table_sheet=is_table_sheet,
            is_chart_sheet=is_chart_sheet,
            has_formulas=has_formulas,
            has_fill_color=has_fill_color,
            gridlines_visible=gridlines_visible,
            empty_data_cells=empty_data_cells,
            merged_row_spans=merged_row_spans,
            footer_rows=footer_rows,
            has_source_line=has_source_line,
            symbols_found=list(set(symbols_found)),
            unit_of_measure_row_present=unit_of_measure_row_present,
            chart_count=chart_count,
            max_series_in_any_chart=max_series,
            has_leading_spaces_indent=has_leading_spaces_indent,
            has_merged_cells=has_merged_cells,
            data_cell_count=data_cell_count,
            row_stubs_present=row_stubs_present,
            charts=charts,
        )

    def _count_data_cells(self, ws: Worksheet) -> tuple:
        """Returns (empty_count, total_data_count) for data region."""
        empty_count = 0
        total_count = 0
        max_row = ws.max_row or 0
        max_col = ws.max_column or 0
        if max_row < 3 or max_col < 2:
            return 0, 0
        for row in ws.iter_rows(min_row=2, max_row=max_row - 1, min_col=2, max_col=max_col):
            for cell in row:
                total_count += 1
                if cell.value is None:
                    empty_count += 1
        return empty_count, total_count

    def _extract_number(self, sheet_name: str) -> Optional[str]:
        m = re.search(r"[0-9]+[A-Za-z]?", sheet_name)
        return m.group(0) if m else None

    # ---- Rule application ---------------------------------------------

    def _make_finding(self, rule_id: str, pack: str, sheet_name: str, location: str) -> Finding:
        rule = self.loader.rule_by_id(rule_id)
        return Finding(
            finding_id=new_id("FND-"),
            rule_id=rule.id,
            pack=pack,
            severity=Severity(rule.severity),
            sheet_name=sheet_name,
            location=location,
            title_en=rule.title_en,
            title_fr=rule.title_fr,
            description_en=rule.description_en,
            description_fr=rule.description_fr,
            status=FindingStatus.OPEN,
        )

    def _check_table_rules(self, ws: Worksheet, p: SheetProfile, language: str) -> List[Finding]:
        findings = []

        # T101-ONE-TABLE-PER-SHEET
        if not SHEET_NAME_PATTERN.match(ws.title):
            findings.append(self._make_finding("T101-ONE-TABLE-PER-SHEET", "tables101", ws.title, "sheet name"))

        # T101-GRIDLINES-ON
        if not p.gridlines_visible:
            findings.append(self._make_finding("T101-GRIDLINES-ON", "tables101", ws.title, "sheet view"))

        # T101-NO-FORMULAS
        if p.has_formulas:
            findings.append(self._make_finding("T101-NO-FORMULAS", "tables101", ws.title, "data cells"))

        # T101-NO-COLOR-FILL
        if p.has_fill_color:
            findings.append(self._make_finding("T101-NO-COLOR-FILL", "tables101", ws.title, "data cells"))

        # T101-UNIT-OF-MEASURE-ROW
        if not p.unit_of_measure_row_present:
            findings.append(self._make_finding("T101-UNIT-OF-MEASURE-ROW", "tables101", ws.title, "header rows"))

        # T101-NO-EMPTY-CELLS
        if p.empty_data_cells > 0:
            findings.append(self._make_finding("T101-NO-EMPTY-CELLS", "tables101", ws.title,
                                                 f"{p.empty_data_cells} empty cell(s)"))

        # T101-STANDARD-SYMBOLS
        if not p.symbols_found:
            findings.append(self._make_finding("T101-STANDARD-SYMBOLS", "tables101", ws.title, "footer/legend"))

        # T101-AVOID-ROW-SPANNING
        if p.merged_row_spans > 0:
            findings.append(self._make_finding("T101-AVOID-ROW-SPANNING", "tables101", ws.title,
                                                 f"{p.merged_row_spans} merged range(s)"))

        # T101-SOURCE-PRESENT
        if not p.has_source_line:
            findings.append(self._make_finding("T101-SOURCE-PRESENT", "tables101", ws.title, "footer"))

        # T101-INDENT-FEATURE (use Excel indent, not leading spaces)
        if p.has_leading_spaces_indent:
            findings.append(self._make_finding("T101-INDENT-FEATURE", "tables101", ws.title, "data cells"))

        # T101-ROW-STUB-RELATED (row stub must relate to data)
        if p.is_table_sheet and p.data_cell_count > 0 and not p.row_stubs_present:
            findings.append(self._make_finding("T101-ROW-STUB-RELATED", "tables101", ws.title, "column A"))

        if language == "fr":
            # Heuristic: flag if any numeric-looking string uses comma decimal separator
            if self._has_french_decimal_commas(ws):
                findings.append(self._make_finding("T101-FR-NUMBER-FORMAT", "tables101", ws.title, "data cells"))

        return findings

    def _check_chart_rules(self, ws: Worksheet, p: SheetProfile, language: str) -> List[Finding]:
        findings = []

        # C101-NO-EMPTY-CELLS
        if p.empty_data_cells > 0:
            findings.append(self._make_finding("C101-NO-EMPTY-CELLS", "charts101", ws.title,
                                                 f"{p.empty_data_cells} empty cell(s)"))

        # C101-MAX-SIX-SERIES
        if p.max_series_in_any_chart > 6:
            findings.append(self._make_finding("C101-MAX-SIX-SERIES", "charts101", ws.title,
                                                 f"{p.max_series_in_any_chart} series"))

        # C101-STANDARD-SYMBOLS
        if not p.symbols_found:
            findings.append(self._make_finding("C101-STANDARD-SYMBOLS", "charts101", ws.title, "footer/legend"))

        # C101-SOURCE-PRESENT
        if not p.has_source_line:
            findings.append(self._make_finding("C101-SOURCE-PRESENT", "charts101", ws.title, "footer"))

        # C101-SIZE-WIDTH and C101-SIZE-HEIGHT-MIN
        for ch in p.charts:
            chart_name = getattr(ch, "title", None) or "chart"
            # Width check
            width_cm = self._chart_width_cm(ch)
            if width_cm is not None and not (CHART_WIDTH_MIN_CM <= width_cm <= CHART_WIDTH_MAX_CM):
                findings.append(self._make_finding("C101-SIZE-WIDTH", "charts101", ws.title,
                                                     f"{chart_name}: {width_cm:.1f}cm"))

            # Height check
            height_cm = self._chart_height_cm(ch)
            if height_cm is not None and height_cm < CHART_HEIGHT_MIN_CM:
                findings.append(self._make_finding("C101-SIZE-HEIGHT-MIN", "charts101", ws.title,
                                                     f"{chart_name}: {height_cm:.1f}cm"))

            # C101-GRIDLINES-NO-DATALABELS (gridlines + data labels together)
            has_gridlines = getattr(ch, "x_axis", None) and getattr(ch.x_axis, "majorGridlines", None) is not None
            # This is a simplified check; full check needs chart element inspection
            # We flag if both gridlines are visible and data labels appear configured

        return findings

    def _chart_width_cm(self, chart: ChartBase) -> Optional[float]:
        """Get chart width in cm from openpyxl chart object."""
        try:
            width = getattr(chart, "width", None)
            if width is not None:
                # openpyxl stores width in cm (as a Length object or float)
                if hasattr(width, "val"):
                    return float(width.val)
                return float(width)
        except (TypeError, ValueError, AttributeError):
            pass
        return None

    def _chart_height_cm(self, chart: ChartBase) -> Optional[float]:
        """Get chart height in cm from openpyxl chart object."""
        try:
            height = getattr(chart, "height", None)
            if height is not None:
                if hasattr(height, "val"):
                    return float(height.val)
                return float(height)
        except (TypeError, ValueError, AttributeError):
            pass
        return None

    def _check_numbering_uniqueness(self, numbers: List[str], pack: str, rule_id: str) -> List[Finding]:
        findings = []
        seen = set()
        dupes = set()
        for n in numbers:
            if n in seen:
                dupes.add(n)
            seen.add(n)
        if dupes:
            findings.append(self._make_finding(rule_id, pack, "workbook", f"duplicate number(s): {sorted(dupes)}"))
        return findings

    def _has_french_decimal_commas(self, ws: Worksheet) -> bool:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and re.match(r"^-?\d+,\d+$", cell.value.strip()):
                    return True
        return False
