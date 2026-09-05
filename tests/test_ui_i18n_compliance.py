"""i18n compliance tests (R2-T2 / spec RH7, NFR-4).

1. EN/FR parity — every key exists in both languages.
2. t() fallback — unknown key returns the key itself.
3. Regression grep — hardcoded UI literals are banned from app/main.py.
   Literals not yet migrated to i18n are marked xfail(non-strict) and the
   xfail markers are removed by the task that migrates them.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.i18n import STRINGS, t

MAIN_PY = Path(__file__).parents[1] / "app" / "main.py"


def test_en_fr_key_parity():
    en_keys = set(STRINGS["en"].keys())
    fr_keys = set(STRINGS["fr"].keys())
    missing_in_fr = en_keys - fr_keys
    missing_in_en = fr_keys - en_keys
    assert not missing_in_fr, f"keys missing in FR: {sorted(missing_in_fr)}"
    assert not missing_in_en, f"keys missing in EN: {sorted(missing_in_en)}"


def test_t_fallback_returns_key():
    assert t("en", "definitely_not_a_key_12345") == "definitely_not_a_key_12345"
    assert t("fr", "definitely_not_a_key_12345") == "definitely_not_a_key_12345"
    # Unknown language falls back to English
    assert t("de", "findings") == STRINGS["en"]["findings"]


def test_r2_keys_present_both_languages():
    required = [
        "finding_detail", "next_open_finding", "back_to_list",
        "no_finding_selected", "status_panel_revision",
        "status_panel_compliance", "status_panel_open",
        "status_panel_resolved", "status_panel_workbook_base",
        "save_confirmation", "save_commited_as", "new_revision_created",
        "resolved_by_iteration", "upload_error", "compliant_panel",
        "download_original", "download_revised",
    ]
    for key in required:
        assert key in STRINGS["en"], f"{key} missing in EN"
        assert key in STRINGS["fr"], f"{key} missing in FR"
        assert STRINGS["en"][key].strip(), f"{key} EN empty"
        assert STRINGS["fr"][key].strip(), f"{key} FR empty"


# ---- Banned hardcoded literals in main.py (RH7) -----------------------

_BANNED = [
    "⬇ Download original workbook",
    "⬇ Download revised workbook",
    "Current workbook base:",
]


def _contains_literal(source: str, literal: str) -> bool:
    return literal in source


def test_no_hardcoded_download_strings():
    source = MAIN_PY.read_text()
    hits = [lit for lit in _BANNED if _contains_literal(source, lit)]
    assert not hits, f"hardcoded literals must route through i18n: {hits}"
