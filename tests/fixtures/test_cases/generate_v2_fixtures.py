"""Generate StatCan test fixture workbooks (v3).

All fixtures are based on real StatCan publication patterns. The
``t101_fail_all`` and ``c101_fail_all`` fixtures are deliberately
engineered to violate every checkable rule — each violation is placed
*inside the contiguous table region* so the deterministic inspector
actually fires.
"""
import os
import sys
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import BarChart, LineChart, Reference

OUTPUT_DIR = os.path.join(os.path.dirname(__file__))


def save(wb, name):
    path = os.path.join(OUTPUT_DIR, name)
    wb.save(path)
    return path


YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
SUPERSCRIPT_FONT = Font(vertAlign='superscript')


# ─── 1. t101_perfect_en ──────────────────────────────────────────────
def make_perfect_en():
    wb = openpyxl.Workbook()
    ws1 = wb.active; ws1.title = "tbl1"; ws1.sheet_view.showGridLines = True
    ws1['A1'] = 'Industry'; ws1['B1'] = 'Employment (thousands)'; ws1['C1'] = 'Change (thousands)'; ws1['D1'] = 'Change (percent)'
    ws1['A2'] = 'Goods-producing sector'; ws1['B2'] = 4500.2; ws1['C2'] = 45.1; ws1['D2'] = 1.0
    ws1['A3'] = 'Agriculture'; ws1['B3'] = 320.5; ws1['C3'] = -5.2; ws1['D3'] = -1.6
    ws1['A4'] = 'Construction'; ws1['B4'] = 1580.4; ws1['C4'] = 25.6; ws1['D4'] = 1.6
    ws1['A5'] = 'Services-producing sector'; ws1['B5'] = 15500.6; ws1['C5'] = 120.4; ws1['D5'] = 0.8
    ws1['A6'] = 'Trade'; ws1['B6'] = 3100.2; ws1['C6'] = 15.8; ws1['D6'] = 0.5
    ws1['A7'] = 'Total, all industries'; ws1['B7'] = 20000.8; ws1['C7'] = 165.5; ws1['D7'] = 0.8
    ws1['A8'] = 'x'; ws1['B8'] = 'confidential'; ws1['C8'] = '..'; ws1['D8'] = '..'
    for cell in (ws1['A8'], ws1['C8'], ws1['D8']):
        cell.font = SUPERSCRIPT_FONT
    ws1['A9'] = 'Source: Statistics Canada, Labour Force Survey, July 2026.'
    ws1['A10'] = '.. not available'
    ws1['A11'] = 'Note: x = confidential; .. = not available. Seasonally adjusted data.'

    ws2 = wb.create_sheet("tbl2"); ws2.sheet_view.showGridLines = True
    ws2['A1'] = 'Province'; ws2['B1'] = 'Unemployment rate (percent)'; ws2['C1'] = 'Participation rate (percent)'
    ws2['A2'] = 'Canada'; ws2['B2'] = 6.2; ws2['C2'] = 65.3
    ws2['A3'] = 'Ontario'; ws2['B3'] = 6.5; ws2['C3'] = 65.8
    ws2['A4'] = 'Quebec'; ws2['B4'] = 5.8; ws2['C4'] = 65.1
    ws2['A5'] = 'British Columbia'; ws2['B5'] = 5.4; ws2['C5'] = 66.1
    ws2['A6'] = 'Alberta'; ws2['B6'] = 6.8; ws2['C6'] = 68.9
    ws2['A7'] = 'Source: Statistics Canada, LFS, July 2026.'
    ws2['A8'] = '.. not available for all territories.'
    ws2['A9'] = 'Note: x = confidential; .. = not available.'

    ws3 = wb.create_sheet("tbl3"); ws3.sheet_view.showGridLines = True
    ws3['A1'] = 'Province/Territory'; ws3['B1'] = 'Population (thousands)'; ws3['C1'] = 'Quarterly change (percent)'
    ws3['A2'] = 'Ontario'; ws3['B2'] = 15996.7; ws3['C2'] = 0.6
    ws3['A3'] = 'Quebec'; ws3['B3'] = 9024.9; ws3['C3'] = 0.4
    ws3['A4'] = 'British Columbia'; ws3['B4'] = 5640.8; ws3['C4'] = 0.7
    ws3['A5'] = 'x'; ws3['B5'] = 'confidential'; ws3['C5'] = '..'
    for cell in (ws3['A5'], ws3['C5']):
        cell.font = SUPERSCRIPT_FONT
    ws3['A6'] = 'Source: Statistics Canada, Demography Division, Q2 2026.'
    ws3['A7'] = 'Note: x = confidential; .. = not available. Preliminary estimates.'
    return save(wb, 't101_perfect_en.xlsx')


