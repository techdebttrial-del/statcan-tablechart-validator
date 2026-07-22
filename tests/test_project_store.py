import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.repository_client import InMemoryRepositoryClient
from core.project_store import ProjectStore
from core.models import DecisionType, DecisionReason, ReplacementReason, ProjectStatus

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_workbook.xlsx")


def make_store():
    return ProjectStore(repo=InMemoryRepositoryClient())


def test_create_project_has_auto_id_and_label():
    store = make_store()
    project = store.create_project(label="Labour Force Tables", reviewer="A. Reviewer")
    assert project.project_id.startswith("TVC-")
    assert project.label == "Labour Force Tables"


def test_add_workbook_revision_creates_findings_and_amendment():
    store = make_store()
    project = store.create_project(label="Test", reviewer="A. Reviewer")
    revision = store.add_workbook_revision(
        project, FIXTURE, original_filename="sample.xlsx", uploaded_by="A. Reviewer",
    )
    assert revision.revision_number == 1
    assert len(revision.findings) > 0
    assert len(project.amendments) == 1
    assert project.amendments[0].kind == "workbook_uploaded"


def test_replacement_revision_is_fresh_revalidation():
    store = make_store()
    project = store.create_project(label="Test", reviewer="A. Reviewer")
    rev1 = store.add_workbook_revision(
        project, FIXTURE, original_filename="sample.xlsx", uploaded_by="A. Reviewer",
    )
    rev2 = store.add_workbook_revision(
        project, FIXTURE, original_filename="sample_v2.xlsx", uploaded_by="A. Reviewer",
        replacement_reason=ReplacementReason.CORRECTED_DATA,
        replacement_note_text="Fixed missing cells.", replacement_note_language="en",
    )
    assert rev2.revision_number == 2
    assert rev2.parent_revision_id == rev1.revision_id
    assert rev2.replacement_note is not None
    assert rev2.replacement_note.original_text == "Fixed missing cells."
    assert len(rev2.findings) > 0


def test_record_decision_updates_finding_status():
    store = make_store()
    project = store.create_project(label="Test", reviewer="A. Reviewer")
    revision = store.add_workbook_revision(
        project, FIXTURE, original_filename="sample.xlsx", uploaded_by="A. Reviewer",
    )
    finding = revision.findings[0]
    store.record_decision(
        project, revision, finding.finding_id,
        decision_type=DecisionType.WAIVED, reason=DecisionReason.EXCEPTION_APPROVED,
        note_text="Approved exception for this publication.", note_language="en",
        reviewer="A. Reviewer", target_resolution_date="2026-08-01",
    )
    updated = [f for f in revision.findings if f.finding_id == finding.finding_id][0]
    assert updated.status.value == "pending_correction"
    assert len(project.decisions) == 1
    assert project.decisions[0].note.translation is not None
    assert project.decisions[0].note.translation.is_machine_translation is True


def test_close_and_reopen_project():
    store = make_store()
    project = store.create_project(label="Test", reviewer="A. Reviewer")
    store.close_project(project, actor="A. Reviewer", note_text="Done.", note_language="en")
    assert project.status == ProjectStatus.CLOSED
    store.reopen_project(project, actor="A. Reviewer")
    assert project.status == ProjectStatus.OPEN
