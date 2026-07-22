"""
StatCan Tables/Charts Validator — Streamlit entry point.

Structured as a thin entry point (page config + session init + service
wiring), mirroring app.py in the broader StatCan ESR Accelerator, so this
module can later be mounted as an additional stage/tab inside that
application with minimal change.
"""
import os
import sys
import tempfile
from datetime import date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import get_project_store, get_report_generator
from app.i18n import t
from core.models import (
    ProjectStatus, ComplianceStatus, DecisionType, DecisionReason,
    ReplacementReason, FindingStatus,
)

st.set_page_config(page_title="StatCan Tables/Charts Validator | Validateur", layout="wide")

if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "en"
if "active_project_id" not in st.session_state:
    st.session_state.active_project_id = None

store = get_project_store()
reportgen = get_report_generator()

with st.sidebar:
    st.session_state.ui_lang = st.radio("Language / Langue", ["en", "fr"],
                                         index=0 if st.session_state.ui_lang == "en" else 1,
                                         horizontal=True)
lang = st.session_state.ui_lang

st.title(t(lang, "app_title"))

tab_projects, tab_new = st.tabs([t(lang, "nav_projects"), t(lang, "nav_new_project")])

with tab_new:
    st.subheader(t(lang, "nav_new_project"))
    with st.form("new_project_form"):
        label = st.text_input(t(lang, "label"))
        reviewer = st.text_input(t(lang, "reviewer"))
        submitted = st.form_submit_button(t(lang, "create"))
        if submitted and label and reviewer:
            project = store.create_project(label=label, reviewer=reviewer)
            st.session_state.active_project_id = project.project_id
            st.success(f"{project.project_id} — {project.label}")

with tab_projects:
    status_filter = st.selectbox(t(lang, "filter"), ["open", "closed", "all"], index=0)
    projects = store.list_projects()
    if status_filter != "all":
        projects = [p for p in projects if p.status.value == status_filter]

    for p in projects:
        with st.expander(f"{p.project_id} — {p.label}  [{p.status.value}]"):
            st.write(f"**{t(lang,'reviewer')}:** {p.reviewer}")
            st.write(f"**{t(lang,'status')}**: {p.status.value}" if False else "")
            if st.button(t(lang, "open"), key=f"open-{p.project_id}"):
                st.session_state.active_project_id = p.project_id

    active_id = st.session_state.active_project_id
    if active_id:
        project = store.load_project(active_id)
        st.markdown("---")
        st.header(f"{project.project_id} — {project.label}")

        colA, colB = st.columns(2)
        with colA:
            if project.status == ProjectStatus.OPEN:
                if st.button(t(lang, "close_project")):
                    store.close_project(project, actor=project.reviewer)
                    st.rerun()
            else:
                if st.button(t(lang, "reopen_project")):
                    store.reopen_project(project, actor=project.reviewer)
                    st.rerun()

        is_replacement = len(project.revisions) > 0
        upload_label = t(lang, "replace_workbook") if is_replacement else t(lang, "upload_workbook")
        st.subheader(upload_label)

        workbook_language = st.selectbox(t(lang, "language_of_workbook"), ["en", "fr"], key="wb_lang")

        replacement_reason = None
        replacement_note_text = ""
        if is_replacement:
            reason_key = st.selectbox(
                t(lang, "replacement_reason"),
                [r.value for r in ReplacementReason],
                key="repl_reason",
            )
            replacement_reason = ReplacementReason(reason_key)
            replacement_note_text = st.text_area(t(lang, "replacement_note"), key="repl_note")

        uploaded = st.file_uploader(upload_label, type=["xlsx"], key="uploader")
        if uploaded is not None and st.button(t(lang, "validate")):
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = tmp.name
            revision = store.add_workbook_revision(
                project, tmp_path, original_filename=uploaded.name,
                uploaded_by=project.reviewer, language=workbook_language,
                replacement_reason=replacement_reason,
                replacement_note_text=replacement_note_text or None,
                replacement_note_language=lang,
            )
            os.unlink(tmp_path)
            st.success(f"Revision {revision.revision_number}: {revision.compliance_status.value}")
            st.rerun()

        project = store.load_project(active_id)
        revision = project.latest_revision()
        if revision:
            st.subheader(f"{t(lang,'findings')} — Revision {revision.revision_number}")
            st.write(f"**{revision.compliance_status.value}**")

            for f in revision.findings:
                title = f.title_en if lang == "en" else f.title_fr
                desc = f.description_en if lang == "en" else f.description_fr
                with st.expander(f"[{f.severity.value.upper()}] {f.rule_id} — {title} ({f.status.value})"):
                    st.write(desc)
                    st.caption(f"{f.sheet_name}: {f.location}")

                    if f.status == FindingStatus.OPEN:
                        with st.form(f"decision-{f.finding_id}"):
                            decision_type = st.selectbox(t(lang, "decision_type"),
                                                          [d.value for d in DecisionType],
                                                          key=f"dt-{f.finding_id}")
                            reason = st.selectbox(t(lang, "reason"),
                                                   [r.value for r in DecisionReason],
                                                   key=f"reason-{f.finding_id}")
                            note_language = st.selectbox(t(lang, "note_language"), ["en", "fr"],
                                                          key=f"nl-{f.finding_id}")
                            note_text = st.text_area(t(lang, "note_text"), key=f"note-{f.finding_id}")
                            target_dt = st.date_input(t(lang, "target_date"), value=None,
                                                       key=f"td-{f.finding_id}")
                            follow_up_owner = st.text_input(t(lang, "follow_up_owner"),
                                                             key=f"fu-{f.finding_id}")
                            if st.form_submit_button(t(lang, "submit_decision")):
                                store.record_decision(
                                    project, revision, f.finding_id,
                                    decision_type=DecisionType(decision_type),
                                    reason=DecisionReason(reason),
                                    note_text=note_text, note_language=note_language,
                                    reviewer=project.reviewer,
                                    target_resolution_date=str(target_dt) if target_dt else None,
                                    follow_up_owner=follow_up_owner or None,
                                )
                                st.rerun()

            st.markdown("---")
            reports = reportgen.generate_both(project)
            colE, colF = st.columns(2)
            with colE:
                st.download_button("Download EN report", reports["en"],
                                    file_name=f"{project.project_id}_report_en.md")
            with colF:
                st.download_button("Télécharger rapport FR", reports["fr"],
                                    file_name=f"{project.project_id}_report_fr.md")