# ─── 2. t101_perfect_fr ──────────────────────────────────────────────
def make_perfect_fr():
    wb = openpyxl.Workbook()
    ws1 = wb.active; ws1.title = "tbl1"; ws1.sheet_view.showGridLines = True
    ws1['A1'] = 'Province'; ws1['B1'] = "Population (en milliers)"
    ws1['A2'] = 'Ontario'; ws1['B2'] = 15996.7
    ws1['A3'] = 'Québec'; ws1['B3'] = 9024.9
    ws1['A4'] = 'Colombie-Britannique'; ws1['B4'] = 5640.8
    ws1['A5'] = 'x'; ws1['B5'] = 'confidentiel'; ws1['A5'].font = SUPERSCRIPT_FONT
    ws1['A6'] = 'Source : Statistique Canada, Division de la démographie, T2 2026.'
    ws1['A7'] = '.. non disponible'; ws1['B7'] = '..'; ws1['B7'].font = SUPERSCRIPT_FONT
    ws1['A8'] = 'Note : x = confidentiel; .. = non disponible. Données désaisonnalisées.'
    return save(wb, 't101_perfect_fr.xlsx')


# ─── 3. t101_fail_all — every table rule violated, in-region ──────────
def make_fail_all():
    """Single sheet engineered to trigger 10 unique T101 rules, plus a
    second sheet with a non-tbl name to trigger ONE-TABLE-PER-SHEET.
    Total: 11 findings across 10 unique rules (ONE-TABLE-PER-SHEET fires twice).
    """
    wb = openpyxl.Workbook()
    # Sheet "Data": wrong name (not tblXX), gridlines off, formula in data,
    # color fill on a data cell, empty data cell, leading-space indent,
    # row-spanning merge within data region, no source, no symbols in data,
    # no unit of measure, no row stubs.
    ws = wb.active; ws.title = "Data"; ws.sheet_view.showGridLines = False
    ws['A1'] = '  Category'   # leading spaces → T101-INDENT-FEATURE
    ws['B1'] = 'Value'
    # Data rows: A2 has no value (no row stubs — only 1 col-A value in rows 2-8)
    ws['B2'] = 100
    ws['B3'] = 50
    ws['B4'] = 75
    # Formula in data region → T101-NO-FORMULAS
    ws['A2'] = '=B2+B3'
    # Color fill on B2 (in data region, has value) → T101-NO-COLOR-FILL
    ws['B2'].fill = YELLOW_FILL
    # Row-spanning merge within data region → T101-AVOID-ROW-SPANNING
    ws.merge_cells('A2:A3')
    # B4 has value but C2 is empty → T101-NO-EMPTY-CELLS
    # Need a 3rd column to create an empty cell in the data region
    ws['C1'] = 'Note col'
    # C2 and C3 are empty → empty data cells → T101-NO-EMPTY-CELLS
    # (but C1 has a value, so column C is part of the contiguous region)
    # Actually, let me be more careful. The data region right_edge is
    # determined by contiguous populated columns. C1='Note col' populates
    # column C in row 1. So C is in the region. C2/C3 empty → finding.
    # But wait — _data_region_bounds starts at col 2. So it checks cols 2+.
    # C is col 3. If C1 is populated, C is contiguous. C2/C3 empty → finding.

    # Row stubs: col A rows 2-8 has A2='=B2+B3' (merged) → 1 value → False → T101-ROW-STUB-RELATED
    # (A2 has a formula string, which counts as a non-None value)

    # No source line → T101-SOURCE-PRESENT
    # Empty data cells + no symbols → T101-STANDARD-SYMBOLS
    # No unit of measure → T101-UNIT-OF-MEASURE-ROW

    # Sheet 2: "tbl_fail" — non-tbl name triggers ONE-TABLE-PER-SHEET
    # Minimal sheet that only triggers ONE-TABLE-PER-SHEET
    ws2 = wb.create_sheet("tbl_fail"); ws2.sheet_view.showGridLines = True
    ws2['A1'] = 'H'; ws2['B1'] = 'V'
    ws2['A2'] = 'Data'; ws2['B2'] = 1
    ws2['A3'] = 'Source: Test'
    return save(wb, 't101_fail_all.xlsx')


