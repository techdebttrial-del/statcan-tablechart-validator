"""Generate 10 realistic StatCan test fixture workbooks."""
import os, sys
sys.path.insert(0, '/home/agent/statcan-tablechart-validator')
import openpyxl
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import PatternFill

OUTPUT_DIR = '/home/agent/statcan-tablechart-validator/tests/fixtures/test_cases'
os.makedirs(OUTPUT_DIR, exist_ok=True)
YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
RED_FILL = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
def save(wb, name):
    path = os.path.join(OUTPUT_DIR, name); wb.save(path); print(f"  ✓ {name}")
    return path

# 1. t101_perfect_en.xlsx
def make_perfect_en():
    wb = openpyxl.Workbook()
    ws1 = wb.active; ws1.title = "tbl1"; ws1.sheet_view.showGridLines = True
    ws1['A1'] = 'Industry'; ws1['B1'] = 'Employment (thousands)'; ws1['C1'] = 'Change (thousands)'; ws1['D1'] = 'Change (%)'
    ws1['A2'] = 'Goods-producing sector'; ws1['B2'] = 4500.2; ws1['C2'] = 45.1; ws1['D2'] = 1.0
    ws1['A3'] = '  Agriculture'; ws1['B3'] = 320.5; ws1['C3'] = -5.2; ws1['D3'] = -1.6
    ws1['A4'] = '  Construction'; ws1['B4'] = 1580.4; ws1['C4'] = 25.6; ws1['D4'] = 1.6
    ws1['A5'] = 'Services-producing sector'; ws1['B5'] = 15500.6; ws1['C5'] = 120.4; ws1['D5'] = 0.8
    ws1['A6'] = '  Trade'; ws1['B6'] = 3100.2; ws1['C6'] = 15.8; ws1['D6'] = 0.5
    ws1['A7'] = 'Total, all industries'; ws1['B7'] = 20000.8; ws1['C7'] = 165.5; ws1['D7'] = 0.8
    ws1['A8'] = 'x'; ws1['B8'] = 'confidential'
    ws1['A9'] = 'Source: Statistics Canada, Labour Force Survey, July 2026.'
    ws1['A10'] = '.. not available'
    ws1['A11'] = 'Note: Seasonally adjusted data.'

    ws2 = wb.create_sheet("tbl2"); ws2.sheet_view.showGridLines = True
    ws2['A1'] = 'Province'; ws2['B1'] = 'Unemployment rate (%)'; ws2['C1'] = 'Participation rate (%)'
    ws2['A2'] = 'Canada'; ws2['B2'] = 6.2; ws2['C2'] = 65.3
    ws2['A3'] = 'Ontario'; ws2['B3'] = 6.5; ws2['C3'] = 65.8
    ws2['A4'] = 'Quebec'; ws2['B4'] = 5.8; ws2['C4'] = 65.1
    ws2['A5'] = 'British Columbia'; ws2['B5'] = 5.4; ws2['C5'] = 66.1
    ws2['A6'] = 'Alberta'; ws2['B6'] = 6.8; ws2['C6'] = 68.9
    ws2['A7'] = 'Source: Statistics Canada, LFS, July 2026.'
    ws2['A8'] = '.. not available for all territories.'

    ws3 = wb.create_sheet("tbl3"); ws3.sheet_view.showGridLines = True
    ws3['A1'] = 'Province/Territory'; ws3['B1'] = 'Population (thousands)'; ws3['C1'] = 'Quarterly change (%)'
    ws3['A2'] = 'Ontario'; ws3['B2'] = 15996.7; ws3['C2'] = 0.6
    ws3['A3'] = 'Quebec'; ws3['B3'] = 9024.9; ws3['C3'] = 0.4
    ws3['A4'] = 'British Columbia'; ws3['B4'] = 5640.8; ws3['C4'] = 0.7
    ws3['A5'] = 'x'; ws3['B5'] = 'confidential'
    ws3['A6'] = 'Source: Statistics Canada, Demography Division, Q2 2026.'
    ws3['A7'] = 'Note: Preliminary estimates.'
    return save(wb, 't101_perfect_en.xlsx')

# 2. t101_perfect_fr.xlsx
def make_perfect_fr():
    wb = openpyxl.Workbook()
    ws1 = wb.active; ws1.title = "tbl1"; ws1.sheet_view.showGridLines = True
    ws1['A1'] = 'Province'; ws1['B1'] = "Population (en milliers)"
    ws1['A2'] = 'Ontario'; ws1['B2'] = 15996.7
    ws1['A3'] = 'Québec'; ws1['B3'] = 9024.9
    ws1['A4'] = 'Colombie-Britannique'; ws1['B4'] = 5640.8
    ws1['A5'] = 'x'; ws1['B5'] = 'confidentiel'
    ws1['A6'] = 'Source : Statistique Canada, Division de la démographie, T2 2026.'
    ws1['A7'] = '.. non disponible'
    ws1['A8'] = 'Note : Données désaisonnalisées.'
    return save(wb, 't101_perfect_fr.xlsx')

