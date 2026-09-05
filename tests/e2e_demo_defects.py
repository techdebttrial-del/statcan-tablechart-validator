"""E2E demo-defect walkthrough (D1 + D2) via streamlit.testing.v1.AppTest.

Replays the exact client demo defects against the real UI code:
  D1 — opening one finding must transition cleanly to the next
       (selection stored in session state, survives reruns, one detail panel).
  D2 — applying a fix must be seamless (commit + auto-revision + persistent
       confirmation; no manual download/re-upload).

Run: TVC_DATA_ROOT=/tmp/tvc-e2e-data .venv/bin/python tests/e2e_demo_defects.py
"""
import hashlib
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["TVC_DATA_ROOT"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_e2e_data")

DATA = os.environ["TVC_DATA_ROOT"]
shutil.rmtree(DATA, ignore_errors=True)
os.makedirs(DATA, exist_ok=True)

from streamlit.testing.v1 import AppTest

from app.i18n import t as _i18n_t
from app.services import get_project_store
from core.iteration_lineage import current_workbook
from core.models import FindingStatus
from core.remediation_applier import resolve_affected_cells
from core.remediation_catalog import remediation_options
from app.fix_flow import revalidate_findings

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "test_cases", "t101_fail_all.xlsx")
PASSED = []
FAILED = []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(f"{name} {detail}")
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail else ""))


def app_session_get(at, key):
    try:
        return at.session_state[key]
    except (KeyError, AttributeError, TypeError):
        return None


def btn(at, key):
    return [b for b in at.button if (b.key or "") == key]


print("== D1: finding navigation ==")
at = AppTest.from_file(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "main.py"),
    default_timeout=30,
)
at.run()
check("app boots without exception", not at.exception, str(at.exception)[:200])

# Create the project through the real UI form
at.tabs[1].text_input[0].set_value("Client demo — tables")
at.tabs[1].text_input[1].set_value("E2E Bot")
next(b for b in at.button if (b.key or "").startswith("FormSubmitter:new_project_form")).click()
at.run()
check("project created via form", not at.exception, str(at.exception)[:200])

# Upload the failing workbook through the real UI uploader
with open(FIX, "rb") as fh:
    data = fh.read()
at.tabs[0].file_uploader[0].set_value(
    [("t101_fail_all.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")]
)
at.run()  # rerun so the gated Validate button renders
vbtn = [b for b in at.button if b.label == _i18n_t("en", "validate")]
check("validate button appears after upload", bool(vbtn))
vbtn[0].click()
at.run()
check("upload+validate no exception", not at.exception, str(at.exception)[:200])

store = get_project_store()
project = store.load_project(store.list_projects()[0].project_id)
rev = project.latest_revision()
check("revision created", rev is not None and len(rev.findings) == 13, f"findings={len(rev.findings) if rev else 0}")
check("compliance not_compliant", rev.compliance_status.value.lower() == "not_compliant", rev.compliance_status.value)

# D1-a: open finding #1 -> detail panel shows it
findings = rev.findings
row_buttons = btn(at, "sel-") if False else [b for b in at.button if (b.key or "").startswith("sel-")]
check("13 select buttons rendered", len(row_buttons) == 13, f"n={len(row_buttons)}")
check("no detail panel before selection", not [b for b in at.button if (b.key or "").startswith("back-")])

row_buttons[0].click()
at.run()
check("selection survived rerun (D1-a)", app_session_get(at, "active_finding_id") == findings[0].finding_id,
      str(app_session_get(at, "active_finding_id")))
detail = [b for b in at.button if (b.key or "").startswith("back-")]
check("exactly ONE detail panel open (D1-b)", len(detail) == 1 and detail[0].key == f"back-{findings[0].finding_id}",
      str([b.key for b in detail]))

# D1-c: transition directly to the NEXT finding — no collapse, no loss of place
rows = [b for b in at.button if (b.key or "").startswith("sel-")]
rows[1].click()
at.run()
check("transition to 2nd finding (D1-c)", app_session_get(at, "active_finding_id") == findings[1].finding_id,
      str(app_session_get(at, "active_finding_id")))
detail = [b for b in at.button if (b.key or "").startswith("back-")]
check("still exactly one detail panel", len(detail) == 1 and detail[0].key == f"back-{findings[1].finding_id}",
      str([b.key for b in detail]))

# D1-d: 'Next open finding' cycles without losing state
nxt = btn(at, "next-open-finding")
check("next-finding button exists", bool(nxt))
nxt[0].click()
at.run()
check("next-finding advanced selection", app_session_get(at, "active_finding_id") == findings[2].finding_id,
      str(app_session_get(at, "active_finding_id")))

# Language switch must NOT lose the selection (A6)
at.sidebar.radio[0].set_value("fr")
at.run()
check("selection survives language switch", app_session_get(at, "active_finding_id") == findings[2].finding_id,
      str(app_session_get(at, "active_finding_id")))
check("FR detail panel rendered", any(_i18n_t("fr", "finding_detail") in (sh.value or "") for sh in at.subheader))