# ─── 4. c101_perfect ──────────────────────────────────────────────────
def make_chart_perfect():
    wb = openpyxl.Workbook()
    ws1 = wb.active; ws1.title = "chart1"
    ws1['A1'] = 'Year'; ws1['B1'] = 'CPI All-items'; ws1['C1'] = 'CPI Core'
    ws1['A2'] = 2021; ws1['B2'] = 141.2; ws1['C2'] = 139.8
    ws1['A3'] = 2022; ws1['B3'] = 151.3; ws1['C3'] = 146.9
    ws1['A4'] = 2023; ws1['B4'] = 157.6; ws1['C4'] = 152.3
    ws1['A5'] = 'Source: Statistics Canada, Consumer Price Index, 2026.'
    ws1['B5'] = 'x'; ws1['C5'] = '..'
    for cell in (ws1['B5'], ws1['C5']):
        cell.font = SUPERSCRIPT_FONT
    ws1['A6'] = 'Note: x = suppressed; .. = not available.'
    chart = BarChart(); chart.type = "col"
    chart.title = "Consumer Price Index (2017=100)"; chart.y_axis.title = "Index"
    chart.width = 25; chart.height = 14
    data = Reference(ws1, min_col=1, min_row=1, max_col=3, max_row=4)
    cats = Reference(ws1, min_col=1, min_row=2, max_row=4)
    chart.add_data(data, titles_from_data=True); chart.set_categories(cats)
    ws1.add_chart(chart, "A8")
    return save(wb, 'c101_perfect.xlsx')


# ─── 5. c101_fail_all — every chart rule violated ─────────────────────
def make_chart_fail():
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "chart_fail"
    ws['A1'] = 'Cat'
    for i in range(1, 9):
        ws.cell(row=1, column=i + 1, value=f'S{i}')
    for r in range(2, 6):
        ws.cell(row=r, column=1, value=f'R{r}')
        for c in range(2, 10):
            if r == 3 and c == 2:
                continue  # leave B3 empty → C101-NO-EMPTY-CELLS + C101-STANDARD-SYMBOLS
            ws.cell(row=r, column=c, value=r * c)
    chart = BarChart()
    chart.title = "Title with ^superscript"  # C101-NO-TITLE-SUPERSCRIPT
    for c in range(2, 10):
        d = Reference(ws, min_col=c, min_row=1, max_row=5)
        chart.add_data(d, titles_from_data=True)
    cats = Reference(ws, min_col=1, min_row=2, max_row=5)
    chart.set_categories(cats)
    chart.width = 20; chart.height = 10  # C101-SIZE-WIDTH, C101-SIZE-HEIGHT-MIN
    ws.add_chart(chart, "A8")
    # No source line → C101-SOURCE-PRESENT
    # No symbols → C101-STANDARD-SYMBOLS
    # 8 series → C101-MAX-SIX-SERIES
    return save(wb, 'c101_fail_all.xlsx')


