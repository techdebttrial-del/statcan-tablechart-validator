# Test Fixture Workbooks

The test fixtures in `tests/fixtures/test_cases/` are Excel workbooks based
on real-world Statistics Canada publication patterns. They validate the
rule engine against authentic data scenarios.

## Fixture Inventory

| File | Type | Sheets | Expected Findings | Source Publication |
|------|------|--------|-------------------|-------------------|
| `t101_perfect_en.xlsx` | Tables 101 — Perfect EN | 3 tables | 0 findings | LFS Daily release |
| `t101_perfect_fr.xlsx` | Tables 101 — Perfect FR | 1 table | 0 findings | LFS Daily release (FR) |
| `t101_fail_all.xlsx` | Tables 101 — All failures | 2 sheets | 13 findings (11 unique rules) | N/A (deliberate) |
| `t101_fail_specific.xlsx` | Tables 101 — Individual rules | 1 sheet | 6 findings | N/A (targeted) |
| `c101_perfect.xlsx` | Charts 101 — Perfect | 1 chart sheet | 0 findings | CPI Daily release |
| `c101_fail_all.xlsx` | Charts 101 — All failures | 1 chart sheet | 7 findings | N/A (deliberate) |
| `mixed_realistic_cpi.xlsx` | Mixed — CPI Inflation | 1 table + 1 chart | 3 findings | StatCan Daily: CPI |
| `mixed_realistic_lfs.xlsx` | Mixed — LFS Employment | 1 table + 1 chart | 2 findings | StatCan Daily: LFS |
| `bilingual_gdp.xlsx` | Bilingual EN/FR | 2 sheets | 3 findings | StatCan ESR: GDP |
| `edge_cases.xlsx` | Edge cases | 4 edge sheets | 2 findings | N/A |
| `daily_retail_2026.xlsx` | Tables 101 — Retail Trade Daily | 1 sheet | 7 findings | StatCan Daily: Retail Trade Aug 2026 |
| `daily_gdp_q2_2026.xlsx` | Tables 101 — GDP Quarterly | 1 sheet | 2 findings | StatCan Daily: GDP by Industry Q2 2026 |
| `daily_cpi_chart_2026.xlsx` | Charts 101 — CPI Chart | 1 chart sheet | 4 findings | StatCan Daily: CPI Aug 2026 |
| `daily_employment_chart_2026.xlsx` | Charts 101 — Employment (perfect) | 1 chart sheet | 0 findings | StatCan Daily: LFS Jul 2026 |

## Running Fixture Validation

```bash
cd /home/agent/statcan-tablechart-validator
source .venv/bin/activate
python -c "
from core.excel_inspector import ExcelInspector
import os
inspector = ExcelInspector()
fixtures_dir = 'tests/fixtures/test_cases'
for fn in sorted(os.listdir(fixtures_dir)):
    if fn.endswith('.xlsx'):
        path = os.path.join(fixtures_dir, fn)
        findings = inspector.inspect_workbook(path)
        print(f'{fn}: {len(findings)} findings')
"
```

## Expected Findings Map

### t101_perfect_en.xlsx → 0 findings
A perfectly compliant workbook should trigger NO findings.

### t101_perfect_fr.xlsx → 0 findings

### t101_fail_all.xlsx → 13 findings (11 unique rules)
Two sheets, each with a non-tbl name (ONE-TABLE-PER-SHEET fires twice).
The "Data" sheet violates every checkable table rule:

- T101-ONE-TABLE-PER-SHEET (sheet name "Data" does not match tblXX)
- T101-GRIDLINES-ON (gridlines off)
- T101-NO-FORMULAS (formula at A2)
- T101-NO-COLOR-FILL (yellow fill on B2)
- T101-NO-EMPTY-CELLS (empty cells C2, C3)
- T101-STANDARD-SYMBOLS (empty cells present but no standard symbols)
- T101-UNIT-OF-MEASURE-ROW (no unit of measure row)
- T101-SOURCE-PRESENT (no source line)
- T101-AVOID-ROW-SPANNING (merged range A2:A3 spans rows)
- T101-INDENT-FEATURE (leading spaces in A1)
- T101-ROW-STUB-RELATED (only 1 value in column A rows 2-8)

### c101_perfect.xlsx → 0 findings

### c101_fail_all.xlsx → 7 findings
- C101-NO-EMPTY-CELLS (empty cell at B3)
- C101-MAX-SIX-SERIES (8 series)
- C101-SIZE-WIDTH (width 20cm, below 22.5cm minimum)
- C101-SIZE-HEIGHT-MIN (height 10cm, below 11cm minimum)
- C101-NO-TITLE-SUPERSCRIPT (title contains ^superscript)
- C101-SOURCE-PRESENT (no source line)
- C101-STANDARD-SYMBOLS (empty cell present but no standard symbols)

### Fresh fixtures (recent StatCan publications)

- `daily_retail_2026.xlsx` → 7 findings: gridlines off, formula, color fill,
  empty cells, row span, leading-space indent, no source, wrong sheet name
- `daily_gdp_q2_2026.xlsx` → 2 findings: gridlines off, abbreviations in headers
- `daily_cpi_chart_2026.xlsx` → 4 findings: 7 series (over limit), title with
  superscript, width too narrow, height too short
- `daily_employment_chart_2026.xlsx` → 0 findings (perfect chart)
