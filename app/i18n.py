"""
Minimal EN/FR UI string dictionary. Mirrors the broader Accelerator's
bilingual-title convention in app.py (page config sets a bilingual title).
The interface language is a user preference independent of workbook
language, per project decision.
"""

STRINGS = {
    "en": {
        "app_title": "StatCan Tables/Charts Validator",
        "nav_projects": "Saved Projects",
        "nav_new_project": "New Project",
        "label": "Project label",
        "reviewer": "Reviewer name",
        "create": "Create project",
        "open": "Open",
        "close_project": "Close project",
        "reopen_project": "Reopen project",
        "upload_workbook": "Upload workbook (.xlsx)",
        "replace_workbook": "Replace workbook (new revision)",
        "new_project_from_workbook": "Start a new separate project instead",
        "replacement_reason": "Reason for replacement",
        "replacement_note": "Note (required)",
        "validate": "Validate",
        "language_of_workbook": "Workbook language",
        "findings": "Findings",
        "decide": "Record decision",
        "decision_type": "Decision",
        "reason": "Structured reason",
        "note_language": "Note language",
        "note_text": "Free-text note",
        "target_date": "Target resolution date (optional)",
        "follow_up_owner": "Follow-up owner (optional)",
        "submit_decision": "Submit decision",
        "status_open": "Open",
        "status_closed": "Closed",
        "filter": "Filter",
        "download_reports": "Download bilingual report",
    },
    "fr": {
        "app_title": "Validateur de tableaux et graphiques de StatCan",
        "nav_projects": "Projets sauvegardés",
        "nav_new_project": "Nouveau projet",
        "label": "Étiquette du projet",
        "reviewer": "Nom du réviseur",
        "create": "Créer le projet",
        "open": "Ouvrir",
        "close_project": "Fermer le projet",
        "reopen_project": "Rouvrir le projet",
        "upload_workbook": "Téléverser un classeur (.xlsx)",
        "replace_workbook": "Remplacer le classeur (nouvelle révision)",
        "new_project_from_workbook": "Démarrer un projet distinct à la place",
        "replacement_reason": "Motif du remplacement",
        "replacement_note": "Note (obligatoire)",
        "validate": "Valider",
        "language_of_workbook": "Langue du classeur",
        "findings": "Constats",
        "decide": "Enregistrer une décision",
        "decision_type": "Décision",
        "reason": "Motif structuré",
        "note_language": "Langue de la note",
        "note_text": "Note en texte libre",
        "target_date": "Date cible de résolution (facultatif)",
        "follow_up_owner": "Responsable du suivi (facultatif)",
        "submit_decision": "Soumettre la décision",
        "status_open": "Ouvert",
        "status_closed": "Fermé",
        "filter": "Filtrer",
        "download_reports": "Télécharger le rapport bilingue",
    },
}


def t(lang: str, key: str) -> str:
    return STRINGS.get(lang, STRINGS["en"]).get(key, key)