# ─── 6. mixed_realistic_cpi ──────────────────────────────────────────
def make_mixed_cpi():
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "tbl1"; ws.sheet_view.showGridLines = True
    ws['A1'] = 'Province'; ws['B1'] = 'CPI (2017=100)'; ws['C1'] = 'Change (%)'
    ws['A2'] = 'Canada'; ws['B2'] = 160.1; ws['C2'] = 2.7
    ws['A3'] = 'Ontario'; ws['B3'] = 161.3; ws['C3'] = 2.8
    ws['A4'] = 'Quebec'; ws['B4'] = 158.9; ws['C4'] = 2.3
    ws['A5'] = 'x'; ws['B5'] = 'confidential'
    ws['A6'] = 'Source: Statistics Canada, CPI, June 2026.'
    ws['A7'] = '.. not available'
    ws['A8'] = 'Note: 2017=100 base year.'
    ws2 = wb.create_sheet("chart1")
    ws2['A1'] = 'Year'; ws2['B1'] = 'CPI'; ws2['C1'] = 'Core'
    ws2['A2'] = 2021; ws2['B2'] = 141.2; ws2['C2'] = 139.8
    ws2['A3'] = 2022; ws2['B3'] = 151.3; ws2['C3'] = 146.9
    ws2['A4'] = 'Source: Statistics Canada.'; ws2['A5'] = 'x suppressed'
    chart = BarChart(); chart.title = "CPI Trends"; chart.width = 25; chart.height = 14
    d = Reference(ws2, min_col=1, min_row=1, max_col=3, max_row=3)
    ct = Reference(ws2, min_col=1, min_row=2, max_row=3)
    chart.add_data(d, titles_from_data=True); chart.set_categories(ct)
    ws2.add_chart(chart, "A6")
    return save(wb, 'mixed_realistic_cpi.xlsx')


# ─── 7. mixed_realistic_lfs ──────────────────────────────────────────
def make_mixed_lfs():
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "tbl1"; ws.sheet_view.showGridLines = True
    ws['A1'] = 'Characteristic'; ws['B1'] = 'July 2026'; ws['C1'] = 'Change'
    ws['A2'] = 'Population (thousands)'; ws['B2'] = 32150.4; ws['C2'] = 64.8
    ws['A3'] = 'Employment'; ws['B3'] = 19720.3; ws['C3'] = 34.7
    ws['A4'] = 'Unemployment'; ws['B4'] = 1300.2; ws['C4'] = 0.6
    ws['A5'] = 'x'; ws['B5'] = 'confidential'
    ws['A6'] = 'Source: Statistics Canada, LFS, July 2026.'
    ws['A7'] = 'Note: Seasonally adjusted.'
    ws2 = wb.create_sheet("chart1")
    ws2['A1'] = 'Year'; ws2['B1'] = 'Goods'; ws2['C1'] = 'Services'
    ws2['A2'] = 2023; ws2['B2'] = 4420.8; ws2['C2'] = 15050.2
    ws2['A3'] = 2024; ws2['B3'] = 4475.6; ws2['C3'] = 15200.8
    ws2['A4'] = 'Source: Statistics Canada.'; ws2['A5'] = 'x suppressed'
    chart = BarChart(); chart.title = "Employment by Sector"; chart.width = 24; chart.height = 13
    d = Reference(ws2, min_col=1, min_row=1, max_col=3, max_row=3)
    ct = Reference(ws2, min_col=1, min_row=2, max_row=3)
    chart.add_data(d, titles_from_data=True); chart.set_categories(ct)
    ws2.add_chart(chart, "A7")
    return save(wb, 'mixed_realistic_lfs.xlsx')


# ─── 8. bilingual_gdp ────────────────────────────────────────────────
def make_bilingual():
    wb = openpyxl.Workbook()
    ws1 = wb.active; ws1.title = "tbl1"; ws1.sheet_view.showGridLines = True
    ws1['A1'] = 'Industry'; ws1['B1'] = 'GDP (billions)'; ws1['C1'] = 'Share (percent)'
    ws1['A2'] = 'All industries'; ws1['B2'] = 2150.5; ws1['C2'] = 100.0
    ws1['A3'] = 'Goods-producing'; ws1['B3'] = 620.8; ws1['C3'] = 28.9
    ws1['A4'] = 'Source: Statistics Canada, GDP.'
    ws1['A5'] = 'x confidential'
    ws2 = wb.create_sheet("tbl1_fr"); ws2.sheet_view.showGridLines = True
    ws2['A1'] = 'Secteur'; ws2['B1'] = 'PIB (milliards)'
    ws2['A2'] = 'Ensemble des industries'; ws2['B2'] = 2150.5
    ws2['A3'] = 'Biens'; ws2['B3'] = 620.8
    ws2['A4'] = 'Source : Statistique Canada, PIB.'
    ws2['A5'] = 'x confidentiel'
    return save(wb, 'bilingual_gdp.xlsx')


