# Plan R2: Client-Release Hardening

Spec: `.g3/spec-r2-client-release.md`. Canonical tree:
`/home/agent/forge/workspace/statcan-tablechart-validator`.

## Architecture

Current UI (`app/main.py`, 308 lines) is a single-file render tree with:
- stacked expanders per finding (D1 root cause),
- `st.rerun()` after every mutation without persisted status (D2 root cause),
- business logic inlined in render code (untouchable by tests).

New structure:

```
app/
├── ui_state.py      # NEW: pure session-state logic (RH8/FR-8), unit-tested
│    #   - active finding selection: get/set/clear (session key "active_finding_id")
│    #   - last apply result: get/set/clear (session key "last_apply_result")
│    #   - auto_revision_note(finding, option, iteration_name) -> str  (bilingual)
├── main.py          # MODIFIED: one-active-finding navigation, seamless save,
│                    #   status panel, guarded upload, i18n compliance
├── services.py      # unchanged (deterministic wiring)
└── i18n.py          # MODIFIED: add new keys (EN+FR parity)
```

### Key design decisions

1. **Navigation (RH1/FR-1/FR-2):** findings list renders as compact selectable
   rows (radio or buttons, not expanders). `ui_state` holds
   `active_finding_id`; one detail panel renders for the selection. Reruns no
   longer collapse anything. "Next open finding" button advances selection.
2. **Seamless save (RH2/FR-3):** after `apply_remediation` succeeds:
   commit file → `store.add_workbook_revision(...)` from the new iteration with
   `replacement_reason=CORRECTED_DATA` → store result in
   `ui_state.set_last_apply_result(...)`. NO `st.rerun()` immediately after —
   the confirmation renders from session state on the natural next rerun.
   Download buttons already pick up the new iteration via `latest_iteration`.
3. **Active-workbook findings (RH3/FR-4):** keep persisted `revision.findings`
   as the audit record; for display, revalidate each finding against
   `current_workbook` via `resolve_affected_cells`; findings with zero
   remaining affected cells AND not in the re-detected finding set render as
   "resolved by iteration" rows without remediation options.
4. **Guarded upload (RH4/FR-5):** wrap `store.add_workbook_revision` call in
   try/except (BadZipFile, InvalidFileException, OSError, ValueError) →
   bilingual `st.error`; no traceback.
5. **Status panel (RH5/FR-6):** top-of-project panel: revision, compliance,
   open/resolved counts, workbook base — always computed from store.
6. **i18n (RH7/FR-7):** all new strings through `t()` or EN/FR conditional;
   compat test greps for regression literals.

## File impact

| File | Action | Lines |
|---|---|---|
| `app/ui_state.py` | create | ~90 |
| `app/main.py` | modify | major rework of findings/save sections |
| `app/i18n.py` | modify | +15 keys |
| `tests/test_ui_state.py` | create | ~120 |
| `tests/test_ui_i18n_compliance.py` | create | ~60 |
| `tests/test_upload_guard.py` | create | ~80 |
| `tests/test_seamless_save.py` | create | ~140 |
| `docs/DEMO_OPERATOR_GUIDE.md` | modify | +deployment section |
| `docs/FIXTURES.md` | verify counts | fix if stale |
| `.g3/eval.md` | append R2 gates | +30 |

## Testing strategy

- `ui_state.py` logic: pure pytest, fake session dict (Streamlit not required).
- Seamless save: ProjectStore + InMemoryRepositoryClient + real fixture
  workbook; assert iteration committed, revision created, note recorded,
  original + prior iterations byte-identical.
- Upload guard: feed corrupt bytes to the same guard function (extract the
  try/except into a callable `app/main.py`-level helper or ui_state) —
  assert friendly error class raised/returned, no traceback.
- i18n compliance: grep `main.py` for hardcoded strings; assert key parity EN/FR.
- Doc consistency: count `pytest --co -q` and compare to number claimed in docs.

## Task order (dependencies)

T1 ui_state (foundation) → T2 i18n keys → T3 navigation rework →
T4 seamless save → T5 upload guard + status panel + compliant panel →
T6 docs + eval + release verification.
