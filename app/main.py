"""
StatCan Tables/Charts Validator — Streamlit entry point

Deterministic-only: identification and changes need no LLM. Findings come
from the rule engine; review resolutions come from the deterministic
remediation catalogue applied to a fresh workbook iteration.

R2 client-release hardening:
- one-active-finding navigation whose selection survives reruns (D1);
- seamless save: apply -> commit -> auto-revision, with a persistent
  confirmation and no manual download/re-upload (D2);
- guarded uploads (no tracebacks), always-on status panel, compliant panel.
"""
import os
import sys
import tempfile

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import ui_state
from app.fix_flow import apply_fix, revalidate_findings, compute_status_panel, guard_upload
from app.services import get_project_store, get_report_generator
from app.i18n import t
from core.models import (
    ProjectStatus, ComplianceStatus, DecisionType, DecisionReason,
    ReplacementReason, FindingStatus,
)
from core.iteration_lineage import current_workbook, latest_iteration
from core.remediation_catalog import remediation_options, approved_symbol_options

st.set_page_config(
    page_title="StatCan Tables/Charts Validator | Validateur",
    layout="wide",
)

# ---- Initialise session state ---------------------------------------
if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "en"
if "active_project_id" not in st.session_state:
    st.session_state.active_project_id = None

store = get_project_store()
reportgen = get_report_generator()

# ---- Sidebar --------------------------------------------------------
with st.sidebar:
    st.session_state.ui_lang = st.radio(
        "Language / Langue", ["en", "fr"],
        index=0 if st.session_state.ui_lang == "en" else 1,
        horizontal=True,
    )
    lang = st.session_state.ui_lang

    st.markdown("---")
    st.caption("StatCan Tables/Charts Validator — deterministic rules")

# ---- Main UI --------------------------------------------------------

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
            ui_state.clear_active_finding(None)
            ui_state.clear_last_apply_result(None)
            st.success(f"{project.project_id} — {project.label}")

