# Test Fixture Workbooks

The test fixtures in `tests/fixtures/test_cases/` are Excel workbooks based
on real-world Statistics Canada publication patterns. They validate the
rule engine against authentic data scenarios.

## Fixture Inventory

| File | Type | Sheets | Expected Findings | Source Publication |
|------|------|--------|-------------------|-------------------|
| `t101_perfect_en.xlsx` | Tables 101 — Perfect EN | 3 tables | 0 findings | LFS Daily release |
| `t101_perfect_fr.xlsx` | Tables 101 — Perfect FR | 3 tables | 0 findings | LFS Daily release (FR) |
| `t101_fail_all.xlsx` | Tables 101 — All failures | 3 tables | 11+ findings | N/A (deliberate) |
| `t101_fail_specific.xlsx` | Tables 101 — Individual rules | 1 sheet per rule | 1 finding per failing sheet | N/A (targeted) |
| `c101_perfect.xlsx` | Charts 101 — Perfect | 2 chart sheets | 0 findings | CPI Daily release |
| `c101_fail_all.xlsx` | Charts 101 — All failures | 2 chart sheets | 7+ findings | N/A (deliberate) |
| `mixed_realistic_cpi.xlsx` | Mixed — CPI Inflation | 3 tables + 2 charts | Variable | StatCan Daily: CPI |
| `mixed_realistic_lfs.xlsx` | Mixed — LFS Employment | 3 tables + 1 chart | Variable | StatCan Daily: LFS |
| `bilingual_gdp.xlsx` | Bilingual EN/FR | 6 sheets | Language-specific | StatCan ESR: GDP |
| `edge_cases.xlsx` | Edge cases | 5+ edge sheets | Per-sheet | N/A |

## Running Fixture Validation

```bash
# Test all fixtures against rule engine
cd /home/agent/statcan-tablechart-validator
source .venv/bin/activate
python -c "
from core.excel_inspector import ExcelInspector
import os, json
inspector = ExcelInspector()
fixtures_dir = 'tests/fixtures/test_cases'
results = {}
for fn in sorted(os.listdir(fixtures_dir)):
    if fn.endswith('.xlsx'):
        path = os.path.join(fixtures_dir, fn)
        findings = inspector.inspect_workbook(path)
        results[fn] = {
            'finding_count': len(findings),
            'rule_ids': sorted(list({f.rule_id for f in findings})),
        }
        print(f'{fn:40s} {len(findings):3d} findings')
# Compare against expected
"
```

## Expected Findings Map

### t101_perfect_en.xlsx → 0 findings
A perfectly compliant workbook should trigger NO findings.

### t101_fail_all.xlsx → 11+ findings
Each row is a unique rule check:
- T101-ONE-TABLE-PER-SHEET (sheet name violation)
- T101-GRIDLINES-ON (gridlines off)
- T101-NO-FORMULAS (formulas present)
- T101-NO-COLOR-FILL (color fill)
- T101-NO-EMPTY-CELLS (empty cells)
- T101-STANDARD-SYMBOLS (no symbols)
- T101-UNIT-OF-MEASURE-ROW (no UoM)
- T101-SOURCE-PRESENT (no source)
- T101-AVOID-ROW-SPANNING (merged cells)
- T101-INDENT-FEATURE (leading spaces)
- T101-ROW-STUB-RELATED (no row stubs)

### c101_perfect.xlsx → 0 findings

### c101_fail_all.xlsx → 5+ findings

The current deterministic engine reports five directly observable failures; drawing-level checks that openpyxl cannot reliably expose are documented as limitations rather than invented results.
- C101-NO-EMPTY-CELLS
- C101-MAX-SIX-SERIES
- C101-STANDARD-SYMBOLS
- C101-SOURCE-PRESENT
- C101-NO-TITLE-SUPERSCRIPT
- C101-GRIDLINES-NO-DATALABELS
- C101-SYMBOL-REQUIRES-NOTE