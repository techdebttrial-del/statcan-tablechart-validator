"""Deterministic fix-flow logic for the reviewer UI (R2-T4/T5).

Pure domain orchestration — no Streamlit imports — so the seamless-save,
revalidation, status-panel and upload-guard behaviours are unit-testable.
The UI layer (app/main.py) calls these functions and renders the results.

Everything here is deterministic: no LLM, no guessing. Mutations always
create a NEW immutable iteration; the original workbook and earlier
iterations are never modified.
"""
from __future__ import annotations

import os
import tempfile
import zipfile
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.utils.exceptions import InvalidFileException

from core.excel_inspector import ExcelInspector
from core.iteration_lineage import current_workbook, next_iteration
from core.models import ReplacementReason
from core.remediation_applier import apply_remediation, resolve_affected_cells
from core.remediation_catalog import remediation_options
from app import ui_state


def apply_fix(store, project, revision, finding,
              option_id: str, value: Optional[str], target_cell: Optional[str],
              workbook_dir: str, lang: str = "en",
              option_label_en: str = "", option_label_fr: str = "") -> Dict[str, Any]:
    """Apply one approved deterministic fix and advance the workflow.

    Sequence (spec FR-3):
    1. create the next immutable iteration from the CURRENT workbook base;
    2. apply the remediation to the selected cell only;
    3. commit the iteration file to the repository;
    4. create the next revision from that iteration with an audit note
       (replacement_reason=CORRECTED_DATA) naming finding, rule, option and
       iteration;
    5. return a result dict for the UI to persist in session state.

    On failure: no partial state — returns success=False with a message.
    """
    # The ROOT original filename is the single lineage key. Auto-created
    # revisions keep it so current_workbook/latest_iteration keep resolving
    # the whole iteration chain (chaining iteration names into the key would
    # orphan every iteration after the first).
    root_name = (project.revisions[0].original_filename
                 if project.revisions else revision.original_filename)
    source_path = str(current_workbook(workbook_dir, root_name,
                                       revision.stored_filename))
    output_obj = next_iteration(workbook_dir, root_name, finding.finding_id)
    output_path = str(output_obj)

    result = apply_remediation(source_path, output_path, finding, option_id,
                               value, target_cell)
    if not result.success:
        return {"success": False, "message": result.message}

    relative_output = f"reviews/{project.project_id}/workbooks/{output_obj.name}"
    with open(output_path, "rb") as generated:
        commit = store.repo.put_file(
            relative_output, generated.read(),
            commit_message=f"Create workbook iteration for {finding.finding_id}",
        )

    # Next revision is generated FROM the iteration, never re-uploaded by hand.
    note_text = _auto_revision_note(finding, option_id, option_label_en,
                                    option_label_fr, output_obj.name, lang)
    new_revision = store.add_workbook_revision(
        project, output_path,
        original_filename=root_name,
        uploaded_by=project.reviewer,
        language=revision.language,
        replacement_reason=ReplacementReason.CORRECTED_DATA,
        replacement_note_text=note_text,
        replacement_note_language=lang,
    )

    return {
        "success": True,
        "finding_id": finding.finding_id,
        "rule_id": finding.rule_id,
        "option_id": option_id,
        "iteration_name": output_obj.name,
        "commit_id": commit.commit_id,
        "revision_number": new_revision.revision_number,
    }


def _auto_revision_note(finding, option_id: str, option_label_en: str,
                        option_label_fr: str, iteration_name: str,
                        lang: str) -> str:
    """Bilingual audit note for the auto-created revision.
    Wording lives in app.ui_state.auto_revision_note (single source)."""
    return ui_state.auto_revision_note(
        finding_id=finding.finding_id, rule_id=finding.rule_id,
        option_id=option_id, option_label_en=option_label_en,
        option_label_fr=option_label_fr, iteration_name=iteration_name,
        lang=lang,
    )


def revalidate_findings(findings: list, active_workbook_path: str) -> List[Dict[str, Any]]:
    """Reconcile persisted findings with the ACTIVE workbook (spec FR-4).

    Returns one entry per persisted finding:
      {finding, affected_cells, resolved}
    where resolved means the rule no longer produces affected cells on the
    current workbook. The persisted finding objects are never mutated —
    they remain the audit record.

    Semantics:
    - rule still fires on the active workbook -> NOT resolved (regardless of
      how many per-cell locations it carries; workbook-level rules such as
      gridlines or source-presence legitimately have none), unless the
      finding was already decided (waived/rejected/...);
    - engine-owned rule (T101-*/C101-*) that no longer fires -> the finding
      was fixed by an iteration: resolved, no remaining cells;
    - legacy/foreign rule not observable by the engine -> fall back to the
      persisted coordinates and the finding's decision status.
    """
    refreshed = ExcelInspector().inspect_workbook(active_workbook_path)
    entries: List[Dict[str, Any]] = []
    for finding in findings:
        match = next((item for item in refreshed
                      if item.rule_id == finding.rule_id
                      and item.sheet_name == finding.sheet_name), None)
        decided = finding.status.value != "open"
        if match is not None:
            affected = list(getattr(match, "affected_cells", None) or [])
            resolved = decided
        elif finding.rule_id.startswith(("T101-", "C101-")):
            # Engine owns this rule and it no longer fires: fixed by iteration.
            affected = []
            resolved = True
        else:
            affected = list(getattr(finding, "affected_cells", None) or [])
            resolved = decided
        entries.append({
            "finding": finding,
            "affected_cells": affected,
            "resolved": resolved,
        })
    return entries


def compute_status_panel(project, revision) -> Dict[str, Any]:
    """Status-panel data always computed from the store (spec FR-6)."""
    findings = revision.findings if revision else []
    open_count = sum(1 for f in findings if f.status.value == "open")
    return {
        "revision_number": revision.revision_number if revision else None,
        "compliance": revision.compliance_status.value if revision else None,
        "open_count": open_count,
        "total_findings": len(findings),
        "resolved_count": len(findings) - open_count,
    }


_UPLOAD_ERRORS = (zipfile.BadZipFile, InvalidFileException, OSError, ValueError)


def guard_upload(store, project, tmp_path: str, original_filename: str,
                 uploaded_by: str, language: str,
                 replacement_reason=None, replacement_note_text: Optional[str] = None,
                 replacement_note_language: str = "en"
                 ) -> Tuple[Optional[object], Optional[str]]:
    """Add a workbook revision, catching malformed-file errors (spec FR-5).

    Returns (revision, None) on success or (None, "upload_error") on a
    malformed/unreadable file — the UI maps the sentinel to a bilingual
    message. A temp file is cleaned up by the caller.
    """
    try:
        revision = store.add_workbook_revision(
            project, tmp_path,
            original_filename=original_filename,
            uploaded_by=uploaded_by, language=language,
            replacement_reason=replacement_reason,
            replacement_note_text=replacement_note_text,
            replacement_note_language=replacement_note_language,
        )
        return revision, None
    except _UPLOAD_ERRORS:
        return None, "upload_error"


def workbook_language_guard(language: str) -> str:
    """Workbook language only affects the FR-NUMBER-FORMAT rule (spec A6)."""
    return language if language in ("en", "fr") else "en"
