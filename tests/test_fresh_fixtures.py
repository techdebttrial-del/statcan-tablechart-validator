"""Tests for fresh fixture workbooks modeled on recent StatCan Daily releases.

These fixtures were engineered with deliberate failures to validate the
deterministic rule engine against realistic publication patterns.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.excel_inspector import ExcelInspector

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "test_cases")
inspector = ExcelInspector()


def _findings_for(filename):
    path = os.path.join(FIXTURES, filename)
    return inspector.inspect_workbook(path)


def _rule_ids(findings):
    return {f.rule_id for f in findings}


# ─── Fresh table fixtures ────────────────────────────────────────────

class TestDailyRetail2026:
    """Retail Trade Daily fixture — modeled on StatCan Daily Aug 2026."""

    def test_produces_findings(self):
        findings = _findings_for("daily_retail_2026.xlsx")
        assert len(findings) > 0

    def test_gridlines_off_detected(self):
        ids = _rule_ids(_findings_for("daily_retail_2026.xlsx"))
        assert "T101-GRIDLINES-ON" in ids

    def test_formula_detected(self):
        ids = _rule_ids(_findings_for("daily_retail_2026.xlsx"))
        assert "T101-NO-FORMULAS" in ids

    def test_color_fill_detected(self):
        ids = _rule_ids(_findings_for("daily_retail_2026.xlsx"))
        assert "T101-NO-COLOR-FILL" in ids

    def test_row_span_detected(self):
        ids = _rule_ids(_findings_for("daily_retail_2026.xlsx"))
        assert "T101-AVOID-ROW-SPANNING" in ids

    def test_indent_detected(self):
        ids = _rule_ids(_findings_for("daily_retail_2026.xlsx"))
        assert "T101-INDENT-FEATURE" in ids

    def test_no_source_detected(self):
        ids = _rule_ids(_findings_for("daily_retail_2026.xlsx"))
        assert "T101-SOURCE-PRESENT" in ids

    def test_wrong_sheet_name_detected(self):
        ids = _rule_ids(_findings_for("daily_retail_2026.xlsx"))
        assert "T101-ONE-TABLE-PER-SHEET" in ids


class TestDailyGDPQ2_2026:
    """GDP by Industry Quarterly fixture — low-severity failures."""

    def test_produces_findings(self):
        findings = _findings_for("daily_gdp_q2_2026.xlsx")
        assert len(findings) >= 2

    def test_gridlines_off_detected(self):
        ids = _rule_ids(_findings_for("daily_gdp_q2_2026.xlsx"))
        assert "T101-GRIDLINES-ON" in ids

    def test_abbreviations_detected(self):
        ids = _rule_ids(_findings_for("daily_gdp_q2_2026.xlsx"))
        assert "T101-FULL-TEXT-OVER-SYMBOLS" in ids

    def test_no_empty_cells(self):
        """GDP fixture should have no empty data cells — all are filled."""
        ids = _rule_ids(_findings_for("daily_gdp_q2_2026.xlsx"))
        assert "T101-NO-EMPTY-CELLS" not in ids


# ─── Fresh chart fixtures ─────────────────────────────────────────────

class TestDailyCPIChart2026:
    """CPI chart fixture — modeled on StatCan Daily CPI Aug 2026."""

    def test_produces_findings(self):
        findings = _findings_for("daily_cpi_chart_2026.xlsx")
        assert len(findings) > 0

    def test_max_six_series_detected(self):
        ids = _rule_ids(_findings_for("daily_cpi_chart_2026.xlsx"))
        assert "C101-MAX-SIX-SERIES" in ids

    def test_title_superscript_detected(self):
        ids = _rule_ids(_findings_for("daily_cpi_chart_2026.xlsx"))
        assert "C101-NO-TITLE-SUPERSCRIPT" in ids

    def test_size_width_detected(self):
        ids = _rule_ids(_findings_for("daily_cpi_chart_2026.xlsx"))
        assert "C101-SIZE-WIDTH" in ids

    def test_size_height_detected(self):
        ids = _rule_ids(_findings_for("daily_cpi_chart_2026.xlsx"))
        assert "C101-SIZE-HEIGHT-MIN" in ids


class TestDailyEmploymentChart2026:
    """Employment chart fixture — should pass cleanly (0 findings)."""

    def test_zero_findings(self):
        findings = _findings_for("daily_employment_chart_2026.xlsx")
        assert len(findings) == 0

    def test_compliant(self):
        """A well-formed chart should not trigger any rules."""
        findings = _findings_for("daily_employment_chart_2026.xlsx")
        for f in findings:
            assert f.severity.value not in ("error", "critical"), \
                f"Unexpected blocking finding: {f.rule_id}"


# ─── Cross-fixture consistency ────────────────────────────────────────

class TestFreshFixtureConsistency:
    """Verify deterministic results are stable across runs."""

    def test_retail_count_stable(self):
        f1 = _findings_for("daily_retail_2026.xlsx")
        f2 = _findings_for("daily_retail_2026.xlsx")
        assert len(f1) == len(f2)
        assert _rule_ids(f1) == _rule_ids(f2)

    def test_cpi_chart_count_stable(self):
        f1 = _findings_for("daily_cpi_chart_2026.xlsx")
        f2 = _findings_for("daily_cpi_chart_2026.xlsx")
        assert len(f1) == len(f2)
        assert _rule_ids(f1) == _rule_ids(f2)

    def test_employment_chart_zero_stable(self):
        f1 = _findings_for("daily_employment_chart_2026.xlsx")
        f2 = _findings_for("daily_employment_chart_2026.xlsx")
        assert len(f1) == 0
        assert len(f2) == 0
