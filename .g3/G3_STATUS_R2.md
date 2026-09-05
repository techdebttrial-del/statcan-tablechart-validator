# G3 Status: R2 Client-Release Hardening — COMPLETE

Spec: `.g3/spec-r2-client-release.md` | Plan: `.g3/plan-r2-client-release.md` | Tasks: `.g3/tasks-r2-client-release.md`

Final: **172 tests pass**, remote tip `edb8bb2` on origin/main, app restarted
on final code (http://192.168.2.170:8502, HTTP 200 / health ok).

| Task | Scope | Player | Coach | Status | Outcome |
|------|-------|--------|-------|--------|---------|
| 0. Spec/plan/tasks | docs | cascade2 (direct) | — | ✅ DONE | 71b1e76 |
| 1. ui_state module | app/ui_state.py + tests | session (TDD) | self | ✅ DONE | e65e066 — 7 unit tests; leaves stalled, stopped, done directly |
| 2. i18n keys | app/i18n.py + tests | session (TDD) | self | ✅ DONE | 4cd84bd — EN/FR parity + banned-literal grep |
| 3. Navigation rework (D1) | app/main.py + compat tests | session (TDD) | self | ✅ DONE | fa2d93d — one-active-finding, rerun-stable |
| 4. Seamless save (D2) | app/main.py + fix_flow | session (TDD) | self | ✅ DONE | fa2d93d — apply→commit→auto-revision |
| 5. Upload guard + panels | app/main.py | session (TDD) | self | ✅ DONE | fa2d93d — no tracebacks, status/compliant panels |
| 6. Docs + eval gate | docs + doc tests | session (TDD) | self | ✅ DONE | 187c344 — deployment section, truthful counts, FIXTURES verified |
| V. Verify-phase fixes | fix_flow/applier | session (E2E-driven) | self + judge | ✅ DONE | e972524, edb8bb2 |

## Defects found and fixed during verify (E2E + coach probes)

1. **Lineage chaining** — auto-revision used the iteration filename as the new
   "original filename", orphaning every iteration after the first.
   Fix: root original filename is the single lineage key.
2. **Workbook-level rules falsely "resolved"** — rules with no cell locations
   (gridlines, source, table-per-sheet) were classified resolved by the
   empty-cell heuristic. Fix: resolved = rule no longer fires on active workbook.
3. **rename_sheet traceback** — user text hit `ws.title` unvalidated
   (ValueError on `:` etc.). Fix: friendly refusal for forbidden chars / >31 chars.
4. **Phantom iteration files** — refused applies left uncommitted copies on disk.
   Fix: apply_fix removes the partial copy on failure.

## E2E evidence (2026-09-05, throwaway TVC_DATA_ROOT)

- 13/13 findings open on upload (correct — no false "resolved").
- 7 sequential fixes: rename_sheet→tbl01, empty cells C2/C3, gridlines,
  source, indent, formula — each produced a new committed immutable
  iteration and auto-revision; findings 13→7; selection + confirmation
  persisted across simulated reruns.
- Corrupt upload → `upload_error` sentinel (no traceback).
- 8 revisions persisted, reload round-trip OK, EN/FR reports generated.

## Independent verification round (2026-09-05, second session post-gateway-crash)

Reviewer: independent session (not the implementing agent). Scope: docs → code →
tests → UI. Evidence:

- Full suite: 172 passed (6.5 s), offline, no Streamlit server required.
- E2E demo-defect walkthrough (tests/e2e_demo_defects.py, streamlit AppTest):
  31/31 passed — replays the exact client-reported defects against the real UI:
  D1 selection survives rerun, exactly one detail panel, clean transition to
  next finding, next-open-finding cycling, selection survives EN↔FR switch;
  D2 apply → commit → auto-revision (CORRECTED_DATA + bilingual audit note) →
  persistent confirmation panel, selection cleared, original workbook untouched,
  iteration file committed, fixed rule regenerated out of the new revision.
- Fixture spot check (real inspector): perfect_en 0, fail_all 13, c101_perfect 0,
  c101_fail_all 7 — matches docs.
- Release acceptance + doc-consistency tests: 8 passed.
- Fresh Streamlit launch on :8503 (throwaway TVC_DATA_ROOT): HTTP 200, boots clean.
- Forgejo: HEAD == origin/main after push 9af8e54; ls-tree shows 83 files.
- AT9 no-LLM regression grep: clean.

Verdict: SHIP for client testing deployment.
