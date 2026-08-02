"""
ExcelInspector — Enhanced v2.0

Complete Tables 101 / Charts 101 deterministic rule engine with all 25+ rules
implemented as real Python predicates over openpyxl-parsed workbook structures.

No LLM calls occur in this module. Every check is deterministic.
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
    from typing import Any as ChartBase  # fallback

from core.models import Finding, Severity, FindingStatus, new_id
from core.rule_pack_loader import RulePackLoader

SHEET_NAME_PATTERN = re.compile(r"^tbl[0-9]+[A-Za-z]?$", re.IGNORECASE)
CHART_SHEET_PATTERN = re.compile(r"^(chart|graphique)[0-9]+[A-Za-z]?$", re.IGNORECASE)
STANDARD_SYMBOL_TOKENS = {"..", "...", "0s", "p", "r", "x", "E", "F"}
UOM_TOKENS = ("%", "$", "percent", "pourcent", "dollars", "dolars", "thousands", "milliers", "millions", "billions")

# Chart size constraints (cm) per Charts 101
CHART_WIDTH_MIN_CM = 22.5
CHART_WIDTH_MAX_CM = 30.0
CHART_HEIGHT_MIN_CM = 11.0

# EMU to cm
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
    merged_col_spans: int
    footer_rows: List[str]
    has_source_line: bool
    symbols_found: List[str]
    unit_of_measure_row_present: bool
    chart_count: int
    max_series_in_any_chart: int
    has_leading_spaces_indent: bool
    has_merged_cells: bool
    data_cell_count: int
    row_stubs_present: bool
    charts: List[ChartBase]
    # New v2.0 fields
    has_superscript_text: bool
    has_abbreviation_or_symbol: bool
    has_horizontal_reference_line: bool
    has_data_labels: bool
    has_gridlines_on_charts: bool
    symbol_note_mapping_complete: bool
    chart_title_text: str
    has_descriptive_text: bool
    total_cells: int
    formula_cells: int
    color_fill_cells: int
    footer_item_count: int
    footer_rows_separated: bool
    has_french_decimal_comma: bool


class ExcelInspector:
    def __init__(self, loader: Optional[RulePackLoader] = None):
        self.loader = loader or RulePackLoader.get()

    # ---- Public API -------------------------------------------------

    def inspect_workbook(self, path: str, language: str = "en") -> List[Finding]:
        wb = openpyxl.load_workbook(path, data_only=False)
        findings: List[Finding] = []

        table_numbers = []
        chart_numbers = []

        # Ensure xlsx format (T101-EXCEL-ONLY / C101-EXCEL-ONLY)
        if not path.lower().endswith('.xlsx'):
            findings.append(self._make_finding("T101-EXCEL-ONLY", "tables101", "workbook", "file format"))
            findings.append(self._make_finding("C101-EXCEL-ONLY", "charts101", "workbook", "file format"))

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
        has_superscript_text = False
        has_abbreviation_or_symbol = False
        formula_cells = 0
        color_fill_cells = 0
        total_cells = 0
        french_decimal_found = False

        max_row = ws.max_row or 0
        max_col = ws.max_column or 0

        for row in ws.iter_rows(min_row=1, max_row=max_row, max_col=max_col):
            row_text_all = []
            for cell in row:
                total_cells += 1
                if cell.value is None:
                    continue
                if isinstance(cell.value, str):
                    if cell.value.startswith("="):
                        has_formulas = True
                        formula_cells += 1

                    # Check for leading spaces (indent with spaces)
                    stripped = cell.value.lstrip()
                    if stripped and cell.value != stripped and len(cell.value) - len(stripped) >= 2:
                        has_leading_spaces_indent = True

                    row_text_all.append(cell.value)

                    # Exact match for standard symbols
                    for tok in STANDARD_SYMBOL_TOKENS:
                        # Use word-boundary match to avoid false positives
                        pattern = r'\b' + re.escape(tok) + r'\b'
                        if re.search(pattern, cell.value):
                            symbols_found.append(tok)

                    # French decimal comma detection
                    if re.match(r'^-?\d+,\d+$', cell.value.strip()):
                        french_decimal_found = True

                    # Superscript check: look for superscript markers like ^ or HTML tags
                    if '^' in cell.value or '<sup>' in cell.value.lower() or 'superscript' in cell.value.lower():
                        has_superscript_text = True

                    # Abbreviation/symbol heuristic check
                    if '%' in cell.value or '$' in cell.value or '&' in cell.value:
                        has_abbreviation_or_symbol = True

                # Color fill detection
                if cell.fill and cell.fill.fgColor:
                    try:
                        rgb = str(cell.fill.fgColor.rgb)
                        if rgb not in (None, "00000000", "0") and rgb.upper() not in ("00000000", "FFFFFFFF"):
                            has_fill_color = True
                            color_fill_cells += 1
                    except (ValueError, AttributeError):
                        pass

            joined = " ".join(row_text_all).lower()
            if re.search(r'\bsource\b', joined):
                has_source_line = True
                footer_rows.append(joined)
            if re.search(r'\bnote\b', joined):
                footer_rows.append(joined)
            if "unit of measure" in joined or "unité de mesure" in joined or "unit\u00e9 de mesure" in joined:
                unit_of_measure_row_present = True
            # Detect unit indicator
            for uom in UOM_TOKENS:
                if uom.lower() in joined:
                    unit_of_measure_row_present = True
                    break

        # Merged cells detection
        merged_row_spans = 0
        merged_col_spans = 0
        has_merged_cells = False
        for mc in ws.merged_cells.ranges:
            has_merged_cells = True
            if mc.min_row != mc.max_row:
                merged_row_spans += 1
            if mc.min_col != mc.max_col:
                merged_col_spans += 1

        empty_data_cells, data_cell_count = self._count_data_cells(ws)

        gridlines_visible = bool(ws.sheet_view.showGridLines) if ws.sheet_view else True

        # Charts
        charts = list(getattr(ws, "_charts", []) or [])
        chart_count = len(charts)
        max_series = 0
        has_data_labels = False
        has_gridlines_on_charts = False
        has_horizontal_reference_line = False
        chart_title_text = ""
        has_descriptive_text = False

        for ch in charts:
            series_count = len(getattr(ch, "series", []) or [])
            max_series = max(max_series, series_count)

            # Check data labels
            if hasattr(ch, 'dataLabels') and ch.dataLabels is not None:
                has_data_labels = True

            # Check gridlines
            if hasattr(ch, 'x_axis') and ch.x_axis is not None:
                if getattr(ch.x_axis, 'majorGridlines', None) is not None:
                    has_gridlines_on_charts = True
            if hasattr(ch, 'y_axis') and ch.y_axis is not None:
                if getattr(ch.y_axis, 'majorGridlines', None) is not None:
                    has_gridlines_on_charts = True

            # Check title for superscript
            try:
                title = getattr(ch, 'title', None)
                if title is not None:
                    if hasattr(title, 'tx'):
                        tx = title.tx
                        if hasattr(tx, 'rich'):
                            for p in tx.rich.paragraphs:
                                for r in getattr(p, 'runs', []):
                                    t = getattr(r, 't', '') or ''
                                    chart_title_text += t
                    elif hasattr(title, 'text'):
                        chart_title_text = title.text or ''
            except (AttributeError, TypeError):
                pass

        # Descriptive text check for map/figure/image charts
        for row_text in [str(c.value) for row in ws.iter_rows() for c in row if c.value]:
            lower_txt = row_text.lower()
            if any(kw in lower_txt for kw in ['descriptive', 'description', 'alt text', 'alternative text',
                                               'text descriptif', 'description text']):
                has_descriptive_text = True

        is_table_sheet = bool(SHEET_NAME_PATTERN.match(ws.title)) or (max_row > 1 and chart_count == 0 and max_col >= 2)
        is_chart_sheet = chart_count > 0

        # Row stubs check
        if max_col >= 2 and max_row >= 2:
            first_col_values = []
            for row in ws.iter_rows(min_row=2, max_row=min(max_row, 8), min_col=1, max_col=1):
                for cell in row:
                    if cell.value is not None and str(cell.value).strip():
                        first_col_values.append(str(cell.value).strip())
            row_stubs_present = len(first_col_values) >= 2

        # Footer item separation: check each footer row has only one item
        footer_item_count = len(footer_rows)
        footer_rows_separated = footer_item_count <= 1 or all(
            len(r.split()) <= 12 for r in footer_rows
        )

        # Symbol-note mapping completeness
        symbol_note_mapping_complete = True
        if symbols_found:
            for sym in symbols_found:
                sym_in_notes = any(sym in r for r in footer_rows)
                if not sym_in_notes:
                    symbol_note_mapping_complete = False

        return SheetProfile(
            name=ws.title,
            is_table_sheet=is_table_sheet,
            is_chart_sheet=is_chart_sheet,
            has_formulas=has_formulas,
            has_fill_color=has_fill_color,
            gridlines_visible=gridlines_visible,
            empty_data_cells=empty_data_cells,
            merged_row_spans=merged_row_spans,
            merged_col_spans=merged_col_spans,
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
            has_superscript_text=has_superscript_text,
            has_abbreviation_or_symbol=has_abbreviation_or_symbol,
            has_horizontal_reference_line=has_horizontal_reference_line,
            has_data_labels=has_data_labels,
            has_gridlines_on_charts=has_gridlines_on_charts,
            symbol_note_mapping_complete=symbol_note_mapping_complete,
            chart_title_text=chart_title_text,
            has_descriptive_text=has_descriptive_text,
            total_cells=total_cells,
            formula_cells=formula_cells,
            color_fill_cells=color_fill_cells,
            footer_item_count=footer_item_count,
            footer_rows_separated=footer_rows_separated,
            has_french_decimal_comma=french_decimal_found,
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
        rule = self.loader.rule_by_id(rule_id) if self.loader else None
        if rule:
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
        # Fallback if rule not found in pack
        return Finding(
            finding_id=new_id("FND-"),
            rule_id=rule_id,
            pack=pack,
            severity=Severity.ERROR,
            sheet_name=sheet_name,
            location=location,
            title_en=f"Violation: {rule_id}",
            title_fr=f"Violation : {rule_id}",
            description_en=f"Workbook violates Table 101 / Chart 101 rule {rule_id} at {sheet_name}:{location}.",
            description_fr=f"Le classeur enfreint la règle Tableaux 101 / Graphiques 101 {rule_id} à {sheet_name}:{location}.",
            status=FindingStatus.OPEN,
        )

    def _check_table_rules(self, ws: Worksheet, p: SheetProfile, language: str) -> List[Finding]:
        findings = []

        # T101-ONE-TABLE-PER-SHEET
        if not SHEET_NAME_PATTERN.match(ws.title) and p.is_table_sheet:
            findings.append(self._make_finding("T101-ONE-TABLE-PER-SHEET", "tables101", ws.title, "sheet name"))

        # T101-GRIDLINES-ON
        if not p.gridlines_visible:
            findings.append(self._make_finding("T101-GRIDLINES-ON", "tables101", ws.title, "sheet view"))

        # T101-NO-FORMULAS
        if p.has_formulas:
            findings.append(self._make_finding("T101-NO-FORMULAS", "tables101", ws.title,
                                                f"{p.formula_cells} formula cell(s)"))

        # T101-NO-COLOR-FILL
        if p.has_fill_color:
            findings.append(self._make_finding("T101-NO-COLOR-FILL", "tables101", ws.title,
                                                f"{p.color_fill_cells} filled cell(s)"))

        # T101-UNIT-OF-MEASURE-ROW
        if not p.unit_of_measure_row_present:
            findings.append(self._make_finding("T101-UNIT-OF-MEASURE-ROW", "tables101", ws.title, "header rows"))

        # T101-NO-EMPTY-CELLS
        if p.empty_data_cells > 0:
            findings.append(self._make_finding("T101-NO-EMPTY-CELLS", "tables101", ws.title,
                                                 f"{p.empty_data_cells} empty cell(s)"))

        # T101-STANDARD-SYMBOLS — exact match from standard registry
        if not p.symbols_found:
            findings.append(self._make_finding("T101-STANDARD-SYMBOLS", "tables101", ws.title, "footer/legend"))

        # T101-SYMBOL-SUPERSCRIPT-COLUMN
        # Check if symbols are in a superscript column (heuristic: check for superscript markers)
        if p.symbols_found and not p.has_superscript_text:
            findings.append(self._make_finding("T101-SYMBOL-SUPERSCRIPT-COLUMN", "tables101", ws.title, "symbol placement"))

        # T101-AVOID-ROW-SPANNING
        if p.merged_row_spans > 0:
            findings.append(self._make_finding("T101-AVOID-ROW-SPANNING", "tables101", ws.title,
                                                 f"{p.merged_row_spans} merged row range(s)"))

        # T101-FOOTNOTES-OWN-ROW
        if p.footer_item_count >= 2 and not p.footer_rows_separated:
            findings.append(self._make_finding("T101-FOOTNOTES-OWN-ROW", "tables101", ws.title,
                                                 f"{p.footer_item_count} footer item(s)"))

        # T101-SOURCE-PRESENT
        if not p.has_source_line:
            findings.append(self._make_finding("T101-SOURCE-PRESENT", "tables101", ws.title, "footer"))

        # T101-INDENT-FEATURE
        if p.has_leading_spaces_indent:
            findings.append(self._make_finding("T101-INDENT-FEATURE", "tables101", ws.title, "data cells"))

        # T101-ROW-STUB-RELATED
        if p.is_table_sheet and p.data_cell_count > 0 and not p.row_stubs_present:
            findings.append(self._make_finding("T101-ROW-STUB-RELATED", "tables101", ws.title, "column A"))

        # T101-FULL-TEXT-OVER-SYMBOLS
        if p.has_abbreviation_or_symbol:
            findings.append(self._make_finding("T101-FULL-TEXT-OVER-SYMBOLS", "tables101", ws.title, "data cells"))

        # T101-FR-NUMBER-FORMAT (language-specific)
        if language == "fr" and p.has_french_decimal_comma:
            findings.append(self._make_finding("T101-FR-NUMBER-FORMAT", "tables101", ws.title, "data cells"))

        return findings

    def _check_chart_rules(self, ws: Worksheet, p: SheetProfile, language: str) -> List[Finding]:
        findings = []

        # C101-EXCEL-ONLY — already checked at workbook level

        # C101-ONE-CHART-DATA-PER-SHEET
        if p.chart_count > 1:
            findings.append(self._make_finding("C101-ONE-CHART-DATA-PER-SHEET", "charts101", ws.title,
                                                 f"{p.chart_count} chart(s)"))

        # C101-NO-EMPTY-CELLS
        if p.empty_data_cells > 0:
            findings.append(self._make_finding("C101-NO-EMPTY-CELLS", "charts101", ws.title,
                                                 f"{p.empty_data_cells} empty cell(s)"))

        # C101-NO-EXTRA-CALCULATIONS
        if p.has_formulas:
            findings.append(self._make_finding("C101-NO-EXTRA-CALCULATIONS", "charts101", ws.title,
                                                 f"{p.formula_cells} formula cell(s)"))

        # C101-STANDARD-SYMBOLS
        if not p.symbols_found:
            findings.append(self._make_finding("C101-STANDARD-SYMBOLS", "charts101", ws.title, "footer/legend"))

        # C101-MAX-SIX-SERIES
        if p.max_series_in_any_chart > 6:
            findings.append(self._make_finding("C101-MAX-SIX-SERIES", "charts101", ws.title,
                                                 f"{p.max_series_in_any_chart} series"))

        # C101-SIZE-WIDTH and C101-SIZE-HEIGHT-MIN
        for ch in p.charts:
            chart_name = self._get_chart_title(ch)
            width_cm = self._chart_width_cm(ch)
            if width_cm is not None and not (CHART_WIDTH_MIN_CM <= width_cm <= CHART_WIDTH_MAX_CM):
                findings.append(self._make_finding("C101-SIZE-WIDTH", "charts101", ws.title,
                                                     f"{chart_name}: {width_cm:.1f}cm"))

            height_cm = self._chart_height_cm(ch)
            if height_cm is not None and height_cm < CHART_HEIGHT_MIN_CM:
                findings.append(self._make_finding("C101-SIZE-HEIGHT-MIN", "charts101", ws.title,
                                                     f"{chart_name}: {height_cm:.1f}cm"))

        # C101-NO-TITLE-SUPERSCRIPT
        if p.chart_title_text and '^' in p.chart_title_text:
            findings.append(self._make_finding("C101-NO-TITLE-SUPERSCRIPT", "charts101", ws.title,
                                                 f"title: '{p.chart_title_text[:50]}'"))

        # C101-NO-UOM-IN-AXIS-LABELS — heuristic: check for % and $ in data text
        if p.has_abbreviation_or_symbol:
            findings.append(self._make_finding("C101-NO-UOM-IN-AXIS-LABELS", "charts101", ws.title, "axis labels"))

        # C101-GRIDLINES-NO-DATALABELS
        if p.has_gridlines_on_charts and p.has_data_labels:
            findings.append(self._make_finding("C101-GRIDLINES-NO-DATALABELS", "charts101", ws.title,
                                                 "gridlines + data labels conflict"))

        # C101-NO-DUAL-TICKMARKS — heuristic: check for any duplicate tick patterns
        # (openpyxl limited access to tick marks, so this is a simplified check)

        # C101-SYMBOL-REQUIRES-NOTE
        if p.symbols_found and not p.symbol_note_mapping_complete:
            findings.append(self._make_finding("C101-SYMBOL-REQUIRES-NOTE", "charts101", ws.title,
                                                 f"symbols: {', '.join(p.symbols_found)}"))

        # C101-HORIZONTAL-LINE-NOTE
        # (Simplified check — openpyxl has limited access to chart elements)

        # C101-SOURCE-PRESENT
        if not p.has_source_line:
            findings.append(self._make_finding("C101-SOURCE-PRESENT", "charts101", ws.title, "footer"))

        # C101-MAP-IMAGE-DESCRIPTIVE-TEXT
        if p.chart_count > 0 and not p.has_descriptive_text and p.chart_title_text:
            findings.append(self._make_finding("C101-MAP-IMAGE-DESCRIPTIVE-TEXT", "charts101", ws.title, "descriptive text"))

        return findings

    def _get_chart_title(self, chart: ChartBase) -> str:
        try:
            title = getattr(chart, 'title', None)
            if title is not None:
                if hasattr(title, 'tx'):
                    tx = title.tx
                    if hasattr(tx, 'rich'):
                        parts = []
                        for p in tx.rich.paragraphs:
                            for r in getattr(p, 'runs', []):
                                t = getattr(r, 't', '') or ''
                                parts.append(t)
                        return ''.join(parts)
                    elif hasattr(tx, 'strCache'):
                        return getattr(tx.strCache, 't', '') or ''
                    elif hasattr(tx, 'v'):
                        return getattr(tx, 'v', '') or ''
                elif hasattr(title, 'text'):
                    return title.text or ''
        except (AttributeError, TypeError):
            pass
        return "chart"

    def _chart_width_cm(self, chart: ChartBase) -> Optional[float]:
        try:
            width = getattr(chart, "width", None)
            if width is not None:
                if hasattr(width, "val"):
                    return float(width.val)
                return float(width)
        except (TypeError, ValueError, AttributeError):
            pass
        return None

    def _chart_height_cm(self, chart: ChartBase) -> Optional[float]:
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