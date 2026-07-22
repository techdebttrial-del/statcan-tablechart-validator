"""
ProjectStore

Persistence + orchestration layer for saved review projects. Wraps a
RepositoryClient (see repository_client.py) the same way the broader
Accelerator's appservices.py wires a ConfigLoader / ForgejoClient singleton
around core.project_state.ProjectState. Responsible for:
  - creating projects with an auto-generated ID + human label
  - appending workbook revisions (fresh-revalidation-only policy)
  - recording decisions (structured reason + free-text bilingual note)
  - closing / reopening projects
  - serializing ProjectState to/from JSON via the repository client

This is the extension point for later integration into the broader
Accelerator: swap RepositoryClient for ForgejoClient and this class needs
no other changes.
"""
from __future__ import annotations

import json
import os
import shutil
from typing import List, Optional

from core.models import (
    ProjectState, WorkbookRevision, Decision, BilingualNote,
    ProjectStatus, ComplianceStatus, DecisionType, DecisionReason,
    ReplacementReason, Severity, FindingStatus, new_id, sha256_of_file, now_iso,
)
from core.repository_client import RepositoryClient
from core.excel_inspector import ExcelInspector
from core.translation_manager import TranslationManager

BLOCKING_SEVERITIES = {Severity.CRITICAL, Severity.ERROR}


