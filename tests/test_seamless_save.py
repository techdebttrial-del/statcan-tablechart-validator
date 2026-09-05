"""Seamless-save integration tests (R2-T4 / spec FR-3, RH2).

Exercises the real deterministic pipeline: ProjectStore +
InMemoryRepositoryClient + real fixture workbook. No Streamlit, no mocks of
the domain logic.
"""
import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.project_store import ProjectStore
from core.repository_client import RepositoryClient
from core.excel_inspector import ExcelInspector
from core.translation_manager import TranslationManager, PassthroughTranslator
from core.models import ReplacementReason, FindingStatus
from core.iteration_lineage import current_workbook, latest_iteration
from core.remediation_catalog import remediation_options

from app.fix_flow import apply_fix, revalidate_findings, compute_status_panel, guard_upload


@pytest.fixture()
def env(tmp_path):
    """A project with one failing revision, using the REAL repository client
    against a throwaway git root — the same wiring as production
    (app/services.py), just rooted in a tmpdir."""
    repo_root = str(tmp_path / "repo")
    repo = RepositoryClient(root_path=repo_root)
    store = ProjectStore(
        repo=repo,
        inspector=ExcelInspector(),
        translator=TranslationManager(translator=PassthroughTranslator()),
    )
    project = store.create_project(label="Seamless save", reviewer="Tester")
    fixture = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "fixtures", "test_cases", "t101_fail_all.xlsx",
    )
    revision = store.add_workbook_revision(
        project, fixture, original_filename="t101_fail_all.xlsx",
        uploaded_by="Tester", language="en",
    )
    workbook_dir = os.path.join(repo_root, "reviews", project.project_id, "workbooks")
    return store, repo, project, revision, fixture, workbook_dir


def _empty_cell_finding(revision):
    return next(f for f in revision.findings if f.rule_id == "T101-NO-EMPTY-CELLS")


def test_apply_fix_creates_iteration_commit_and_revision(env):
    store, repo, project, revision, fixture, workbook_dir = env
    finding = _empty_cell_finding(revision)

    outcome = apply_fix(
        store, project, revision, finding,
        option_id="select_symbol", value="..",
        target_cell=finding.affected_cells[0],
        workbook_dir=workbook_dir, lang="en",
    )

    assert outcome["success"] is True
    assert outcome["iteration_name"].startswith("iteration_01_")
    assert outcome["commit_id"]
    # Auto-revision was created from the iteration
    assert outcome["revision_number"] == 2
    new_revision = project.latest_revision()
    assert new_revision.revision_number == 2
    assert new_revision.replacement_reason == ReplacementReason.CORRECTED_DATA
    # Audit note names finding, rule and iteration
    note_text = new_revision.replacement_note.original_text
    assert finding.finding_id in note_text
    assert finding.rule_id in note_text
    assert outcome["iteration_name"] in note_text


def test_apply_fix_preserves_original_and_prior_iterations(env):
    store, repo, project, revision, fixture, workbook_dir = env
    finding = _empty_cell_finding(revision)
    original_path = os.path.join(workbook_dir, revision.stored_filename)
    original_bytes = open(original_path, "rb").read()

    outcome1 = apply_fix(store, project, revision, finding,
                         "select_symbol", "..", finding.affected_cells[0],
                         workbook_dir, "en")
    assert outcome1["success"] is True, outcome1
    iter1 = os.path.join(workbook_dir, outcome1["iteration_name"])
    iter1_bytes = open(iter1, "rb").read()

    # Second fix on the new revision
    revision2 = project.latest_revision()
    finding2 = _empty_cell_finding(revision2)
    assert finding2.affected_cells, "second fix needs a remaining affected cell"
    outcome2 = apply_fix(store, project, revision2, finding2,
                         "select_symbol", "..", finding2.affected_cells[0],
                         workbook_dir, "en")
    assert outcome2["success"] is True, outcome2

    # Original untouched, iteration 1 untouched, iteration 2 distinct
    assert open(original_path, "rb").read() == original_bytes
    assert open(iter1, "rb").read() == iter1_bytes
    assert outcome2["iteration_name"] != outcome1["iteration_name"]
    assert outcome2["revision_number"] == 3


def test_revalidate_marks_fixed_finding_resolved(env):
    store, repo, project, revision, fixture, workbook_dir = env
    finding = _empty_cell_finding(revision)

    fixed_cell = finding.affected_cells[0]
    outcome = apply_fix(store, project, revision, finding,
                        "select_symbol", "..", fixed_cell, workbook_dir, "en")
    assert outcome["success"] is True, outcome

    active = current_workbook(workbook_dir, revision.original_filename,
                              revision.stored_filename)
    reval = revalidate_findings(revision.findings, str(active))

    fixed_entry = next(e for e in reval if e["finding"].finding_id == finding.finding_id)
    # One cell fixed; remaining empties keep the rule open with fewer cells
    assert fixed_entry["resolved"] is False
    assert fixed_cell not in fixed_entry["affected_cells"]
    assert len(fixed_entry["affected_cells"]) == len(finding.affected_cells) - 1


def test_revalidate_resolved_when_no_cells_remain(env):
    store, repo, project, revision, fixture, workbook_dir = env
    finding = _empty_cell_finding(revision)

    # Fix every empty cell of this finding, one fix per iteration
    rev = revision
    remaining = list(finding.affected_cells)
    for cell in remaining:
        rev = project.latest_revision()
        f = _empty_cell_finding(rev)
        outcome = apply_fix(store, project, rev, f, "select_symbol", "..", cell,
                            workbook_dir, "en")
        assert outcome["success"] is True, outcome

    active = current_workbook(workbook_dir, revision.original_filename,
                              revision.stored_filename)
    reval = revalidate_findings(revision.findings, str(active))
    fixed_entry = next(e for e in reval if e["finding"].finding_id == finding.finding_id)
    assert fixed_entry["resolved"] is True
    assert fixed_entry["affected_cells"] == []


def test_status_panel_counts(env):
    store, repo, project, revision, fixture, workbook_dir = env
    panel = compute_status_panel(project, revision)
    assert panel["revision_number"] == 1
    assert panel["compliance"] == revision.compliance_status.value
    assert panel["open_count"] == sum(
        1 for f in revision.findings if f.status == FindingStatus.OPEN)
    assert panel["total_findings"] == len(revision.findings)


def test_guard_upload_rejects_corrupt_file(env):
    store, repo, project, revision, fixture, workbook_dir = env
    tmpdir = tempfile.mkdtemp()
    corrupt = os.path.join(tmpdir, "corrupt.xlsx")
    with open(corrupt, "wb") as fh:
        fh.write(b"this is not an excel file at all")
    try:
        new_revision, error = guard_upload(
            store, project, corrupt,
            original_filename="corrupt.xlsx", uploaded_by="Tester",
            language="en",
        )
        assert new_revision is None
        assert error == "upload_error"
    finally:
        shutil.rmtree(tmpdir)


def test_guard_upload_accepts_valid_file(env):
    store, repo, project, revision, fixture, workbook_dir = env
    new_revision, error = guard_upload(
        store, project, fixture,
        original_filename="t101_fail_all.xlsx", uploaded_by="Tester",
        language="en",
    )
    assert error is None
    assert new_revision is not None
    assert new_revision.revision_number == 2
