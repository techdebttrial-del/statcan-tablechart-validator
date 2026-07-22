"""
ReportGenerator

Produces the two human-readable bilingual audit reports (English + French)
per project decision: reports are always generated in both languages,
independent of the reviewer's interface language. Mirrors the broader
Accelerator's publication_formatter.py bilingual EN/FR HTML formatting
convention, but targets the audit/review-report artifact instead of a
publication draft.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from core.models import ProjectState, WorkbookRevision, Finding, Decision, ComplianceStatus, Severity
from core.translation_manager import TranslationManager

STRINGS = {
    "en": {
        "title": "Table 101 / Chart 101 Compliance Review",
        "project": "Project",
        "reviewer": "Reviewer",
        "status": "Status",
        "revision": "Revision",
        "workbook": "Workbook",
        "sha256": "SHA-256",
        "compliant": "Compliant",
        "not_compliant": "Not compliant",
        "pending": "Pending",
        "findings": "Findings",
        "no_findings": "No findings were identified for this revision.",
        "severity": "Severity",
        "location": "Location",
        "rule": "Rule",
        "decisions": "Reviewer Decisions",
        "no_decisions": "No decisions recorded yet.",
        "target_date": "Target resolution date",
        "amendments": "Audit Trail (Amendments)",
        "generated_note": "This report was generated automatically and is available in both English and French.",
    },
    "fr": {
        "title": "Examen de conformité Tableaux 101 / Graphiques 101",
        "project": "Projet",
        "reviewer": "Réviseur",
        "status": "Statut",
        "revision": "Révision",
        "workbook": "Classeur",
        "sha256": "SHA-256",
        "compliant": "Conforme",
        "not_compliant": "Non conforme",
        "pending": "En attente",
        "findings": "Constats",
        "no_findings": "Aucun constat n'a été relevé pour cette révision.",
        "severity": "Gravité",
        "location": "Emplacement",
        "rule": "Règle",
        "decisions": "Décisions du réviseur",
        "no_decisions": "Aucune décision enregistrée pour le moment.",
        "target_date": "Date cible de résolution",
        "amendments": "Piste de vérification (modifications)",
        "generated_note": "Ce rapport a été généré automatiquement et est disponible en anglais et en français.",
    },
}

STATUS_LABEL = {
    ComplianceStatus.COMPLIANT: ("compliant", "compliant"),
    ComplianceStatus.NOT_COMPLIANT: ("not_compliant", "not_compliant"),
    ComplianceStatus.PENDING: ("pending", "pending"),
}


class ReportGenerator:
    def __init__(self, translator: TranslationManager = None):
        self.translator = translator or TranslationManager()

    def generate(self, project: ProjectState, language: str) -> str:
        s = STRINGS[language]
        lines = []
        lines.append(f"# {s['title']}")
        lines.append("")
        lines.append(f"**{s['project']}:** {project.label} (`{project.project_id}`)  ")
        lines.append(f"**{s['reviewer']}:** {project.reviewer}  ")
        lines.append(f"**{s['status']}:** {project.status.value}  ")
        lines.append("")
        lines.append(f"*{s['generated_note']}*")
        lines.append("")

        for revision in project.revisions:
            lines.extend(self._render_revision(revision, project, language, s))

        lines.append(f"## {s['amendments']}")
        lines.append("")
        if project.amendments:
            for a in project.amendments:
                desc = a.description_en if language == "en" else a.description_fr
                lines.append(f"- `{a.created_at}` — **{a.actor}** — {desc}")
        else:
            lines.append("_None._")
        lines.append("")

        return "\n".join(lines)

    def _render_revision(self, revision: WorkbookRevision, project: ProjectState,
                          language: str, s: dict) -> List[str]:
        lines = []
        lines.append(f"## {s['revision']} {revision.revision_number} — {revision.original_filename}")
        lines.append("")
        lines.append(f"- **{s['workbook']}:** {revision.original_filename}")
        lines.append(f"- **{s['sha256']}:** `{revision.sha256}`")
        status_key = STATUS_LABEL[revision.compliance_status][0]
        lines.append(f"- **{s['status']}:** {s[status_key]}")
        lines.append("")

        if revision.replacement_note:
            pair = self.translator.render_pair(revision.replacement_note, language)
            label = pair["label_en"] if language == "en" else pair["label_fr"]
            lines.append(f"> **{label}:** {pair['text']}")
            lines.append("")

        lines.append(f"### {s['findings']}")
        lines.append("")
        if not revision.findings:
            lines.append(s["no_findings"])
        else:
            lines.append(f"| {s['rule']} | {s['severity']} | {s['location']} | {s['status']} |")
            lines.append("|---|---|---|---|")
            for f in revision.findings:
                title = f.title_en if language == "en" else f.title_fr
                lines.append(f"| `{f.rule_id}` {title} | {f.severity.value} | {f.sheet_name}: {f.location} | {f.status.value} |")
        lines.append("")

        lines.append(f"### {s['decisions']}")
        lines.append("")
        revision_finding_ids = {f.finding_id for f in revision.findings}
        decisions = [d for d in project.decisions if d.finding_id in revision_finding_ids]
        if not decisions:
            lines.append(s["no_decisions"])
        else:
            for d in decisions:
                pair = self.translator.render_pair(d.note, language)
                label = pair["label_en"] if language == "en" else pair["label_fr"]
                target = f" ({s['target_date']}: {d.target_resolution_date})" if d.target_resolution_date else ""
                lines.append(
                    f"- **{d.decision_type.value}** ({d.reason.value}) by **{d.reviewer}**{target}  \n"
                    f"  {label}: {pair['text']}"
                )
        lines.append("")
        return lines

    def generate_both(self, project: ProjectState) -> dict:
        return {
            "en": self.generate(project, "en"),
            "fr": self.generate(project, "fr"),
        }
