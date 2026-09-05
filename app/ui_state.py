"""Pure session-state logic for the reviewer UI (R2-T1 / spec FR-8).

All functions accept a session-like mapping (Streamlit's st.session_state
behaves like one). When no session is injected, Streamlit's session state is
used if available; otherwise an in-process fallback dict keeps the module
importable outside a Streamlit runtime (tests, CLI tooling).

No business logic lives here beyond UI state; domain sequencing belongs to
app/fix_flow.py.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

_ACTIVE_FINDING_KEY = "active_finding_id"
_LAST_APPLY_KEY = "last_apply_result"
_fallback_session: Dict[str, Any] = {}


def _session(session=None):
    if session is not None:
        return session
    try:
        import streamlit as st

        return st.session_state
    except Exception:
        return _fallback_session


# ---- Active finding selection (RH1 / FR-1) ---------------------------

def get_active_finding(session=None) -> Optional[str]:
    value = _session(session).get(_ACTIVE_FINDING_KEY)
    return value if value else None


def set_active_finding(session, finding_id: str) -> None:
    _session(session)[_ACTIVE_FINDING_KEY] = finding_id


def clear_active_finding(session=None) -> None:
    _session(session).pop(_ACTIVE_FINDING_KEY, None)


# ---- Last apply result (RH2 / FR-3c) ----------------------------------

def get_last_apply_result(session=None) -> Optional[Dict[str, Any]]:
    value = _session(session).get(_LAST_APPLY_KEY)
    return value if value else None


def set_last_apply_result(session, result: Dict[str, Any]) -> None:
    _session(session)[_LAST_APPLY_KEY] = dict(result)


def clear_last_apply_result(session=None) -> None:
    _session(session).pop(_LAST_APPLY_KEY, None)


# ---- Auto-revision audit note (FR-3b) ---------------------------------

def _option_clause(option_id: str, label: str) -> str:
    return f' for "{label}" [{option_id}]' if label else f" [{option_id}]"


def auto_revision_note(finding_id: str, rule_id: str, option_id: str,
                       option_label_en: str, option_label_fr: str,
                       iteration_name: str, lang: str = "en") -> str:
    """Bilingual deterministic audit note naming finding, rule, option and
    iteration. Single source of wording — app/fix_flow.py delegates here.
    """
    label = option_label_en if lang == "en" else (option_label_fr or option_label_en)
    clause = _option_clause(option_id, label)
    if lang == "en":
        return (f"Applied deterministic fix for finding {finding_id} "
                f"({rule_id}){clause}. Workbook iteration {iteration_name} "
                f"created and promoted to this revision.")
    return (f"Correction déterministe appliquée pour le constat "
            f"{finding_id} ({rule_id}){clause}. L'itération {iteration_name} "
            f"du classeur a été créée et promue comme présente révision.")
