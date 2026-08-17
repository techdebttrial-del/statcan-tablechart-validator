# Fixing Findings — Deterministic Remediation

Identifying violations and fixing them are both fully deterministic; no LLM
is involved. This page describes the remediation (change) workflow.

## Workflow

```
Finding detected → Reviewer picks a resolution option → Applies → validates
                                                          ↓
                                      Fresh immutable workbook iteration + git commit
                                                          ↓
                                              Download & re-upload as next revision
```

## How changes work

For an open finding, the UI shows the **deterministic resolution options** for
that rule, sourced from `core/remediation_catalog.py`. Options are bounded and
finite — the reviewer never relies on an AI "guess" for a fix.

| Option | Applies to | What it does |
|--------|-----------|--------------|
| `enter_value` / `replace_with_value` | text input | Writes the typed value into the affected cells |
| `select_symbol` | approved-symbol select | Writes one of the approved StatCan symbols (`..` `...` `0s` `p` `r` `x` `E` `F`) |
| `remove_fill` | `T101-NO-COLOR-FILL` | Clears cell background fill |
| `use_indent` | `T101-INDENT-FEATURE` | Strips leading spaces and sets Excel indent |
| `turn_on` | `T101-GRIDLINES-ON` | Enables worksheet gridlines |
| `leave_open` | any | Still requires reviewer handling in Excel — not auto-applied |
| `resize_chart`, `remove_series`, `enter_source`, `remove_calculation` | charts/source | Requires reviewer handling in Excel — not auto-applied |

## Safety / integrity

1. The source workbook is **never opened for writing**. A fresh immutable copy
   is created via `iteration_lineage.next_iteration()`.
2. `core/remediation_applier.apply_remediation()` re-inspects the source so an
   already-fixed cell cannot be selected or overwritten again
   (`resolve_affected_cells`).
3. Only cells reported as affected for that finding are writable.
4. The generated iteration is committed to git history and offered for
   download; the reviewer uploads it as the next revision for re-validation.

## Configuration

No environment variables are required. Each rule's options are defined inline
in `core/remediation_catalog.py`.