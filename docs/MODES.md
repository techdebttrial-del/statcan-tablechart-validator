# Validator Design: Deterministic-Only (no LLM)

## Overview

The validator is **deterministic-only**. Identification of rule violations and
the changes to fix them require **no LLM and no network**. This is a
deliberate inversion of the earlier "dual-flavour" design: the LLM-assisted
mode was removed because it added nothing that the deterministic pipeline
could not already do.

## Why the LLM path was removed

- **Identification** — `core/excel_inspector.py` runs every rule as a plain
  Python predicate over openpyxl-parsed workbook structures (cell values,
  fills, formulas, merged ranges, chart series, sheet naming). This was
  already 100% deterministic and LLM-free; a spec guarantee
  ("offline mode must produce identical findings to LLM-assisted mode")
  made the LLM redundant by construction.
- **Changes** — `core/remediation_catalog.py` + `core/remediation_applier.py`
  define a finite, per-rule set of approved changes (enter value, select
  symbol, remove fill, use indent, turn on gridlines) applied to a fresh
  workbook iteration. This was already the primary remediation path; an
  LLM auto-fix suggester only duplicated it with slower, lower-trust results.

Files removed when the LLM path was deleted:

```
core/mode_manager.py       # offline/LLM/cloud mode switching — moot without an LLM
core/fix_suggester.py      # LLM auto-fix suggestions — redundant with the remediation catalogue
core/llm_translator.py     # LLM note translation — PassthroughTranslator covers the bilingual feature
tests/test_llm_thinking_control.py
```

`litellm` was removed from `requirements.txt` / `pyproject.toml`.

## Operating characteristics

| Characteristic | Value |
|----------------|-------|
| Rule checking | Deterministic, all rule packs (Tables 101 / Charts 101) |
| Fix/resolution options | Deterministic per-rule remediation catalogue |
| Bilingual reports | `PassthroughTranslator` (original + clearly labelled) plus human-verified slot |
| Network required | None |
| Hardware required | Any (no GPU, no gateway) |
| Start time | < 1s |

## Translation

Reviewer notes are stored in their original language. The alternate language
field shows a clearly labelled `[FR translation unavailable]` (or
`[EN translation unavailable]`) marker plus the original text, so it is never
mistaken for a real translation. A human-verified translation can be attached
later via `TranslationManager.attach_human_verified_translation`.

## File structure (current)

```
core/
├── excel_inspector.py       # Deterministic rule engine (no LLM)
├── translation_manager.py   # Translator protocol + PassthroughTranslator
├── remediation_catalog.py   # Finite per-rule resolution choices
├── remediation_applier.py   # Apply a choice to a fresh workbook iteration
├── ... (project_store, report_generator, repository_client, etc.)
app/
├── main.py                  # Streamlit UI (no LLM controls)
└── services.py              # Deterministic service wiring only
```

## Re-introducing an LLM later

The `Translator` protocol in `core/translation_manager.py` remains a clean
extension point: swap `PassthroughTranslator` for an LLM-backed translator
without changing any calling code. No other module needs LLM.