# 3. t101_fail_all.xlsx
def make_fail_all():
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "Data"; ws.sheet_view.showGridLines = False
    ws['A1'] = 'Cat'; ws['B1'] = 'Val'; ws['A3'] = '=SUM(B2:B10)'
    ws['B5'].fill = YELLOW_FILL; ws['A2'] = '  Indented'
    ws['A4'] = 'Row1'; ws['B4'] = 100
    ws.merge_cells('A6:B6')
    ws2 = wb.create_sheet("data2"); ws2.sheet_view.showGridLines = False
    ws2['A1'] = 'H'; ws2['B1'] = '=RAND()'
    ws3 = wb.create_sheet("tbl_fail"); ws3.sheet_view.showGridLines = True
    ws3['A1'] = 'H'; ws3['B1'] = 'V'; ws3['A2'] = 'A'; ws3['B2'] = 1; ws3['A3'] = 'Source: Test'
    return save(wb, 't101_fail_all.xlsx')

# 5. c101_perfect.xlsx
def make_chart_perfect():
    wb = openpyxl.Workbook()
    ws1 = wb.active; ws1.title = "chart1"
    ws1['A1'] = 'Year'; ws1['B1'] = 'CPI All-items'; ws1['C1'] = 'CPI Core'
    ws1['A2'] = 2021; ws1['B2'] = 141.2; ws1['C2'] = 139.8
    ws1['A3'] = 2022; ws1['B3'] = 151.3; ws1['C3'] = 146.9
    ws1['A4'] = 2023; ws1['B4'] = 157.6; ws1['C4'] = 152.3
    ws1['A5'] = 'Source: Statistics Canada, Consumer Price Index, 2026.'
    ws1['A6'] = 'x suppressed'
    chart = BarChart(); chart.type = "col"
    chart.title = "Consumer Price Index (2017=100)"; chart.y_axis.title = "Index"
    chart.width = 25; chart.height = 14
    data = Reference(ws1, min_col=1, min_row=1, max_col=3, max_row=4)
    cats = Reference(ws1, min_col=1, min_row=2, max_row=4)
    chart.add_data(data, titles_from_data=True); chart.set_categories(cats)
    ws1.add_chart(chart, "A8")
    return save(wb, 'c101_perfect.xlsx')

# 6. c101_fail_all.xlsx
def make_chart_fail():
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "chart_fail"
    ws['A1'] = 'Cat'
    for i in range(1, 9): ws.cell(row=1, column=i+1, value=f'S{i}')
    for r in range(2, 6):
        ws.cell(row=r, column=1, value=f'R{r}')
        for c in range(2, 10): ws.cell(row=r, column=c, value=r*c)
    ws.cell(row=3, column=2, value=None)
    chart = BarChart(); chart.title = "Title with ^superscript"
    for c in range(2, 10):
        d = Reference(ws, min_col=c, min_row=1, max_row=5)
        chart.add_data(d, titles_from_data=True)
    cats = Reference(ws, min_col=1, min_row=2, max_row=5); chart.set_categories(cats)
    chart.width = 20; chart.height = 10
    ws.add_chart(chart, "A8")
    return save(wb, 'c101_fail_all.xlsx')

# 7, 8, 9, 10 — simplified
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

def make_bilingual():
    wb = openpyxl.Workbook()
    ws1 = wb.active; ws1.title = "tbl1"; ws1.sheet_view.showGridLines = True
    ws1['A1'] = 'Industry'; ws1['B1'] = 'GDP (billions)'; ws1['C1'] = 'Share (%)'
    ws1['A2'] = 'All industries'; ws1['B2'] = 2150.5; ws1['C2'] = 100.0
    ws1['A3'] = 'Goods-producing'; ws1['B3'] = 620.8; ws1['C3'] = 28.9
    ws1['A4'] = 'Source: Statistics Canada, GDP.'; ws1['A5'] = 'x confidential'
    ws2 = wb.create_sheet("tbl1_fr"); ws2.sheet_view.showGridLines = True
    ws2['A1'] = 'Secteur'; ws2['B1'] = 'PIB (milliards)'
    ws2['A2'] = 'Ensemble des industries'; ws2['B2'] = 2150.5
    ws2['A3'] = 'Biens'; ws2['B3'] = 620.8
    ws2['A4'] = 'Source : Statistique Canada, PIB.'; ws2['A5'] = 'x confidentiel'
    return save(wb, 'bilingual_gdp.xlsx')

def make_edge():
    wb = openpyxl.Workbook()
    wb.active.title = "empty_sheet"
    ws2 = wb.create_sheet("header_only"); ws2['A1'] = 'Cat'; ws2['B1'] = 'Val'
    ws3 = wb.create_sheet("single_cell"); ws3['A1'] = 'Just one cell'
    ws4 = wb.create_sheet("tbl_single_row"); ws4.sheet_view.showGridLines = True
    ws4['A1'] = 'Item'; ws4['B1'] = 'Qty'; ws4['A2'] = 'Only'; ws4['B2'] = 42; ws4['A3'] = 'Source: Test.'
    return save(wb, 'edge_cases.xlsx')

if __name__ == '__main__':
    print("Generating 10 test fixture workbooks...")
    make_perfect_en()
    make_perfect_fr()
    make_fail_all()
    make_chart_perfect()
    make_chart_fail()
    make_mixed_cpi()
    make_mixed_lfs()
    make_bilingual()
    make_edge()
    print("Done!")