# ─── 9. edge_cases ───────────────────────────────────────────────────
def make_edge():
    wb = openpyxl.Workbook()
    wb.active.title = "empty_sheet"
    ws2 = wb.create_sheet("header_only"); ws2['A1'] = 'Cat'; ws2['B1'] = 'Val'
    ws3 = wb.create_sheet("single_cell"); ws3['A1'] = 'Just one cell'
    ws4 = wb.create_sheet("tbl_single_row"); ws4.sheet_view.showGridLines = True
    ws4['A1'] = 'Item'; ws4['B1'] = 'Qty'; ws4['A2'] = 'Only'; ws4['B2'] = 42
    ws4['A3'] = 'Source: Test.'
    return save(wb, 'edge_cases.xlsx')


# ─── 10. t101_fail_specific ─────────────────────────────────────────
def make_fail_specific():
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "tbl1"; ws.sheet_view.showGridLines = False
    ws['A1'] = 'Region'; ws['B1'] = 'Value'
    ws['A2'] = 'Canada'; ws['B2'] = 100
    ws['A3'] = 'Source: Statistics Canada.'
    # Gridlines off → T101-GRIDLINES-ON
    # Formula
    ws['C1'] = '=SUM(B2:B3)'
    # Color fill
    ws['B2'].fill = YELLOW_FILL
    # Symbol without superscript
    ws['A4'] = 'x'; ws['B4'] = 'suppressed'
    # No unit of measure in header (B1='Value' has no unit token)
    return save(wb, 't101_fail_specific.xlsx')


# ─── 11–14. FRESH fixtures based on recent StatCan Daily releases ───
# These are modeled on real recent StatCan publications with engineered
# failures built in, to demonstrate the validator against realistic content.

def make_daily_retail_2026():
    """Retail Trade Monthly — modeled on StatCan Daily 2026-08-22.
    Table with: gridlines off, formula, color fill, empty cell, no source,
    leading-space indent, no symbols, no unit row, merged row span.
    Engineered to produce ~10 findings across multiple rules.
    """
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "retail_data"; ws.sheet_view.showGridLines = False
    ws['A1'] = '  Industry'
    ws['B1'] = 'Retail sales (millions)'
    ws['C1'] = 'Change (percent)'
    ws['A2'] = 'Total retail trade'
    ws['B2'] = 68500.3
    ws['C2'] = 1.2
    ws['A3'] = 'Food and beverage stores'
    ws['B3'] = 14200.5
    ws['C3'] = 0.8
    # Formula in data region
    ws['B4'] = '=B2+B3'
    ws['C4'] = 2.1
    # Color fill on a data cell
    ws['B3'].fill = YELLOW_FILL
    # Empty cell in data region (C5)
    ws['A5'] = 'Health and personal care'
    ws['B5'] = 6500.2
    # C5 is empty
    # Merged row span within data region
    ws.merge_cells('A3:A4')
    # No source, no symbols, no unit row, leading spaces on A1
    return save(wb, 'daily_retail_2026.xlsx')


def make_daily_gdp_q2_2026():
    """GDP by Industry Quarterly — modeled on StatCan Daily 2026-08-29.
    Mostly compliant but with: gridlines off, no unit row, abbreviation in header.
    Engineered to produce ~3 findings (low-severity demo).
    """
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "tbl1"; ws.sheet_view.showGridLines = False
    ws['A1'] = 'Industry'
    ws['B1'] = 'GDP ($B)';  # uses $ abbreviation → T101-FULL-TEXT-OVER-SYMBOLS
    ws['C1'] = 'Change (%)'  # uses % → T101-FULL-TEXT-OVER-SYMBOLS
    ws['A2'] = 'All industries'
    ws['B2'] = 2150.5
    ws['C2'] = 0.8
    ws['A3'] = 'Goods-producing'
    ws['B3'] = 620.8
    ws['C3'] = 0.3
    ws['A4'] = 'Services-producing'
    ws['B4'] = 1530.2
    ws['C4'] = 1.1
    ws['A5'] = 'x'
    ws['B5'] = 'confidential'
    ws['C5'] = '..'  # fill all cells — no empty cells
    ws['A5'].font = SUPERSCRIPT_FONT
    ws['A6'] = 'Source: Statistics Canada, GDP by Industry, Q2 2026.'
    ws['A7'] = 'Note: x = suppressed. Chain-volume real GDP, 2017=100.'
    # Gridlines off, abbreviations in headers, no explicit unit row (though $B and % are tokens)
    return save(wb, 'daily_gdp_q2_2026.xlsx')


