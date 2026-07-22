"""
Comprehensive ProjectStore tests — round-trip serialization, compliance
recomputation, decision edge cases, and audit trail integrity.
"""
import os
import sys
import json
import tempfile

import pytest
import openpyxl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.repository_client import InMemoryRepositoryClient, RepositoryClient
from core.project_store import ProjectStore
from core.models import (
    DecisionType, DecisionReason, ReplacementReason, ProjectStatus,
    ComplianceStatus, FindingStatus, Severity,
)
from core.rule_pack_loader import RulePackLoader

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_WORKBOOK = os.path.join(FIXTURES_DIR, "sample_workbook.xlsx")


def _make_workbook(path, has_source=True, has_formulas=False, has_fill=False):
    """Create a minimal valid workbook at the given path."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "tbl1"
    ws["A1"] = "Category"
    ws["B1"] = "Value"
    ws["A2"] = "Row1"
    ws["B2"] = 100
    ws["A3"] = "Row2"
    ws["B3"] = 200
    if has_source:
        ws["A4"] = "Source: Test Survey"
        ws["A5"] = "x = suppressed"
        ws["A6"] = "Unit of measure: thousands"
    if has_formulas:
        ws["B2"] = "=SUM(1,2)"
    if has_fill:
        from openpyxl.styles import PatternFill
        ws["B2"].fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    wb.save(path)


def _make_store():
    return ProjectStore(repo=InMemoryRepositoryClient())


# ---------------------------------------------------------------------------
# Project creation and lifecycle
# ---------------------------------------------------------------------------

class TestProjectLifecycle:
    def test_create_project_generates_tvc_id(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        assert p.project_id.startswith("TVC-")
        assert len(p.project_id) > 4  # TVC- prefix + date + hex

    def test_create_project_stores_label_and_reviewer(self):
        store = _make_store()
        p = store.create_project(label="Labour Force Survey", reviewer="Dr. Smith")
        assert p.label == "Labour Force Survey"
        assert p.reviewer == "Dr. Smith"
        assert p.status == ProjectStatus.OPEN

    def test_list_projects_returns_sorted_by_updated(self):
        store = _make_store()
        p1 = store.create_project(label="First", reviewer="A")
        p2 = store.create_project(label="Second", reviewer="B")
        projects = store.list_projects()
        assert len(projects) == 2
        # Most recently updated first
        assert projects[0].project_id == p2.project_id

    def test_rename_project_records_amendment(self):
        store = _make_store()
        p = store.create_project(label="Old Name", reviewer="A")
        store.rename_project(p, "New Name", actor="A")
        assert p.label == "New Name"
        assert any(a.kind == "label_changed" for a in p.amendments)

    def test_close_project_sets_status_and_records_amendment(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        store.close_project(p, actor="A", note_text="All done.", note_language="en")
        assert p.status == ProjectStatus.CLOSED
        assert p.closed_at is not None
        assert p.closed_by == "A"
        assert p.closing_note is not None

    def test_reopen_project_after_close(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        store.close_project(p, actor="A")
        assert p.status == ProjectStatus.CLOSED
        store.reopen_project(p, actor="A")
        assert p.status == ProjectStatus.OPEN

    def test_close_without_note(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        store.close_project(p, actor="A")
        assert p.status == ProjectStatus.CLOSED
        assert p.closing_note is None


# ---------------------------------------------------------------------------
# Workbook revisions
# ---------------------------------------------------------------------------

class TestWorkbookRevisions:
    def test_first_revision_is_numbered_1(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name)
            rev = store.add_workbook_revision(p, f.name, "test.xlsx", "A")
            assert rev.revision_number == 1
            assert rev.parent_revision_id is None
            os.unlink(f.name)

    def test_second_revision_is_numbered_2_and_has_parent(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name)
            rev1 = store.add_workbook_revision(p, f.name, "v1.xlsx", "A")
            rev2 = store.add_workbook_revision(p, f.name, "v2.xlsx", "A")
            assert rev2.revision_number == 2
            assert rev2.parent_revision_id == rev1.revision_id
            os.unlink(f.name)

    def test_sha256_is_computed(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name)
            rev = store.add_workbook_revision(p, f.name, "test.xlsx", "A")
            assert len(rev.sha256) == 64  # SHA-256 hex digest
            assert all(c in "0123456789abcdef" for c in rev.sha256)
            os.unlink(f.name)

    def test_findings_are_populated(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name)
            rev = store.add_workbook_revision(p, f.name, "test.xlsx", "A")
            assert isinstance(rev.findings, list)
            assert len(rev.findings) > 0
            os.unlink(f.name)

    def test_replacement_with_reason_and_note(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name)
            rev1 = store.add_workbook_revision(p, f.name, "v1.xlsx", "A")
            rev2 = store.add_workbook_revision(
                p, f.name, "v2.xlsx", "A",
                replacement_reason=ReplacementReason.CORRECTED_DATA,
                replacement_note_text="Fixed missing data",
                replacement_note_language="en",
            )
            assert rev2.replacement_reason == ReplacementReason.CORRECTED_DATA
            assert rev2.replacement_note is not None
            assert rev2.replacement_note.original_text == "Fixed missing data"
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# Compliance status
# ---------------------------------------------------------------------------

class TestComplianceStatus:
    def test_compliant_when_no_blocking_findings(self):
        """A workbook with only warnings/info is compliant."""
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name, has_source=True)
            rev = store.add_workbook_revision(p, f.name, "test.xlsx", "A")
            # If no critical/error findings, should be compliant
            has_blocking = any(
                f.severity in (Severity.CRITICAL, Severity.ERROR)
                for f in rev.findings
            )
            if not has_blocking:
                assert rev.compliance_status == ComplianceStatus.COMPLIANT
            else:
                assert rev.compliance_status == ComplianceStatus.NOT_COMPLIANT
            os.unlink(f.name)

    def test_not_compliant_when_error_findings_open(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name, has_source=False)  # missing source → error
            rev = store.add_workbook_revision(p, f.name, "test.xlsx", "A")
            assert rev.compliance_status == ComplianceStatus.NOT_COMPLIANT
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# Decisions and compliance recomputation
# ---------------------------------------------------------------------------

class TestDecisions:
    def test_accepted_fix_resolves_finding(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name, has_source=False)
            rev = store.add_workbook_revision(p, f.name, "test.xlsx", "A")
            finding = rev.findings[0]
            store.record_decision(
                p, rev, finding.finding_id,
                decision_type=DecisionType.ACCEPTED_FIX,
                reason=DecisionReason.FALSE_POSITIVE,
                note_text="Fixed in v2",
                note_language="en",
                reviewer="A",
            )
            updated = [f for f in rev.findings if f.finding_id == finding.finding_id][0]
            assert updated.status == FindingStatus.ACCEPTED_FIX
            os.unlink(f.name)

    def test_rejected_sets_rejected_status(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name, has_source=False)
            rev = store.add_workbook_revision(p, f.name, "test.xlsx", "A")
            finding = rev.findings[0]
            store.record_decision(
                p, rev, finding.finding_id,
                decision_type=DecisionType.REJECTED,
                reason=DecisionReason.NOT_APPLICABLE,
                note_text="Not applicable",
                note_language="en",
                reviewer="A",
            )
            updated = [f for f in rev.findings if f.finding_id == finding.finding_id][0]
            assert updated.status == FindingStatus.REJECTED
            os.unlink(f.name)

    def test_waived_with_date_becomes_pending_correction(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name, has_source=False)
            rev = store.add_workbook_revision(p, f.name, "test.xlsx", "A")
            finding = rev.findings[0]
            store.record_decision(
                p, rev, finding.finding_id,
                decision_type=DecisionType.WAIVED,
                reason=DecisionReason.EXTERNAL_DEPENDENCY,
                note_text="Waiting for data",
                note_language="en",
                reviewer="A",
                target_resolution_date="2026-09-01",
            )
            updated = [f for f in rev.findings if f.finding_id == finding.finding_id][0]
            assert updated.status == FindingStatus.PENDING_CORRECTION
            os.unlink(f.name)

    def test_waived_without_date_becomes_permanently_waived(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name, has_source=False)
            rev = store.add_workbook_revision(p, f.name, "test.xlsx", "A")
            finding = rev.findings[0]
            store.record_decision(
                p, rev, finding.finding_id,
                decision_type=DecisionType.WAIVED,
                reason=DecisionReason.EXCEPTION_APPROVED,
                note_text="Approved exception",
                note_language="en",
                reviewer="A",
            )
            updated = [f for f in rev.findings if f.finding_id == finding.finding_id][0]
            assert updated.status == FindingStatus.PERMANENTLY_WAIVED
            os.unlink(f.name)

    def test_decision_creates_bilingual_note(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name, has_source=False)
            rev = store.add_workbook_revision(p, f.name, "test.xlsx", "A")
            finding = rev.findings[0]
            decision = store.record_decision(
                p, rev, finding.finding_id,
                decision_type=DecisionType.WAIVED,
                reason=DecisionReason.EXCEPTION_APPROVED,
                note_text="Approved exception for this cycle.",
                note_language="en",
                reviewer="A",
            )
            assert decision.note.original_text == "Approved exception for this cycle."
            assert decision.note.original_language == "en"
            assert decision.note.translation is not None
            assert decision.note.translation.target_language == "fr"
            assert decision.note.translation.is_machine_translation is True
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# JSON round-trip serialization
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_project_survives_json_round_trip(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name, has_source=False)
            rev = store.add_workbook_revision(p, f.name, "test.xlsx", "A")
            finding = rev.findings[0]
            store.record_decision(
                p, rev, finding.finding_id,
                decision_type=DecisionType.WAIVED,
                reason=DecisionReason.EXCEPTION_APPROVED,
                note_text="Note",
                note_language="en",
                reviewer="A",
                target_resolution_date="2026-10-01",
            )

            # Serialize and deserialize
            json_str = p.to_json()
            data = json.loads(json_str)
            assert data["project_id"] == p.project_id
            assert data["label"] == "Test"
            assert len(data["revisions"]) == 1
            assert len(data["decisions"]) == 1
            assert len(data["amendments"]) >= 2  # upload + decision

            # Load back through ProjectStore
            loaded = store._from_dict(data)
            assert loaded.project_id == p.project_id
            assert loaded.label == "Test"
            assert len(loaded.revisions) == 1
            assert loaded.revisions[0].revision_number == 1
            assert len(loaded.decisions) == 1
            assert loaded.decisions[0].decision_type == DecisionType.WAIVED
            assert loaded.decisions[0].target_resolution_date == "2026-10-01"
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# Amendment audit trail
# ---------------------------------------------------------------------------

class TestAmendmentAuditTrail:
    def test_amendments_record_all_actions(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name)
            store.add_workbook_revision(p, f.name, "test.xlsx", "A")
            store.rename_project(p, "New Label", actor="A")
            store.close_project(p, actor="A")

            kinds = [a.kind for a in p.amendments]
            assert "workbook_uploaded" in kinds
            assert "label_changed" in kinds
            assert "project_closed" in kinds
            os.unlink(f.name)

    def test_amendment_ids_are_unique(self):
        store = _make_store()
        p = store.create_project(label="Test", reviewer="A")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            _make_workbook(f.name)
            store.add_workbook_revision(p, f.name, "test.xlsx", "A")
            store.close_project(p, actor="A")
            ids = [a.amendment_id for a in p.amendments]
            assert len(ids) == len(set(ids))
            os.unlink(f.name)
