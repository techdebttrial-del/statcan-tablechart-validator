# Eval: StatCan Tables/Charts Validator v2.0

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
**Expected:** 100+ tests passed, 0 failed, 0 errors.

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

**Expected:** Perfect workbooks → 0 findings. Failure workbooks → findings
matching documented expectations.

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

### AT6 — LLM-assisted mode produces suggestions
**Command:** `LITELLM_BASE_URL=http://192.168.2.170:4000 LITELLM_MODEL=r720-cascade2 python -c "
import sys; sys.path.insert(0, '.')
from core.fix_suggester import FixSuggester
fs = FixSuggester()
suggestions = fs.suggest_fixes(findings=[mock_finding])
print(f'{len(suggestions)} suggestions generated')
"`
**Expected:** Suggestions returned for real findings

### AT7 — Bilingual report generation
**Command:** `python -m pytest tests/test_report_generator.py -v`
**Expected:** Tests pass. Both EN and FR reports generated with correct
content and language markers.

### AT8 — Streamlit app starts
**Command:** `timeout 10 streamlit run app/main.py --server.port 8505 2>&1 | grep -i "you can now view"`
**Expected:** Streamlit banner appears, app accessible on port 8505

### AT9 — Mode switching without restart
**Command:** Check that `st.session_state.use_llm` toggle in sidebar
changes finding suggestion panel visibility without app restart
**Expected:** Verified via functional test

### AT10 — Git persistence round-trip
**Command:** `python -m pytest tests/test_project_store.py tests/test_project_store_comprehensive.py -v --tb=short`
**Expected:** All project store tests pass. Create/save/load/list/close
operations work correctly.