"""Source-level compat tests for the Streamlit UI (R2-T3).

These assert the UI keeps the behaviours that protect persisted legacy
findings and the D1/D2 demo fixes. They read app/main.py as text — no
running Streamlit server required.
"""
from pathlib import Path

MAIN_PY = (Path(__file__).parents[1] / "app" / "main.py").read_text()


def test_findings_ui_supports_legacy_persisted_findings():
    """Persisted findings are revalidated against the active workbook
    (resolve_affected_cells semantics now live in app/fix_flow.py)."""
    assert "revalidate_findings(" in MAIN_PY


def test_ui_uses_state_module_for_finding_selection():
    assert "ui_state.get_active_finding" in MAIN_PY
    assert "ui_state.set_active_finding" in MAIN_PY


def test_ui_uses_seamless_save_flow():
    assert "apply_fix(" in MAIN_PY
    assert "ui_state.set_last_apply_result" in MAIN_PY
    # The old manual re-upload instruction is gone
    assert "then upload as next revision" not in MAIN_PY


def test_ui_guards_uploads():
    assert "guard_upload(" in MAIN_PY
    assert 'st.error(t(lang, "upload_error"))' in MAIN_PY


def test_no_stacked_expander_navigation():
    """D1: the old per-finding stacked-expander render is replaced by
    one-active-finding navigation."""
    assert "for f in revision.findings[:200]" not in MAIN_PY
    assert 'with st.expander(\n                    f"[{f.severity' not in MAIN_PY


def test_next_open_finding_action_present():
    assert '"next_open_finding"' in MAIN_PY
