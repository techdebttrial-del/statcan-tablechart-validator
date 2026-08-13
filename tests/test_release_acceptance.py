"""Release gates for the client demo."""
from pathlib import Path

from core.excel_inspector import ExcelInspector
from core.mode_manager import ModeManager

FIXTURES = Path(__file__).parent / "fixtures" / "test_cases"


def test_perfect_demo_fixtures_are_clean():
    inspector = ExcelInspector()
    for name in ("t101_perfect_en.xlsx", "t101_perfect_fr.xlsx", "c101_perfect.xlsx"):
        assert inspector.inspect_workbook(str(FIXTURES / name)) == []


def test_failure_demo_fixtures_are_not_clean():
    inspector = ExcelInspector()
    for name in ("t101_fail_all.xlsx", "c101_fail_all.xlsx"):
        assert inspector.inspect_workbook(str(FIXTURES / name))


def test_offline_mode_does_not_probe_gateway():
    health = ModeManager(use_llm=False, litellm_url="http://127.0.0.1:9").check_health()
    assert health.mode.value == "offline"
    assert not health.gateway_ok


def test_local_llm_mode_sees_cascade2_gateway():
    health = ModeManager(
        use_llm=True,
        litellm_url="http://192.168.2.170:4000",
        cascade2_model="r720-cascade2",
    ).check_health()
    assert health.gateway_ok
    assert health.cascade2_loaded
    assert health.mode.value == "llm_assisted"


def test_rule_packs_have_deterministic_checks():
    inspector = ExcelInspector()
    assert len(inspector.loader.rules_for("tables101")) >= 17
    assert len(inspector.loader.rules_for("charts101")) >= 17
