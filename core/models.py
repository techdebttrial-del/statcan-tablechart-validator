"""
Shared dataclasses for the StatCan Tables/Charts Validator.

Design note: this mirrors the ProjectState / Amendment pattern used in the
broader StatCan ESR Accelerator (core/project_state.py) so that this
standalone tool can be merged into that codebase later with minimal
refactoring. Field names and semantics are intentionally kept close to the
Accelerator's Amendment / ReviewComment conventions.
"""
from __future__ import annotations

import uuid
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str = "") -> str:
    suffix = uuid.uuid4().hex[:8].upper()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}{stamp}-{suffix}" if prefix else f"{stamp}-{suffix}"


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class Severity(str, Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ProjectStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NOT_COMPLIANT = "not_compliant"
    PENDING = "pending"


class DecisionType(str, Enum):
    ACCEPTED_FIX = "accepted_fix"
    REJECTED = "rejected"
    WAIVED = "waived"


class DecisionReason(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    FALSE_POSITIVE = "false_positive"
    SOURCE_MUST_REMAIN_UNCHANGED = "source_must_remain_unchanged"
    ALTERS_ANALYTICAL_MEANING = "alters_analytical_meaning"
    INFO_UNAVAILABLE_OR_PENDING = "info_unavailable_or_pending"
    EXCEPTION_APPROVED = "exception_approved"
    EXTERNAL_DEPENDENCY = "external_dependency"
    OTHER = "other"


class FindingStatus(str, Enum):
    OPEN = "open"
    ACCEPTED_FIX = "accepted_fix"
    REJECTED = "rejected"
    WAIVED = "waived"
    PENDING_CORRECTION = "pending_correction"
    PERMANENTLY_WAIVED = "permanently_waived"


class ReplacementReason(str, Enum):
    CORRECTED_DATA = "corrected_data"
    REVISED_CONTENT = "revised_content"
    FORMATTING_CHANGE = "formatting_change"
    LANGUAGE_REVISION = "language_revision"
    OTHER = "other"


@dataclass
class Translation:
    """A machine or human translation of a free-text field."""
    text: str
    source_language: str  # "en" or "fr"
    target_language: str
    is_machine_translation: bool = True
    engine: Optional[str] = None
    translated_at: str = field(default_factory=now_iso)
    source_text_hash: Optional[str] = None
    human_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BilingualNote:
    """
    Free-text note captured in its original language, with an auto-generated
    machine translation to the alternate language. Mirrors the
    'structured section + free text note' decision-capture pattern.
    """
    original_text: str
    original_language: str  # "en" or "fr"
    author: str
    created_at: str = field(default_factory=now_iso)
    translation: Optional[Translation] = None
    human_verified_translation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class Finding:
    """A single Table 101 / Chart 101 rule violation instance."""
    finding_id: str
    rule_id: str
    pack: str  # "tables101" | "charts101"
    severity: Severity
    sheet_name: str
    location: str  # e.g. cell ref, chart name, row/col
    title_en: str
    title_fr: str
    description_en: str
    description_fr: str
    status: FindingStatus = FindingStatus.OPEN
    detected_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["status"] = self.status.value
        return d


@dataclass
class Decision:
    """
    Reviewer decision on a Finding: structured reason + free-text note,
    optional target resolution date, per the decision-capture spec.
    """
    decision_id: str
    finding_id: str
    decision_type: DecisionType
    reason: DecisionReason
    note: BilingualNote
    reviewer: str
    decided_at: str = field(default_factory=now_iso)
    target_resolution_date: Optional[str] = None
    follow_up_owner: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["decision_type"] = self.decision_type.value
        d["reason"] = self.reason.value
        return d


@dataclass
class Amendment:
    """
    Generic audit-trail entry. Mirrors core/project_state.py Amendment in the
    broader Accelerator: every analyst/reviewer override or state change is
    recorded here, independent of Decision (which is finding-specific).
    """
    amendment_id: str
    project_id: str
    kind: str  # e.g. "workbook_replaced", "project_closed", "label_changed"
    description_en: str
    description_fr: str
    actor: str
    created_at: str = field(default_factory=now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkbookRevision:
    """One uploaded workbook revision within a project."""
    revision_id: str
    revision_number: int
    original_filename: str
    stored_filename: str
    sha256: str
    uploaded_by: str
    uploaded_at: str = field(default_factory=now_iso)
    language: str = "en"  # "en" | "fr"
    replacement_reason: Optional[ReplacementReason] = None
    replacement_note: Optional[BilingualNote] = None
    parent_revision_id: Optional[str] = None
    findings: List[Finding] = field(default_factory=list)
    compliance_status: ComplianceStatus = ComplianceStatus.PENDING
    validated_at: Optional[str] = None
    commit_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["compliance_status"] = self.compliance_status.value
        if self.replacement_reason:
            d["replacement_reason"] = self.replacement_reason.value
        d["findings"] = [f.to_dict() for f in self.findings]
        return d


@dataclass
class ProjectState:
    """
    The single artifact carried through this tool's pipeline, analogous to
    core/project_state.py ProjectState in the broader Accelerator. Uses an
    automatically generated immutable ID plus a human-readable label.
    """
    project_id: str
    label: str
    reviewer: str
    status: ProjectStatus = ProjectStatus.OPEN
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    revisions: List[WorkbookRevision] = field(default_factory=list)
    decisions: List[Decision] = field(default_factory=list)
    amendments: List[Amendment] = field(default_factory=list)
    closed_at: Optional[str] = None
    closed_by: Optional[str] = None
    closing_note: Optional[BilingualNote] = None
    derived_from_project_id: Optional[str] = None

    def latest_revision(self) -> Optional[WorkbookRevision]:
        return self.revisions[-1] if self.revisions else None

    def add_amendment(self, kind: str, description_en: str, description_fr: str,
                       actor: str, **metadata) -> Amendment:
        amendment = Amendment(
            amendment_id=new_id("AMD-"),
            project_id=self.project_id,
            kind=kind,
            description_en=description_en,
            description_fr=description_fr,
            actor=actor,
            metadata=metadata,
        )
        self.amendments.append(amendment)
        self.updated_at = now_iso()
        return amendment

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["revisions"] = [r.to_dict() for r in self.revisions]
        d["decisions"] = [dec.to_dict() for dec in self.decisions]
        d["amendments"] = [a.to_dict() for a in self.amendments]
        return d

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
