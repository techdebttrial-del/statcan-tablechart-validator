# Eval: StatCan Tables/Charts Validator

> **Amendment (2026-08-17):** The original v2.0 spec called for a dual-flavour
> (offline + LLM-assisted) architecture. The LLM path was subsequently
> removed — identification and changes are fully deterministic. See
> `docs/MODES.md`. Acceptance tests AT6 and AT9 below were reworked to the
> deterministic remediation workflow.

## Acceptance Tests

### AT1 — All Tables 101 rules fire correctly
**Command:** `python -m pytest tests/test_rules_tables101.py -v --tb=short`
**Expected:** 25+ tests passed, 0 failed. Every rule ID in tables101.yaml
has at least one pass and one fail test.

### AT2 — All Charts 101 rules fire correctly
**Command:** `python -m pytest tests/test_rules_charts101.py -v --tb=short`
**Expected:** 20+ tests passed, 0 failed. Every rule ID in charts101.yaml
has at least one pass and one fail test.

### AT3 — Full test suite passes
**Command:** `python -m pytest tests/ -v --tb=short`
**Expected:** 100+ tests passed, 0 failed, 0 errors (currently 102).

### AT4 — Real-world fixtures produce expected findings
**Command:** `python -c "
import json, sys; sys.path.insert(0, '.')
from core.excel_inspector import ExcelInspector
inspector = ExcelInspector()
for fn in ['test_perfect_tables.xlsx','test_perfect_charts.xlsx','test_table_failures.xlsx',
           'test_chart_failures.xlsx','test_mixed_pass_fail.xlsx']:
    f = inspector.inspect_workbook(f'tests/fixtures/test_cases/{fn}')
    print(f'{fn}: {len(f)} findings')
"`

**Expected:** `t101_perfect_en.xlsx`, `t101_perfect_fr.xlsx`, and
`c101_perfect.xlsx` → 0 findings. Failure workbooks → findings matching
`docs/FIXTURES.md`; drawing-level checks unavailable through openpyxl are
explicitly documented as limitations.

### AT5 — Offline mode runs without LLM calls
**Command:** `LITELLM_BASE_URL="" python -c "
import sys; sys.path.insert(0, '.')
from core.excel_inspector import ExcelInspector
from core.translation_manager import TranslationManager, PassthroughTranslator
tm = TranslationManager(translator=PassthroughTranslator())
inspector = ExcelInspector()
f = inspector.inspect_workbook('tests/fixtures/sample_workbook.xlsx')
print(f'{len(f)} findings — no LLM calls made')
assert tm.translator.engine_name == 'passthrough-no-llm-configured'
"`
**Expected:** Findings produced, translator is PassthroughTranslator

### AT6 — Deterministic remediation produces a new workbook iteration
**Command:** `python -m pytest tests/test_remediation_apply.py tests/test_deterministic_remediation.py tests/test_iteration_verification.py -v`
**Expected:** Tests pass. Applying an approved remediation choice to a
violating finding produces a fresh immutable workbook iteration and commits it.

### AT7 — Bilingual report generation
**Command:** `python -m pytest tests/test_report_generator.py -v`
**Expected:** Tests pass. Both EN and FR reports generated with correct
content and language markers.

### AT8 — Streamlit app starts
**Command:** `timeout 10 streamlit run app/main.py --server.port 8505 2>&1 | grep -i "you can now view"`
**Expected:** Streamlit banner appears, app accessible on port 8505

### AT9 — No LLM machinery in the application
**Command:** `grep -rnE "mode_mgr|suggest_fixes|get_mode_manager|llm_suggestions_enabled" app/ || echo clean`
**Expected:** No matches — the LLM mode/suggestion machinery has been removed.

### AT10 — Git persistence round-trip
**Command:** `python -m pytest tests/test_project_store.py tests/test_project_store_comprehensive.py -v --tb=short`
**Expected:** All project store tests pass. Create/save/load/list/close
operations work correctly.