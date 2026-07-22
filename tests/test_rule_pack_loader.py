import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rule_pack_loader import RulePackLoader

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")


def test_loads_both_packs():
    loader = RulePackLoader(CONFIG_DIR)
    assert loader.rules_for("tables101")
    assert loader.rules_for("charts101")


def test_rule_by_id_lookup():
    loader = RulePackLoader(CONFIG_DIR)
    rule = loader.rule_by_id("T101-NO-EMPTY-CELLS")
    assert rule.severity == "error"
    assert rule.title_fr


def test_standard_symbols_loaded():
    loader = RulePackLoader(CONFIG_DIR)
    symbols = loader.standard_symbols()
    assert "symbols" in symbols
    assert len(symbols["symbols"]) >= 5
