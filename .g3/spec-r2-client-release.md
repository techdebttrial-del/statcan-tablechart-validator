# Spec R2: Client-Release Hardening — StatCan Tables/Charts Validator

> Status: GOVERNING for the client-release increment. Supersedes the R2-relevant
> parts of `.g3/spec.md` (v2.0, amended 2026-08-17) which remain historical context.
> Source requirements: `docs/ORIGINAL_STATCAN_REQUIREMENTS.md` (Tables 101 /
> Charts 101), `docs/DEMO_OPERATOR_GUIDE.md`, client demo feedback 2026-09-05.

## Problem

The validator was demoed to clients (2026-09-05). The concept was liked, but two
interaction defects were observed live:

1. **D1 — finding navigation**: opening one problem did not transition nicely to
   the next. Root cause: findings render as stacked `st.expander` widgets in
   `app/main.py`; every action calls `st.rerun()`, which collapses all expanders
   to default and loses the reviewer's place.
2. **D2 — save flow**: saving a change did not go seamlessly. Root cause: after
   applying a remediation the app calls `st.rerun()` (wiping the success banner
   and all form inputs), and the designed flow is manual: download the new
   iteration, then re-upload it as the next revision. Three page resets and two
   manual steps per fix.

The code is shared with clients for testing next week; the deployed build must be
defect-free, auditable, and deployable from the README alone.

## Goals (all testable)

- [ ] **RH1** — Finding navigation is state-stable: the reviewer's selection
  survives every rerun; moving to the next problem is one explicit action.
- [ ] **RH2** — Seamless save: applying an approved fix produces a persisted
  confirmation (survives rerun), commits the iteration, and automatically creates
  the next workbook revision from that iteration; no manual download/re-upload
  is required.
- [ ] **RH3** — Findings display always reflects the ACTIVE workbook
  (latest iteration), reconciled with persisted revision findings; a fixed
  finding is visibly resolved and is not re-offered for remediation.
- [ ] **RH4** — Malformed/corrupt uploads show a bilingual friendly error, never
  a traceback (original spec scenario A4, still violated).
- [ ] **RH5** — Upload/validation outcome is a persistent status panel (revision,
  compliance, finding counts) — not a transient banner.
- [ ] **RH6** — Zero-finding workbooks render an explicit bilingual compliant
  panel, not an empty section.
- [ ] **RH7** — All user-facing strings are bilingual via `app/i18n.t`; no
  hardcoded English remnants.
- [ ] **RH8** — UI state logic is unit-testable in a `app/ui_state.py` module
  (no logic buried in `main.py` render code); UI-behaviour regressions are
  covered by tests, not manual clicking.
- [ ] **RH9** — Documentation tells the truth: operator guide, FIXTURES.md counts,
  and a client deployment section (venv → run → data root → port) verified by a
  doc-consistency test.

## Non-goals

- No new validation rules or rule-pack changes.
- No LLM anything (deterministic-only is a hard property; regression test exists).
- No authentication/multi-tenant work.
- No redesign of the decision/waiver workflow.

## Requirements

### Functional

- **FR-1**: Active finding selection is stored in `st.session_state` via a
  state module; render code reads it; it is not reset by `st.rerun()`.
- **FR-2**: Exactly one finding detail (description, affected cells,
  remediation options, decision form) is displayed at a time; the finding list
  remains visible for selection.
- **FR-3**: After a successful `apply_remediation`: (a) commit the iteration
  file via the repository client; (b) create the next revision from the new
  iteration with `replacement_reason=CORRECTED_DATA` and an audit note naming
  the finding and option; (c) store the result (iteration name, commit id,
  new revision number) in session-backed UI state; (d) render it until the
  next apply or dismiss.
- **FR-4**: The displayed findings for the active revision are computed from
  `current_workbook` (the latest iteration) via `resolve_affected_cells`
  revalidation; findings no longer detected on the active workbook are shown
  as resolved-by-iteration (rule id, iteration name), and are excluded from
  the remediation choices.
- **FR-5**: Upload path catches `zipfile.BadZipFile`,
  `openpyxl.utils.exceptions.InvalidFileException`, `OSError`, and `ValueError`
  and renders a bilingual `st.error`; upload state is reset afterwards.
- **FR-6**: A status panel at the top of the project view always shows: active
  revision number, compliance status, open/resolved finding counts, and current
  workbook base — computed from the store, not from transient banners.
- **FR-7**: `grep`-verifiable: every literal user-facing string in `app/main.py`
  routes through `app/i18n.t` or the EN/FR conditional pattern used for catalog
  labels; a compat test fails on regression strings.
- **FR-8**: `app/ui_state.py` exposes pure functions for: active finding
  selection (get/set/clear), last-apply result (get/set/clear), and the
  auto-revision note builder. All have unit tests.
- **FR-9**: `docs/DEMO_OPERATOR_GUIDE.md` gains a "Client deployment" section:
  clone → venv → pip install → streamlit run → port/URL; TVC_DATA_ROOT for a
  clean demo slate; keep-alive note. A doc-consistency test asserts stated test
  counts equal actual collected test count.

### Non-functional

- **NFR-1**: Full test suite passes in < 60 s.
- **NFR-2**: No finding may be remediated twice against the same workbook
  (stale selection rejected — existing behaviour, must remain).
- **NFR-3**: All mutation continues to require explicit reviewer approval
  (button press); auto-revision never mutates the original or prior iterations.
- **NFR-4**: EN/FR parity for every new string (both languages present in i18n).

## Constraints

- Python 3.11, Streamlit >= 1.32, openpyxl >= 3.1 (existing stack).
- Forgejo `origin/main` is the source of truth; commit per task; push verified.
- Canonical working tree: `/home/agent/forge/workspace/statcan-tablechart-validator`
  (the tree the demo app serves).
- Tests must not require a running Streamlit server; `pytest` only.

## Adversarial scenarios (G3 coach must verify each)

- **A1**: Select finding → apply fix → rerun: selection and confirmation
  persist; list still shows all findings with updated statuses.
- **A2**: Apply fix to finding F on iteration_01 → iteration_02 exists, F's
  edit present, iteration_01 byte-identical, original byte-identical.
- **A3**: Re-open the same finding after its fix: remediation options absent
  (resolved) — stale selection cannot double-fix.
- **A4**: Upload `not-an-xlsx.xlsx` (bytes garbage): bilingual error, no traceback.
- **A5**: Upload a compliant fixture: compliant panel, zero findings, downloads
  still visible side-by-side.
- **A6**: Switch language EN↔FR mid-session: no English remnants in FR mode.
- **A7**: Suite runs offline, no Streamlit server, < 60 s.
