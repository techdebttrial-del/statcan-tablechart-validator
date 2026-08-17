# Architecture

## Layered view

```
app/main.py            Streamlit entry point (thin, mirrors app.py in the
                        broader Accelerator: page config, session init,
                        service wiring)
app/services.py         Singleton service constructors, cached via
                        st.cache_resource (mirrors app/services.py pattern)
app/i18n.py              Minimal EN/FR UI string table

core/models.py           Dataclasses: ProjectState, WorkbookRevision,
                        Finding, Decision, Amendment, BilingualNote,
                        Translation (mirrors core/project_state.py's
                        ProjectState / Amendment pattern from the broader
                        Accelerator)
core/rule_pack_loader.py Loads YAML rule packs (mirrors
                        core/support_pack_loader.py's SupportPackLoader)
core/excel_inspector.py  Deterministic openpyxl-based rule engine —
                        NO LLM calls (mirrors the Accelerator's
                        "deterministic-first" principle)
core/translation_manager.py  EN/FR note translation, pluggable Translator
                        protocol (mirrors translation_manager.py)
core/repository_client.py    Git-backed file CRUD, same method contract
                        as core/forgejo_client.py in the broader
                        Accelerator (put_file/get_file/list_files/history)
core/project_store.py    Orchestration: create/close/reopen projects,
                        add workbook revisions, record decisions,
                        persist ProjectState as JSON via
                        RepositoryClient
core/report_generator.py Bilingual (EN+FR) Markdown/HTML audit report
                        generator (mirrors publication_formatter.py's
                        bilingual HTML formatting convention)

config/rule_packs/*.yaml   Tables 101 / Charts 101 rules, versioned,
                        with EN/FR titles and descriptions, language-
                        neutral rule IDs
config/symbols/*.yaml      Standard Table Symbols registry (unmodifiable
                        definitions per Standards Division)
```

## Data flow

1. `ProjectStore.create_project()` → `ProjectState` with an auto-generated
   ID (`TVC-YYYYMMDD-XXXXXXXX`) and human label.
2. `ProjectStore.add_workbook_revision()`:
   - Hashes the uploaded file (SHA-256)
   - Persists it via `RepositoryClient.put_file()` (git commit)
   - Runs `ExcelInspector.inspect_workbook()` → list of `Finding`
   - Computes `ComplianceStatus` (blocking = critical/error severity, open)
   - Appends an `Amendment` (`workbook_uploaded` or `workbook_replaced`)
   - Persists `ProjectState` as `project.json`
3. `ProjectStore.record_decision()`:
   - Builds a `BilingualNote` via `TranslationManager` (original + labeled
     machine translation)
   - Updates the `Finding.status` (accepted_fix / rejected / pending_correction
     / permanently_waived)
   - Recomputes `WorkbookRevision.compliance_status`
   - Appends an `Amendment` (`decision_recorded`)
4. `ReportGenerator.generate_both()` renders the same underlying data as two
   parallel Markdown documents (`en`, `fr`), with reviewer notes shown as
   original-language text plus a clearly labeled machine translation.

## Determinism guarantee

No rule evaluation depends on an LLM call — this is a deliberate, hard
property of the tool. All checks in `ExcelInspector` are plain Python
predicates over openpyxl-parsed workbook structures (cell values, fills,
formulas, merged ranges, chart series counts, sheet naming patterns), and all
changes go through the deterministic remediation catalogue
(`core/remediation_catalog.py` + `remediation_applier.py`). This mirrors the
broader Accelerator's core design principle: *"Deterministic-first — LLM only
for targeted disambiguation."* The `TranslationManager.Translator` protocol is
the only extension point where an LLM gateway could later be wired in (e.g., to
replace `PassthroughTranslator` with a call into the broader Accelerator's
`core/llm_client.py` LiteLLM wrapper) — swapping it does not change any calling
code and nothing else needs an LLM.

## Persistence contract

`RepositoryClient` exposes the same four-method contract the broader
Accelerator's `core/forgejo_client.py` uses: `put_file`, `get_file`,
`list_files`, `history`. The MVP implementation shells out to a local `git`
repository so the tool works fully offline; `InMemoryRepositoryClient` is a
test double with the same interface. Swapping in a Forgejo-backed
implementation later (as used by the broader Accelerator) requires no
changes to `ProjectStore` or any UI code — only a different constructor.

## Rule pack format

Each rule in `config/rule_packs/*.yaml` has:

```yaml
- id: T101-NO-EMPTY-CELLS
  severity: error
  title_en: "..."
  title_fr: "..."
  description_en: "..."
  description_fr: "..."
  check: "<human-readable predicate, implemented in ExcelInspector>"
```

Rule IDs are stable and language-neutral (e.g. `T101-NO-FORMULAS`), so audit
history, saved decisions, and cross-references to Table 101/Chart 101 remain
valid regardless of interface language. This mirrors the broader
Accelerator's `SupportPackRule` / `SupportPackCheck` object shape produced by
`SupportPackLoader`, adapted here for deterministic (not LLM-prompt-injected)
evaluation.
