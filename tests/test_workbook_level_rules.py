"""Regression guard: workbook-level rules (gridlines, source-presence,
table-per-sheet) fire on fresh inspection with EMPTY affected-cell lists.
They are still open problems — they must never be classified as
"resolved by iteration" merely because they carry no cell coordinates.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.project_store import ProjectStore
from core.repository_client import RepositoryClient
from core.excel_inspector import ExcelInspector
from core.translation_manager import TranslationManager, PassthroughTranslator

from app.fix_flow import revalidate_findings


@pytest.fixture()
def failing_project(tmp_path):
    repo = RepositoryClient(root_path=str(tmp_path / "repo"))
    store = ProjectStore(
        repo=repo,
        inspector=ExcelInspector(),
        translator=TranslationManager(translator=PassthroughTranslator()),
    )
    project = store.create_project(label="Workbook-level rules", reviewer="Tester")
    fixture = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "fixtures", "test_cases", "t101_fail_all.xlsx")
    revision = store.add_workbook_revision(
        project, fixture, original_filename="t101_fail_all.xlsx",
        uploaded_by="Tester", language="en",
    )
    workbook_dir = os.path.join(repo.root_path, "reviews",
                                project.project_id, "workbooks")
    return store, project, revision, workbook_dir


def test_workbook_level_rules_are_not_resolved_by_empty_cell_list(failing_project):
    store, project, revision, workbook_dir = failing_project
    active = os.path.join(workbook_dir, revision.stored_filename)

    # Sanity: the fresh engine does fire the workbook-level rule with no cells
    insp = ExcelInspector()
    fresh = insp.inspect_workbook(active)
    grid = next(f for f in fresh if f.rule_id == "T101-GRIDLINES-ON")
    assert grid.affected_cells == [], "precondition: workbook-level rule has no cells"

    entries = revalidate_findings(revision.findings, str(active))
    grid_entry = next(e for e in entries
                      if e["finding"].rule_id == "T101-GRIDLINES-ON")
    assert grid_entry["resolved"] is False, (
        "an open workbook-level finding must not be shown as resolved"
    )
    assert grid_entry["affected_cells"] == []


def test_cell_level_still_resolves_when_rule_stops_firing(failing_project):
    store, project, revision, workbook_dir = failing_project
    from core.iteration_lineage import current_workbook
    from app.fix_flow import apply_fix

    finding = next(f for f in revision.findings
                   if f.rule_id == "T101-NO-EMPTY-CELLS")
    # Fix every affected cell, one iteration per fix
    for cell in list(finding.affected_cells):
        rev = project.latest_revision()
        f = next(x for x in rev.findings if x.rule_id == "T101-NO-EMPTY-CELLS")
        outcome = apply_fix(store, project, rev, f, "select_symbol", "..", cell,
                            workbook_dir, "en")
        assert outcome["success"] is True, outcome

    active = str(current_workbook(workbook_dir, revision.original_filename,
                                  revision.stored_filename))
    entries = revalidate_findings(revision.findings, active)
    entry = next(e for e in entries if e["finding"].rule_id == "T101-NO-EMPTY-CELLS")
    assert entry["resolved"] is True
    assert entry["affected_cells"] == []


def test_rename_sheet_rejects_invalid_sheet_characters(failing_project):
    """User-supplied sheet names flow into ws.title; Excel forbids : \\ / ? * [ ]
    and >31 chars. The applier must refuse them with a friendly message, not
    crash with an openpyxl ValueError."""
    store, project, revision, workbook_dir = failing_project
    from app.fix_flow import apply_fix
    finding = next(f for f in revision.findings
                   if f.rule_id == "T101-ONE-TABLE-PER-SHEET")
    outcome = apply_fix(store, project, revision, finding,
                        "rename_sheet", "bad:name", None, workbook_dir, "en")
    assert outcome["success"] is False
    assert "message" in outcome and outcome["message"]


def test_rename_sheet_rejects_too_long_name(failing_project):
    store, project, revision, workbook_dir = failing_project
    from app.fix_flow import apply_fix
    finding = next(f for f in revision.findings
                   if f.rule_id == "T101-ONE-TABLE-PER-SHEET")
    outcome = apply_fix(store, project, revision, finding,
                        "rename_sheet", "x" * 40, None, workbook_dir, "en")
    assert outcome["success"] is False


def test_rename_sheet_accepts_valid_name(failing_project):
    store, project, revision, workbook_dir = failing_project
    from app.fix_flow import apply_fix
    finding = next(f for f in revision.findings
                   if f.rule_id == "T101-ONE-TABLE-PER-SHEET")
    outcome = apply_fix(store, project, revision, finding,
                        "rename_sheet", "tbl_fail", None, workbook_dir, "en")
    assert outcome["success"] is True, outcome


def test_failed_apply_leaves_no_iteration_file(failing_project):
    """A refused remediation must not leave a phantom iteration file behind
    (the copy happens inside the applier before validation)."""
    store, project, revision, workbook_dir = failing_project
    from app.fix_flow import apply_fix
    finding = next(f for f in revision.findings
                   if f.rule_id == "T101-ONE-TABLE-PER-SHEET")
    before = set(os.listdir(workbook_dir))
    outcome = apply_fix(store, project, revision, finding,
                        "rename_sheet", "bad:name", None, workbook_dir, "en")
    assert outcome["success"] is False
    after = set(os.listdir(workbook_dir))
    assert after == before, f"phantom files left: {after - before}"
    assert not any(p.startswith("iteration_") for p in after - before)
