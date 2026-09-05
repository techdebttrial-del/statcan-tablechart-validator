"""Unit tests for the pure session-state module (R2-T1 / spec FR-8).

Streamlit is never imported: a plain dict stands in for st.session_state.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import ui_state


def test_active_finding_roundtrip():
    session = {}
    assert ui_state.get_active_finding(session) is None
    ui_state.set_active_finding(session, "FND-1")
    assert ui_state.get_active_finding(session) == "FND-1"


def test_active_finding_clear():
    session = {}
    ui_state.set_active_finding(session, "FND-1")
    ui_state.clear_active_finding(session)
    assert ui_state.get_active_finding(session) is None


def test_last_apply_result_roundtrip_and_clear():
    session = {}
    assert ui_state.get_last_apply_result(session) is None
    result = {
        "finding_id": "FND-1", "rule_id": "T101-NO-EMPTY-CELLS",
        "option_id": "select_symbol", "iteration_name": "iteration_01_x.xlsx",
        "commit_id": "abc123", "revision_number": 2,
    }
    ui_state.set_last_apply_result(session, result)
    got = ui_state.get_last_apply_result(session)
    assert got == result
    ui_state.clear_last_apply_result(session)
    assert ui_state.get_last_apply_result(session) is None


def test_auto_revision_note_en_names_all_parts():
    note = ui_state.auto_revision_note(
        finding_id="FND-1", rule_id="T101-NO-EMPTY-CELLS",
        option_id="select_symbol",
        option_label_en="Use an approved StatCan symbol",
        option_label_fr="Utiliser un symbole approuvé de StatCan",
        iteration_name="iteration_01_FND-1_t101.xlsx", lang="en",
    )
    assert "FND-1" in note
    assert "T101-NO-EMPTY-CELLS" in note
    assert "select_symbol" in note
    assert "iteration_01_FND-1_t101.xlsx" in note
    assert "approved StatCan symbol" in note


def test_auto_revision_note_fr():
    note = ui_state.auto_revision_note(
        finding_id="FND-1", rule_id="T101-NO-EMPTY-CELLS",
        option_id="select_symbol",
        option_label_en="Use an approved StatCan symbol",
        option_label_fr="Utiliser un symbole approuvé de StatCan",
        iteration_name="iteration_01_FND-1_t101.xlsx", lang="fr",
    )
    assert "FND-1" in note
    assert "symbole approuvé" in note


def test_auto_revision_note_matches_fix_flow_note():
    """ui_state note and fix_flow note must agree (single source of wording)."""
    from app import fix_flow
    kwargs = dict(
        finding_id="FND-2", rule_id="C101-SIZE-WIDTH", option_id="resize_chart",
        option_label_en="Resize the chart", option_label_fr="Redimensionner le graphique",
        iteration_name="iteration_03_FND-2_c101.xlsx", lang="fr",
    )
    assert ui_state.auto_revision_note(**kwargs) == \
        fix_flow._auto_revision_note(
            type("F", (), {"finding_id": "FND-2", "rule_id": "C101-SIZE-WIDTH"})(),
            "resize_chart", "Resize the chart", "Redimensionner le graphique",
            "iteration_03_FND-2_c101.xlsx", "fr",
        )


def test_default_session_uses_streamlit_when_present():
    """Without an injected session, functions fall back to st.session_state."""
    import types
    fake_st = types.ModuleType("streamlit")
    fake_st.session_state = {}
    sys.modules["streamlit"] = fake_st
    try:
        ui_state.set_active_finding(None, "FND-9")
        assert fake_st.session_state["active_finding_id"] == "FND-9"
        assert ui_state.get_active_finding(None) == "FND-9"
    finally:
        del sys.modules["streamlit"]