def make_daily_cpi_chart_2026():
    """CPI Chart — modeled on StatCan Daily 2026-08-19 CPI release.
    Chart with: 7 series (over limit), width too narrow, no source, title with superscript.
    Engineered to produce ~5 chart findings.
    """
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "chart_cpi"
    ws['A1'] = 'Month'
    for i, prov in enumerate(['Canada', 'Newfoundland', 'PEI', 'Nova Scotia',
                              'New Brunswick', 'Quebec', 'Ontario'], start=1):
        ws.cell(row=1, column=i + 1, value=prov)
    months = ['Apr', 'May', 'Jun', 'Jul', 'Aug']
    for r, m in enumerate(months, start=2):
        ws.cell(row=r, column=1, value=m)
        for c in range(2, 9):
            ws.cell(row=r, column=c, value=round(150 + r * c * 0.1, 1))
    ws.cell(row=7, column=1, value='Source: Statistics Canada, CPI, August 2026.')
    chart = LineChart()
    chart.title = "CPI by Province^1"  # superscript in title
    chart.width = 18; chart.height = 8  # too narrow and too short
    for c in range(2, 9):
        d = Reference(ws, min_col=c, min_row=1, max_row=6)
        chart.add_data(d, titles_from_data=True)
    cats = Reference(ws, min_col=1, min_row=2, max_row=6)
    chart.set_categories(cats)
    ws.add_chart(chart, "A9")
    # 7 series → C101-MAX-SIX-SERIES
    # Width 18cm → C101-SIZE-WIDTH
    # Height 8cm → C101-SIZE-HEIGHT-MIN
    # Title has ^ → C101-NO-TITLE-SUPERSCRIPT
    return save(wb, 'daily_cpi_chart_2026.xlsx')


def make_daily_employment_chart_2026():
    """Employment Chart — modeled on StatCan Daily 2026-08-08 LFS release.
    Well-formed chart that should pass cleanly.
    Used as a "this real-world chart passes" demo fixture.
    """
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "chart_emp"
    ws['A1'] = 'Month'; ws['B1'] = 'Full-time'; ws['C1'] = 'Part-time'
    ws['A2'] = 'Mar 2026'; ws['B2'] = 16100.5; ws['C2'] = 3600.2
    ws['A3'] = 'Apr 2026'; ws['B3'] = 16200.8; ws['C3'] = 3580.1
    ws['A4'] = 'May 2026'; ws['B4'] = 16350.3; ws['C4'] = 3620.5
    ws['A5'] = 'Jun 2026'; ws['B5'] = 16410.7; ws['C5'] = 3650.8
    ws['A6'] = 'Jul 2026'; ws['B6'] = 16480.2; ws['C6'] = 3680.4
    ws['A7'] = 'Source: Statistics Canada, LFS, July 2026.'
    ws['A8'] = 'Note: Seasonally adjusted. Thousands.'
    chart = BarChart(); chart.type = "col"
    chart.title = "Employment by Full-time and Part-time"
    chart.width = 25; chart.height = 14
    data = Reference(ws, min_col=1, min_row=1, max_col=3, max_row=6)
    cats = Reference(ws, min_col=1, min_row=2, max_row=6)
    chart.add_data(data, titles_from_data=True); chart.set_categories(cats)
    ws.add_chart(chart, "A10")
    return save(wb, 'daily_employment_chart_2026.xlsx')


if __name__ == '__main__':
    print("Generating test fixture workbooks...")
    make_perfect_en()
    make_perfect_fr()
    make_fail_all()
    make_chart_perfect()
    make_chart_fail()
    make_mixed_cpi()
    make_mixed_lfs()
    make_bilingual()
    make_edge()
    make_fail_specific()
    make_daily_retail_2026()
    make_daily_gdp_q2_2026()
    make_daily_cpi_chart_2026()
    make_daily_employment_chart_2026()
    print("Done!")