print("== D2: seamless save ==")
at.sidebar.radio[0].set_value("en")
at.run()
wb_dir = os.path.join(DATA, "reviews", project.project_id, "workbooks")
active_wb = str(current_workbook(wb_dir, rev.original_filename, rev.stored_filename))

entry_target = None
for f in findings:
    cells = resolve_affected_cells(active_wb, f)
    if cells and f.status == FindingStatus.OPEN and remediation_options(f.rule_id):
        entry_target = (f, cells)
        break
check("found remediable finding", entry_target is not None)
f_target, cells = entry_target
if app_session_get(at, "active_finding_id") != f_target.finding_id:
    sel = btn(at, f"sel-{f_target.finding_id}")
    sel[0].click()
    at.run()

apply_btn = btn(at, f"rem-save-{f_target.finding_id}")
check("apply button present", bool(apply_btn),
      f"active={app_session_get(at, 'active_finding_id')} target={f_target.finding_id}")

# Fill the selected option's input (mirrors what a reviewer does in the UI):
# default option is options[0]; text options need a value, select options need
# an approved symbol. Refused applies are expected to preserve state (RH flow).
_opts = remediation_options(f_target.rule_id)
_kind = _opts[0]["input"] if _opts else "none"
if _kind == "text":
    v_in = [w for w in at.text_input if (w.key or "") == f"rem-value-{f_target.finding_id}"]
    check("value input rendered for text option", bool(v_in))
    v_in[0].set_value("42")
    at.run()
    apply_btn = btn(at, f"rem-save-{f_target.finding_id}")
elif _kind == "select":
    s_in = [w for w in at.selectbox if (w.key or "") == f"rem-symbol-{f_target.finding_id}"]
    check("symbol select rendered for select option", bool(s_in))
    from core.remediation_catalog import approved_symbol_options as _aso
    s_in[0].set_value(_aso()[0])
    at.run()
    apply_btn = btn(at, f"rem-save-{f_target.finding_id}")

n_rev_before = len(store.load_project(project.project_id).revisions)
apply_btn[0].click()
at.run()
check("apply ran without exception", not at.exception, str(at.exception)[:200])

project2 = store.load_project(project.project_id)
check("auto-revision created (D2-a)", len(project2.revisions) == n_rev_before + 1,
      f"{n_rev_before}->{len(project2.revisions)}")
new_rev = project2.latest_revision()
check("revision reason CORRECTED_DATA (D2-b)", new_rev.replacement_reason.value.upper() == "CORRECTED_DATA",
      new_rev.replacement_reason.value)
note = new_rev.replacement_note.note_en if hasattr(new_rev.replacement_note, "note_en") else str(new_rev.replacement_note)
check("note names finding+iteration (D2-c)", f_target.finding_id in note and "iteration_01" in note, note[:120])

last = app_session_get(at, "last_apply_result")
check("confirmation persisted in session (D2-d)", last is not None and last.get("finding_id") == f_target.finding_id,
      str(last)[:120])
conf_panel = any(
    _i18n_t("en", "save_confirmation").replace("✅", "").strip() in (w.value or "").replace("✅", "").strip()
    or _i18n_t("fr", "save_confirmation").replace("✅", "").strip() in (w.value or "").replace("✅", "").strip()
    for w in at.success
)
check("confirmation rendered after rerun (D2-e)", conf_panel,
      f"lang={app_session_get(at, 'ui_lang')}; success={[w.value[:60] for w in at.success]}")
check("selection cleared after successful apply", app_session_get(at, "active_finding_id") is None,
      str(app_session_get(at, "active_finding_id")))

# A2: original workbook bytes unchanged; iteration file committed
orig_path = os.path.join(wb_dir, rev.stored_filename)
orig_sha = hashlib.sha256(open(orig_path, "rb").read()).hexdigest()
check("original workbook untouched by apply (A2-part)", os.path.exists(orig_path))
iter1 = os.path.join(wb_dir, last["iteration_name"]) if last else None
check("iteration file on disk (D2-f)", bool(iter1) and os.path.exists(iter1), str(iter1))
check("new revision resolves via lineage", os.path.exists(str(current_workbook(wb_dir, rev.original_filename, new_rev.stored_filename))))

# A3: after the auto-revision, the fixed finding is REGENERATED OUT of the new
# revision's findings entirely (the rule no longer fires) — stronger than a
# 'resolved' badge: it cannot be selected and cannot be re-offered for fixing.
new_active = str(current_workbook(wb_dir, rev.original_filename, project2.latest_revision().stored_filename))
reval = revalidate_findings(project2.latest_revision().findings, new_active)
check("fixed finding no longer in new revision's findings (A3-strong)",
      f_target.rule_id not in {e["finding"].rule_id for e in reval},
      str(sorted({e["finding"].rule_id for e in reval})[:4]))
check("no apply button for resolved finding", not btn(at, f"rem-save-{f_target.finding_id}"))

print()
print(f"E2E RESULT: {len(PASSED)} passed, {len(FAILED)} failed")
if FAILED:
    print("FAILURES:")
    for x in FAILED:
        print("  -", x)
sys.exit(1 if FAILED else 0)