with tab_projects:
    status_filter = st.selectbox(t(lang, "filter"), ["open", "closed", "all"], index=0)
    projects = store.list_projects()
    if status_filter != "all":
        projects = [p for p in projects if p.status.value == status_filter]

    for p in projects:
        with st.expander(f"{p.project_id} — {p.label}  [{p.status.value}]"):
            st.write(f"**{t(lang,'reviewer')}:** {p.reviewer}")
            if st.button(t(lang, "open"), key=f"open-{p.project_id}"):
                st.session_state.active_project_id = p.project_id
                ui_state.clear_active_finding(None)
                ui_state.clear_last_apply_result(None)

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

        # ---- Workbook upload / replacement ------------------------------
        is_replacement = len(project.revisions) > 0
        upload_label = t(lang, "replace_workbook") if is_replacement else t(lang, "upload_workbook")
        st.subheader(upload_label)

        workbook_language = st.selectbox(
            t(lang, "language_of_workbook"), ["en", "fr"], key="wb_lang"
        )

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
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                    tmp.write(uploaded.getvalue())
                    tmp_path = tmp.name
                revision, upload_error = guard_upload(
                    store, project, tmp_path,
                    original_filename=uploaded.name,
                    uploaded_by=project.reviewer,
                    language=workbook_language,
                    replacement_reason=replacement_reason,
                    replacement_note_text=replacement_note_text or None,
                    replacement_note_language=lang,
                )
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            if upload_error is not None:
                st.error(t(lang, "upload_error"))
            else:
                assert revision is not None
                ui_state.clear_active_finding(None)
                ui_state.clear_last_apply_result(None)
                st.success(f"Revision {revision.revision_number}: {revision.compliance_status.value}")
                st.rerun()

        project = store.load_project(active_id)
        revision = project.latest_revision()
        if revision:
            workbook_dir = os.path.join(
                store.repo.root_path, f"reviews/{project.project_id}/workbooks"
            )
            active_workbook = current_workbook(
                workbook_dir, revision.original_filename, revision.stored_filename
            )

            # ---- Status panel (always computed from the store) ----------
            entries = revalidate_findings(revision.findings, str(active_workbook))
            open_entries = [e for e in entries if not e["resolved"]]
            resolved_entries = [e for e in entries if e["resolved"]]
            panel = compute_status_panel(project, revision)
            panel["open_display"] = len(open_entries)
            panel["resolved_display"] = len(resolved_entries)

            st.subheader(t(lang, "findings"))
            p_rev, p_comp, p_open, p_res = st.columns(4)
            p_rev.metric(t(lang, "status_panel_revision"), panel["revision_number"])
            p_comp.metric(t(lang, "status_panel_compliance"), panel["compliance"])
            p_open.metric(t(lang, "status_panel_open"), panel["open_display"])
            p_res.metric(t(lang, "status_panel_resolved"), panel["resolved_display"])
            st.caption(
                f"{t(lang, 'status_panel_workbook_base')}: `{active_workbook.name}`. "
                + ("Each accepted change creates a new immutable iteration and preserves earlier changes."
                   if lang == "en" else
                   "Chaque correction acceptée crée une nouvelle itération immuable et préserve les corrections précédentes.")
            )

            # ---- Compliant panel (zero findings) ------------------------
            if not revision.findings:
                st.success(t(lang, "compliant_panel"))

            # ---- Downloads (always visible, side by side) ---------------
            iter = latest_iteration(workbook_dir, revision.original_filename)
            dl_cols = st.columns(2)
            with dl_cols[0]:
                with open(str(active_workbook), "rb") as fh:
                    wb_bytes = fh.read()
                st.download_button(
                    t(lang, "download_original"),
                    wb_bytes, file_name=active_workbook.name,
                    key="dl-original-workbook",
                    use_container_width=True,
                )
            with dl_cols[1]:
                if iter:
                    with open(str(iter), "rb") as fh:
                        iter_bytes = fh.read()
                    st.download_button(
                        t(lang, "download_revised"),
                        iter_bytes, file_name=iter.name,
                        key="dl-revised-workbook",
                        use_container_width=True,
                        type="primary",
                    )
                else:
                    st.info(
                        "No revisions yet. Apply a fix below to create a revised workbook."
                        if lang == "en" else
                        "Aucune révision. Appliquez une correction ci-dessous pour créer un classeur révisé."
                    )

            # ---- Persistent save confirmation (D2) ----------------------
            last_apply = ui_state.get_last_apply_result(None)
            if last_apply:
                with st.container(border=True):
                    st.success(t(lang, "save_confirmation"))
                    st.write(
                        f"**{t(lang, 'save_commited_as')}** `{last_apply['commit_id'][:8]}` "
                        f"· `{last_apply['iteration_name']}`"
                    )
                    st.write(t(lang, "new_revision_created"))
                    if st.button(t(lang, "back_to_list"), key="dismiss-last-apply"):
                        ui_state.clear_last_apply_result(None)
                        st.rerun()

            # ---- Finding navigation (D1) --------------------------------
            if entries:
                st.markdown("---")
                st.write(f"**{t(lang, 'findings')}**")

                active_fid = ui_state.get_active_finding(None)
                known_ids = [e["finding"].finding_id for e in entries]
                if active_fid and active_fid not in known_ids:
                    ui_state.clear_active_finding(None)
                    active_fid = None

                def _row_label(e):
                    f = e["finding"]
                    title = f.title_en if lang == "en" else f.title_fr
                    if e["resolved"]:
                        state = t(lang, "resolved_by_iteration")
                    else:
                        state = f.status.value
                    return f"[{f.severity.value.upper()}] {f.rule_id} — {title} ({state})"

                for e in entries:
                    f = e["finding"]
                    row_sel, row_btn = st.columns([7, 1])
                    row_sel.write(_row_label(e))
                    is_selected = active_fid == f.finding_id
                    if row_btn.button(
                        "▸" if not is_selected else "●",
                        key=f"sel-{f.finding_id}",
                        disabled=False,
                        use_container_width=True,
                    ):
                        if is_selected:
                            ui_state.clear_active_finding(None)
                        else:
                            ui_state.set_active_finding(None, f.finding_id)
                        st.rerun()

                if open_entries:
                    if st.button(t(lang, "next_open_finding"), key="next-open-finding"):
                        ids = [e["finding"].finding_id for e in open_entries]
                        if active_fid in ids:
                            idx = (ids.index(active_fid) + 1) % len(ids)
                        else:
                            idx = 0
                        ui_state.set_active_finding(None, ids[idx])
                        st.rerun()

                # ---- Detail panel (single active finding) ----------------
                active_fid = ui_state.get_active_finding(None)
                if not active_fid:
                    st.info(t(lang, "no_finding_selected"))
                else:
                    entry = next((e for e in entries
                                  if e["finding"].finding_id == active_fid), None)
                    if entry is None:
                        ui_state.clear_active_finding(None)
                        st.rerun()
                    else:
                        f = entry["finding"]
                        title = f.title_en if lang == "en" else f.title_fr
                        desc = f.description_en if lang == "en" else f.description_fr
                        with st.container(border=True):
                            st.subheader(t(lang, "finding_detail"))
                            st.write(f"**[{f.severity.value.upper()}] {f.rule_id} — {title}**")
                            st.write(desc)
                            st.caption(f"{f.sheet_name}: {f.location}")

                            if st.button(t(lang, "back_to_list"), key=f"back-{f.finding_id}"):
                                ui_state.clear_active_finding(None)
                                st.rerun()

                            if entry["resolved"]:
                                st.success(
                                    f"✅ {t(lang, 'resolved_by_iteration')}"
                                )
                            else:
                                if entry["affected_cells"]:
                                    st.markdown(
                                        ("**Affected cells:** " if lang == "en" else "**Cellules touchées :** ")
                                        + ", ".join(f"`{f.sheet_name}!{cell}`" for cell in entry["affected_cells"])
                                    )

                                # ---- Deterministic remediation choices ----
                                options = remediation_options(f.rule_id)
                                if options and f.status == FindingStatus.OPEN:
                                    st.markdown("---")
                                    st.markdown("##### 🛠 Deterministic resolution options" if lang == "en" else "##### 🛠 Options de résolution déterministes")
                                    selected_cell = None
                                    if entry["affected_cells"]:
                                        selected_cell = st.selectbox(
                                            "Cell to change" if lang == "en" else "Cellule à modifier",
                                            entry["affected_cells"],
                                            key=f"rem-cell-{f.finding_id}",
                                        )
                                    option_labels = [o["label_en"] if lang == "en" else o["label_fr"] for o in options]
                                    selected_idx = st.selectbox(
                                        "Resolution" if lang == "en" else "Résolution",
                                        range(len(options)),
                                        format_func=lambda i: option_labels[i],
                                        key=f"rem-option-{f.finding_id}",
                                    )
                                    selected = options[selected_idx]
                                    input_value = None
                                    if selected["input"] == "text":
                                        input_value = st.text_input(
                                            "Enter value or instruction" if lang == "en" else "Saisir la valeur ou l'instruction",
                                            key=f"rem-value-{f.finding_id}",
                                        )
                                    elif selected["input"] == "select":
                                        input_value = st.selectbox(
                                            "Approved symbol" if lang == "en" else "Symbole approuvé",
                                            approved_symbol_options(), key=f"rem-symbol-{f.finding_id}",
                                        )
                                    if st.button(
                                        "✅ Apply change & create iteration" if lang == "en" else "✅ Appliquer et créer une itération",
                                        key=f"rem-save-{f.finding_id}",
                                        type="primary",
                                        use_container_width=True,
                                    ):
                                        outcome = apply_fix(
                                            store, project, revision, f,
                                            option_id=selected["id"],
                                            value=input_value,
                                            target_cell=selected_cell,
                                            workbook_dir=workbook_dir,
                                            lang=lang,
                                            option_label_en=selected.get("label_en", ""),
                                            option_label_fr=selected.get("label_fr", ""),
                                        )
                                        if outcome["success"]:
                                            ui_state.set_last_apply_result(None, outcome)
                                            ui_state.clear_active_finding(None)
                                            st.rerun()
                                        else:
                                            # No rerun: inputs and selection are preserved
                                            st.warning(outcome["message"])

                                # ---- Decision form ------------------------
                                if f.status == FindingStatus.OPEN:
                                    with st.form(f"decision-{f.finding_id}"):
                                        decision_type = st.selectbox(
                                            t(lang, "decision_type"),
                                            [d.value for d in DecisionType],
                                            key=f"dt-{f.finding_id}",
                                        )
                                        reason = st.selectbox(
                                            t(lang, "reason"),
                                            [r.value for r in DecisionReason],
                                            key=f"reason-{f.finding_id}",
                                        )
                                        note_language = st.selectbox(
                                            t(lang, "note_language"), ["en", "fr"],
                                            key=f"nl-{f.finding_id}",
                                        )
                                        note_text = st.text_area(t(lang, "note_text"), key=f"note-{f.finding_id}")
                                        target_dt = st.date_input(
                                            t(lang, "target_date"), value=None,
                                            key=f"td-{f.finding_id}",
                                        )
                                        follow_up_owner = st.text_input(
                                            t(lang, "follow_up_owner"),
                                            key=f"fu-{f.finding_id}",
                                        )
                                        if st.form_submit_button(
                                            t(lang, "submit_decision"),
                                            use_container_width=True,
                                        ):
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

            # ---- Report download ----------------------------------------
            st.markdown("---")
            st.subheader("📄 Audit Reports" if lang == "en" else "📄 Rapports d'audit")
            reports = reportgen.generate_both(project)
            colE, colF = st.columns(2)
            with colE:
                st.download_button(
                    "⬇ Download EN report", reports["en"],
                    file_name=f"{project.project_id}_report_en.md",
                    use_container_width=True,
                )
            with colF:
                st.download_button(
                    "⬇ Télécharger rapport FR", reports["fr"],
                    file_name=f"{project.project_id}_report_fr.md",
                    use_container_width=True,
                )
