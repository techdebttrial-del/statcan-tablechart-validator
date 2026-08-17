"""Release gates for the client demo."""
from pathlib import Path

from core.excel_inspector import ExcelInspector

FIXTURES = Path(__file__).parent / "fixtures" / "test_cases"


def test_perfect_demo_fixtures_are_clean():
    inspector = ExcelInspector()
    for name in ("t101_perfect_en.xlsx", "t101_perfect_fr.xlsx", "c101_perfect.xlsx"):
        assert inspector.inspect_workbook(str(FIXTURES / name)) == []


def test_failure_demo_fixtures_are_not_clean():
    inspector = ExcelInspector()
    for name in ("t101_fail_all.xlsx", "c101_fail_all.xlsx"):
        assert inspector.inspect_workbook(str(FIXTURES / name))


def test_app_has_no_llm_gateway_machinery():
    # A regression guard against re-introducing an LLM dependency: validation
    # and remediation are fully deterministic, so no LLM mode/suggestion code
    # should be present in the application.
    main_src = (Path(__file__).parents[1] / "app" / "main.py").read_text()
    services_src = (Path(__file__).parents[1] / "app" / "services.py").read_text()
    combined = main_src + "\n" + services_src
    for fragment in ("mode_mgr", "suggest_fixes", "llm_suggestions_enabled", "get_mode_manager"):
        assert fragment not in combined, f"LLM machinery '{fragment}' should have been removed"


def test_rule_packs_have_deterministic_checks():
    inspector = ExcelInspector()
    assert len(inspector.loader.rules_for("tables101")) >= 17
    assert len(inspector.loader.rules_for("charts101")) >= 17
