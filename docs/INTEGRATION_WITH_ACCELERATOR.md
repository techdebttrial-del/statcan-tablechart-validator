# Integration Path into the Broader StatCan ESR Accelerator

This validator was built to stand alone for the MVP, but its logic and file
layout deliberately parallel the broader StatCan ESR Accelerator
(`statcan-esr-accelerator/`) documented in this space's `REVIEW_README.md`,
so it can be merged in later with minimal rework. This document is the
concrete integration checklist for that future work.

## Why this matters

The broader Accelerator's pipeline stage 6 ("editorial / polish_draft") and
stage 8 ("publication / format_publication") both already perform bilingual
EN/FR checks (shallow numeric-alignment comparison, HTML/PDF formatting).
This validator's Table 101 / Chart 101 rule engine is a natural deterministic
sub-stage to slot in immediately before or during "editorial," since tables
and charts are typically finalized right after the R analysis / draft-upload
stage (stage 5) and before peer review (stage 7).

## Direct correspondences

| This validator | Broader Accelerator equivalent | Notes |
|---|---|---|
| `core/models.ProjectState` | `core/project_state.py ProjectState` | Same Amendment-audit-trail pattern; field names deliberately aligned |
| `core/models.Amendment` | `core/project_state.py Amendment` | Identical purpose: every override recorded |
| `core/rule_pack_loader.RulePackLoader` | `core/support_pack_loader.py SupportPackLoader` | This validator's rules are deterministic; the Accelerator's are LLM-prompt rules. Both load YAML into a `Rule`/`SupportPackRule` object |
| `core/repository_client.RepositoryClient` | `core/forgejo_client.py ForgejoClient` | Same 4-method contract (`put_file`/`get_file`/`list_files`/`history`); swap implementation only |
| `core/translation_manager.TranslationManager` | `core/translation_manager.py` (broader project) | This validator's version is deliberately simpler (note-level, not draft-level) but uses the same `Translator` plug-point idea |
| `core/report_generator.ReportGenerator` | `core/publication_formatter.py` | Both produce bilingual EN/FR output; formatter targets full publications, this targets audit reports |
| `app/services.py` | `app/services.py` (broader project) | Identical `st.cache_resource` singleton-wiring pattern |
| Rule IDs (`T101-*`, `C101-*`) | `SupportPackRule` IDs | Both are stable, language-neutral identifiers usable in cross-references |

## Concrete migration steps (when the owner is ready)

1. Copy `core/rule_pack_loader.py`, `core/excel_inspector.py`,
   `config/rule_packs/tables101.yaml`, `config/rule_packs/charts101.yaml`,
   and `config/symbols/standard_symbols.yaml` directly into the broader
   Accelerator's `core/` and `config/` directories — no renaming required.
2. Add a new stage key, e.g. `9b: validate_tables_charts`, to
   `core/accelerate.py`'s 9-stage pipeline, calling
   `ExcelInspector.inspect_workbook()` on the analyst's uploaded suppressed
   results workbook (post-SECURE-BREAK, matching this validator's assumption
   that it never touches confidential microdata either).
3. Replace this validator's `RepositoryClient` with the broader Accelerator's
   `ForgejoClient` by changing only the constructor call in
   `app/services.py get_repository()` — `ProjectStore` requires no changes
   because both expose the same four methods.
4. Fold `ProjectState` (this validator) into the broader Accelerator's
   `ProjectState` as an optional `table_chart_validation: ProjectState` field,
   or keep it as a linked sibling object referenced by `project_id` — either
   approach preserves this validator's existing audit trail.
5. Route `TranslationManager.Translator` to the broader Accelerator's
   `core/llm_client.py` LiteLLM gateway instead of `PassthroughTranslator`,
   to produce genuine machine translations rather than the current
   translation-unavailable passthrough. No other code changes are required due
   to the `Translator` protocol.
6. Merge `ReportGenerator` output into the broader Accelerator's stage 8
   `format_publication` bilingual HTML pipeline, or keep it as a standalone
   audit artifact attached to the publication package (see broader project's
   9.4 P3 backlog item: "Export review package — confrontation report +
   amendments + drafts as a single ZIP" — this validator's report fits
   naturally into that ZIP).

## What was deliberately NOT done

- No LLM calls anywhere. Identification and changes are fully deterministic;
  the `TranslationManager.Translator` protocol is the only extension point
  (the broader Accelerator may swap in its LiteLLM gateway later, but this
  validator stays deterministic).
- No live StatCan WDS API integration (out of scope; this tool only inspects
  the uploaded workbook's own structure/content, not published table data).
- No diffing between workbook revisions (each revision is fully revalidated
  from scratch, per project decision).
- No "reviewed and acceptable" state for machine translations (deferred per
  project decision — only original text, machine translation, and optional
  human-verified translation exist as states).