class ProjectStore:
    def __init__(self, repo: RepositoryClient, inspector: Optional[ExcelInspector] = None,
                 translator: Optional[TranslationManager] = None):
        self.repo = repo
        self.inspector = inspector or ExcelInspector()
        self.translator = translator or TranslationManager()

    # ---- Project lifecycle -----------------------------------------

    def create_project(self, label: str, reviewer: str) -> ProjectState:
        project_id = new_id("TVC-")
        project = ProjectState(project_id=project_id, label=label, reviewer=reviewer)
        self._save(project)
        return project

    def list_projects(self) -> List[ProjectState]:
        projects = []
        for path in self.repo.list_files(prefix="reviews"):
            if path.endswith("project.json"):
                data = json.loads(self.repo.get_file(path))
                projects.append(self._from_dict(data))
        return sorted(projects, key=lambda p: p.updated_at, reverse=True)

    def load_project(self, project_id: str) -> ProjectState:
        path = f"reviews/{project_id}/project.json"
        data = json.loads(self.repo.get_file(path))
        return self._from_dict(data)

    def rename_project(self, project: ProjectState, new_label: str, actor: str) -> ProjectState:
        old_label = project.label
        project.label = new_label
        project.add_amendment(
            kind="label_changed",
            description_en=f"Project label changed from '{old_label}' to '{new_label}'.",
            description_fr=f"L'étiquette du projet est passée de « {old_label} » à « {new_label} ».",
            actor=actor,
            old_label=old_label,
            new_label=new_label,
        )
        self._save(project)
        return project

    def close_project(self, project: ProjectState, actor: str, note_text: Optional[str] = None,
                       note_language: str = "en") -> ProjectState:
        project.status = ProjectStatus.CLOSED
        project.closed_at = now_iso()
        project.closed_by = actor
        if note_text:
            project.closing_note = self.translator.make_bilingual_note(note_text, note_language, actor)
        project.add_amendment(
            kind="project_closed",
            description_en="Project closed by reviewer.",
            description_fr="Projet fermé par le réviseur.",
            actor=actor,
        )
        self._save(project)
        return project

    def reopen_project(self, project: ProjectState, actor: str) -> ProjectState:
        project.status = ProjectStatus.OPEN
        project.add_amendment(
            kind="project_reopened",
            description_en="Project reopened by reviewer.",
            description_fr="Projet rouvert par le réviseur.",
            actor=actor,
        )
        self._save(project)
        return project

    # ---- Workbook revisions -----------------------------------------

    def add_workbook_revision(self, project: ProjectState, local_file_path: str,
                               original_filename: str, uploaded_by: str, language: str = "en",
                               replacement_reason: Optional[ReplacementReason] = None,
                               replacement_note_text: Optional[str] = None,
                               replacement_note_language: str = "en") -> WorkbookRevision:
        sha = sha256_of_file(local_file_path)
        revision_number = len(project.revisions) + 1
        revision_id = new_id("REV-")
        stored_filename = f"revision_{revision_number:02d}_{original_filename}"

        parent = project.latest_revision()
        replacement_note = None
        if replacement_note_text:
            replacement_note = self.translator.make_bilingual_note(
                replacement_note_text, replacement_note_language, uploaded_by
            )

        with open(local_file_path, "rb") as fh:
            content = fh.read()

        stored_path = f"reviews/{project.project_id}/workbooks/{stored_filename}"
        commit = self.repo.put_file(
            stored_path, content,
            commit_message=f"Add workbook revision {revision_number} for {project.project_id}",
        )

        revision = WorkbookRevision(
            revision_id=revision_id,
            revision_number=revision_number,
            original_filename=original_filename,
            stored_filename=stored_filename,
            sha256=sha,
            uploaded_by=uploaded_by,
            language=language,
            replacement_reason=replacement_reason,
            replacement_note=replacement_note,
            parent_revision_id=parent.revision_id if parent else None,
            commit_id=commit.commit_id,
        )

        findings = self.inspector.inspect_workbook(local_file_path, language=language)
        revision.findings = findings
        revision.validated_at = now_iso()
        revision.compliance_status = self._compute_compliance(findings)

        project.revisions.append(revision)

        kind = "workbook_uploaded" if parent is None else "workbook_replaced"
        project.add_amendment(
            kind=kind,
            description_en=(
                f"Workbook revision {revision_number} added ('{original_filename}'), "
                f"revalidated from scratch."
            ),
            description_fr=(
                f"Révision de classeur {revision_number} ajoutée (« {original_filename} »), "
                f"revalidée intégralement."
            ),
            actor=uploaded_by,
            revision_id=revision_id,
            sha256=sha,
            replacement_reason=replacement_reason.value if replacement_reason else None,
        )

        self._save(project)
        return revision

    def _compute_compliance(self, findings) -> ComplianceStatus:
        has_blocking_open = any(
            f.severity in BLOCKING_SEVERITIES and f.status == FindingStatus.OPEN
            for f in findings
        )
        return ComplianceStatus.NOT_COMPLIANT if has_blocking_open else ComplianceStatus.COMPLIANT

    def _recompute_revision_compliance(self, revision: WorkbookRevision) -> None:
        has_blocking_unresolved = any(
            f.severity in BLOCKING_SEVERITIES and f.status not in (
                FindingStatus.ACCEPTED_FIX, FindingStatus.PERMANENTLY_WAIVED
            )
            for f in revision.findings
        )
        revision.compliance_status = (
            ComplianceStatus.NOT_COMPLIANT if has_blocking_unresolved else ComplianceStatus.COMPLIANT
        )

    # ---- Decisions ----------------------------------------------------

    def record_decision(self, project: ProjectState, revision: WorkbookRevision, finding_id: str,
                         decision_type: DecisionType, reason: DecisionReason, note_text: str,
                         note_language: str, reviewer: str,
                         target_resolution_date: Optional[str] = None,
                         follow_up_owner: Optional[str] = None) -> Decision:
        note = self.translator.make_bilingual_note(note_text, note_language, reviewer)
        decision = Decision(
            decision_id=new_id("DEC-"),
            finding_id=finding_id,
            decision_type=decision_type,
            reason=reason,
            note=note,
            reviewer=reviewer,
            target_resolution_date=target_resolution_date,
            follow_up_owner=follow_up_owner,
        )
        project.decisions.append(decision)

        for f in revision.findings:
            if f.finding_id == finding_id:
                if decision_type == DecisionType.ACCEPTED_FIX:
                    f.status = FindingStatus.ACCEPTED_FIX
                elif decision_type == DecisionType.REJECTED:
                    f.status = FindingStatus.REJECTED
                elif decision_type == DecisionType.WAIVED:
                    f.status = (
                        FindingStatus.PENDING_CORRECTION if target_resolution_date
                        else FindingStatus.PERMANENTLY_WAIVED
                    )
                break

        self._recompute_revision_compliance(revision)

        project.add_amendment(
            kind="decision_recorded",
            description_en=f"Decision '{decision_type.value}' recorded for finding {finding_id}.",
            description_fr=f"Décision « {decision_type.value} » enregistrée pour le constat {finding_id}.",
            actor=reviewer,
            finding_id=finding_id,
            decision_id=decision.decision_id,
        )

        self._save(project)
        return decision

    # ---- Persistence --------------------------------------------------

    def _save(self, project: ProjectState) -> None:
        path = f"reviews/{project.project_id}/project.json"
        self.repo.put_file(
            path,
            project.to_json().encode("utf-8"),
            commit_message=f"Update project {project.project_id} ({project.label})",
        )

    def _from_dict(self, data: dict) -> ProjectState:
        # Minimal reconstruction path; full round-trip covered in tests.
        from core.models import (
            WorkbookRevision, Decision, Amendment, BilingualNote, Translation,
            Finding,
        )
        revisions = []
        for r in data.get("revisions", []):
            findings = [
                Finding(
                    finding_id=f["finding_id"], rule_id=f["rule_id"], pack=f["pack"],
                    severity=Severity(f["severity"]), sheet_name=f["sheet_name"],
                    location=f["location"], title_en=f["title_en"], title_fr=f["title_fr"],
                    description_en=f["description_en"], description_fr=f["description_fr"],
                    status=FindingStatus(f["status"]), detected_at=f["detected_at"],
                ) for f in r.get("findings", [])
            ]
            rn = None
            if r.get("replacement_note"):
                rn_data = r["replacement_note"]
                rn = BilingualNote(
                    original_text=rn_data["original_text"], original_language=rn_data["original_language"],
                    author=rn_data["author"], created_at=rn_data["created_at"],
                    translation=Translation(**rn_data["translation"]) if rn_data.get("translation") else None,
                    human_verified_translation=rn_data.get("human_verified_translation"),
                )
            revisions.append(WorkbookRevision(
                revision_id=r["revision_id"], revision_number=r["revision_number"],
                original_filename=r["original_filename"], stored_filename=r["stored_filename"],
                sha256=r["sha256"], uploaded_by=r["uploaded_by"], uploaded_at=r["uploaded_at"],
                language=r["language"],
                replacement_reason=ReplacementReason(r["replacement_reason"]) if r.get("replacement_reason") else None,
                replacement_note=rn,
                parent_revision_id=r.get("parent_revision_id"),
                findings=findings,
                compliance_status=ComplianceStatus(r["compliance_status"]),
                validated_at=r.get("validated_at"), commit_id=r.get("commit_id"),
            ))

        decisions = []
        for d in data.get("decisions", []):
            note_data = d["note"]
            note = BilingualNote(
                original_text=note_data["original_text"], original_language=note_data["original_language"],
                author=note_data["author"], created_at=note_data["created_at"],
                translation=Translation(**note_data["translation"]) if note_data.get("translation") else None,
                human_verified_translation=note_data.get("human_verified_translation"),
            )
            decisions.append(Decision(
                decision_id=d["decision_id"], finding_id=d["finding_id"],
                decision_type=DecisionType(d["decision_type"]), reason=DecisionReason(d["reason"]),
                note=note, reviewer=d["reviewer"], decided_at=d["decided_at"],
                target_resolution_date=d.get("target_resolution_date"),
                follow_up_owner=d.get("follow_up_owner"),
            ))

        amendments = [
            Amendment(
                amendment_id=a["amendment_id"], project_id=a["project_id"], kind=a["kind"],
                description_en=a["description_en"], description_fr=a["description_fr"],
                actor=a["actor"], created_at=a["created_at"], metadata=a.get("metadata", {}),
            ) for a in data.get("amendments", [])
        ]

        closing_note = None
        if data.get("closing_note"):
            cn = data["closing_note"]
            closing_note = BilingualNote(
                original_text=cn["original_text"], original_language=cn["original_language"],
                author=cn["author"], created_at=cn["created_at"],
                translation=Translation(**cn["translation"]) if cn.get("translation") else None,
                human_verified_translation=cn.get("human_verified_translation"),
            )

        return ProjectState(
            project_id=data["project_id"], label=data["label"], reviewer=data["reviewer"],
            status=ProjectStatus(data["status"]), created_at=data["created_at"], updated_at=data["updated_at"],
            revisions=revisions, decisions=decisions, amendments=amendments,
            closed_at=data.get("closed_at"), closed_by=data.get("closed_by"),
            closing_note=closing_note, derived_from_project_id=data.get("derived_from_project_id"),
        )
