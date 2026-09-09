#!/usr/bin/env bash
# ============================================================================
# verify_deployment.sh — Post-deployment verification gate for non-technical
# operators. Run after deploy_local.sh, or any time you want proof the app is
# healthy. Exits non-zero on ANY failure (CI-friendly).
#
# Checks:
#   1. venv + dependencies importable
#   2. Full deterministic test suite passes (172 tests)
#   3. Fixture sanity gates (perfect=0 findings; fail books match doc counts)
#   4. No-LLM regression guard (deterministic-only guarantee)
# ============================================================================
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"
PY=.venv/bin/python

ok()   { printf '\033[1;32m  OK\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mFAIL\033[0m %s\n' "$*"; exit 1; }

echo "== Verify 1/4: environment =="
[ -x "$PY" ] || fail ".venv missing — run scripts/deploy_local.sh first."
$PY -c "import streamlit, openpyxl, yaml, pytest" || fail "core dependencies missing — re-run deploy_local.sh."
ok "venv + core imports"

echo "== Verify 2/4: full test suite =="
$PY -m pytest tests/ -q 2>&1 | tail -1 | tee /tmp/tvc_pytest.txt | grep -qE "[1-9][0-9]* passed" \
  || fail "test suite failing — see output above. Contact the project maintainer."
ok "$(grep -oE '[0-9]+ passed[^,]*' /tmp/tvc_pytest.txt | head -1)"

echo "== Verify 3/4: fixture sanity gates =="
$PY - <<'PYEOF' || fail "fixture gates failed — the rule engine is not matching documented counts."
import sys; sys.path.insert(0, ".")
from core.excel_inspector import ExcelInspector
insp = ExcelInspector()
checks = {
    "tests/fixtures/test_cases/t101_perfect_en.xlsx": 0,
    "tests/fixtures/test_cases/t101_perfect_fr.xlsx": 0,
    "tests/fixtures/test_cases/c101_perfect.xlsx": 0,
    "tests/fixtures/test_cases/t101_fail_all.xlsx": 13,
    "tests/fixtures/test_cases/c101_fail_all.xlsx": 7,
}
for path, expected in checks.items():
    n = len(insp.inspect_workbook(path))
    status = "OK " if n == expected else "BAD"
    print(f"  {status} {path.split('/')[-1]}: {n} findings (expected {expected})")
    if n != expected:
        sys.exit(1)
PYEOF
ok "fixture counts match documented values"

echo "== Verify 4/4: deterministic-only guarantee (no LLM machinery) =="
if grep -rniE "litellm|mode_manager|fix_suggester|llm_translator" app/ core/ --include="*.py" \
   | grep -v "translation_manager.py:33" >/dev/null 2>&1; then
  fail "LLM wiring detected — deterministic-only guarantee violated."
fi
ok "no LLM machinery in app/ or core/"

echo
echo "ALL CHECKS PASSED — deployment verified. Start the app with:"
echo "  .venv/bin/streamlit run app/main.py --server.port 8502"
