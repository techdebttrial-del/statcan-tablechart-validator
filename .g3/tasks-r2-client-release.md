# Tasks R2: Client-Release Hardening

Execution mode: G3 — coach holds spec, player implements TDD, coach re-runs
tests and judges. Commit per task. Canonical tree:
`/home/agent/forge/workspace/statcan-tablechart-validator`.

## Task 1: `app/ui_state.py` — session-state logic module
**Objective:** Extract all UI session-state decisions into pure, unit-testable
functions (RH8/FR-8).
**Files:**
- Create: `app/ui_state.py`
- Create: `tests/test_ui_state.py`
**Steps:**
1. Write failing tests: selection get/set/clear; last-apply-result get/set/clear;
   `auto_revision_note` returns bilingual note naming finding id, option id,
   iteration name; all work on a plain dict session.
2. Verify tests fail (module absent).
3. Implement minimum. All functions take/accept a session-like mapping
   (default `st.session_state` if available, injectable for tests).
4. Verify tests pass. Commit `feat(ui): session-state module with tests`.
**Done when:** `pytest tests/test_ui_state.py` green; no Streamlit import needed
for the module's logic (import streamlit lazily or not at all).

## Task 2: i18n keys
**Objective:** Add all new user-facing strings with EN/FR parity (RH7/NFR-4).
**Files:**
- Modify: `app/i18n.py`
- Create: `tests/test_ui_i18n_compliance.py`
**Steps:**
1. Failing tests first: every key used by main.py's new sections exists in both
   languages; parity check (no key with one language missing); regression-grep
   for hardcoded literals listed in plan.
2. Implement: keys for navigation (findings list, next-finding, back),
   status panel labels, save confirmation, resolved-by-iteration label,
   upload error, compliant panel, deployment doc references.
3. Full suite green. Commit `feat(i18n): R2 keys with EN/FR parity`.

## Task 3: Finding navigation rework (D1)
**Objective:** One-active-finding navigation; selection survives rerun (RH1).
**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_streamlit_compat.py` (source-level assertions)
**Steps:**
1. Failing compat tests first: source must contain active-finding selection
   usage (`ui_state.get_active_finding`), must NOT contain the old
   stacked-expander pattern (assert `for f in revision.findings[:200]` loop
   with per-finding expanders is gone → assert string
   `"with st.expander(\n                    f\"[{f.severity"` absent, or
   equivalent precise markers), and must contain a next-finding action.
2. Implement: findings list as compact rows with select buttons (per finding),
   detail panel for selection, "next open finding" button. Keep decision form
   inside the detail panel.
3. Manual verification via source assertions + full suite green.
   Commit `fix(ui): state-stable finding navigation (D1)`.

## Task 4: Seamless save (D2)
**Objective:** Apply → commit → auto-revision → persisted confirmation, no
manual re-upload (RH2/FR-3).
**Files:**
- Modify: `app/main.py`
- Create: `tests/test_seamless_save.py`
**Steps:**
1. Failing integration tests first (no Streamlit): simulate apply flow with
   ProjectStore+InMemoryRepositoryClient+t101 fixture: after a successful
   apply — (a) iteration file exists in repo, (b) a new revision exists with
   `replacement_reason=CORRECTED_DATA`, (c) revision note names finding+option,
   (d) original workbook bytes unchanged, (e) prior iteration bytes unchanged,
   (f) revalidating the fixed finding against the new revision yields no
   affected cells.
2. Implement in main.py: replace `st.rerun()`-after-apply with FR-3 sequence;
   confirmation stored via ui_state, rendered persistently.
3. Full suite green. Commit `fix(ui): seamless save with auto-revision (D2)`.

## Task 5: Upload guard + status panel + compliant panel
**Objective:** RH4, RH5, RH6.
**Files:**
- Modify: `app/main.py`
- Create: `tests/test_upload_guard.py`
**Steps:**
1. Failing tests: guard helper catches BadZipFile/InvalidFileException/
   OSError/ValueError and returns a friendly bilingual message object; status
   panel computation returns revision/compliance/counts from a project fixture;
   zero-finding project yields compliant-panel data.
2. Implement in main.py. Commit `feat(ui): guarded uploads, status + compliant panels`.

## Task 6: Docs, eval gate, release verification
**Objective:** RH9; client-deployable truth.
**Files:**
- Modify: `docs/DEMO_OPERATOR_GUIDE.md` (client deployment section)
- Modify: `docs/FIXTURES.md` (verify counts against real fixture runs)
- Modify: `.g3/eval.md` (append R2 gates)
- Create: `tests/test_doc_consistency.py`
**Steps:**
1. Failing doc-consistency test: stated test count in docs equals actual
   collected count; stated run commands exist.
2. Rewrite docs sections; verify FIXTURES.md counts by running the real
   inspector over every listed fixture.
3. Full suite green; push to Forgejo; verify remote tip contains all new files
   (ls-tree), not just local commit.
4. Commit `docs: client deployment + truthful counts (R2)`.

## Final integration gate
- `pytest tests/ -q` → all pass < 60 s.
- Fresh Streamlit launch on :8503 (canonical for client demo); scripted
  walkthrough: create project → upload fail fixture → navigate findings →
  apply fix → confirmation persists → new revision present → reports download.
- Push verified via `git ls-tree origin/main`.
