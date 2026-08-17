# Spec: StatCan Tables/Charts Validator v2.0 — Dual-Flavour Offline + LLM-Assisted

> **Amendment (2026-08-17):** Goals G3–G6, G9 (dual-flavour architecture, LLM
> mode, cloud escalation, LLM fix-suggestion UI) were **obsolete and removed.**
> Presumption validated: identification (`excel_inspector`) and changes
> (remediation_catalog + applier) are fully deterministic. The LLM added only
> redundant suggestions and mode-switching machinery, so it was dropped from
> the code, UI, dependencies, docs, and tests. See `docs/MODES.md`. The
> deterministic goals (G1, G2, G4, G7, G8) remain the operating contract.

## Problem

The current StatCan Tables/Charts Validator (v0.5 MVP) provides deterministic
rule checking against Tables 101 and Charts 101 standards, but:
1. Rule coverage is incomplete — several Tables 101 and Charts 101 rules are
   only partially implemented or use heuristics
2. No real-world test fixtures exist from actual published StatCan pubs to
   validate against
3. No LLM-assisted mode exists — all findings are manual decisions with no
   auto-fix suggestion capability
4. No graceful fallback between offline (no LLM) and LLM-assisted modes
5. No cloud model escalation when local models are insufficient

## Goals

- [ ] **G1** — Complete Table 101 rule implementation: every rule in the
  `tables101.yaml` pack must have a real Python check, not a heuristic
- [ ] **G2** — Complete Chart 101 rule implementation: every rule in the
  `charts101.yaml` pack must have a real Python check, not a heuristic
- [ ] **G3** — Dual-flavour architecture: a config flag (`use_llm=true/false`)
  switches between offline-only and LLM-assisted mode. No code changes required
  to toggle.
- [ ] **G4** — Offline mode (use_llm=false): runs with zero external dependencies.
  No HTTP calls, no LLM gateway needed. Translation falls back to
  PassthroughTranslator with clear markers.
- [ ] **G5** — LLM-assisted mode (use_llm=true, default): Cascade 2
  (r720-cascade2 via LiteLLM) suggests auto-fixes for findings. Reviewer
  can accept/accept-modified/reject each suggestion.
- [ ] **G6** — Cloud escalation: if Cascade 2 fails or is insufficient, the
  system can escalate via OpenRouter free-tier models (cloud-*-free) or the
  deepseek/deepseek-v4-flash model.
- [ ] **G7** — Real-world test fixtures: minimum 8 Excel workbooks based on
  actual published StatCan publications (Daily, ESR, Insights), with known
  pass/fail cases documented.
- [ ] **G8** — Complete test pass: all rules have pytest RED→GREEN→REFACTOR
  tests. Minimum 100 passing tests across all modules.
- [ ] **G9** — Streamlit UI: mode indicator (offline/LLM-assisted), auto-fix
  suggestion panel, one-click accept/reject for suggested fixes.

## Non-goals

- Not replacing the broader ESR Accelerator — this remains a standalone tool
  that can be merged into Stage 8 later
- Not implementing a full Forgejo integration in this phase — local git
  persistence is sufficient
- Not a production LLM gateway — LiteLLM proxy on localhost is the target
- Not implementing full Charts 101 size detection (openpyxl limitation);
  heuristic width/height checks are acceptable

## Requirements

### Functional

- **FR-1**: System must detect and report all rule violations from Tables 101
  and Charts 101 packs
- **FR-2**: Every finding must include: rule_id, severity, sheet, location,
  bilingual title/description
- **FR-3**: Offline mode must produce identical findings to LLM-assisted mode
  (LLM only adds suggestions, never changes findings)
- **FR-4**: Auto-fix suggestions must be per-finding, not bulk
- **FR-5**: Reviewer must approve/reject each suggestion before any changes
  are applied
- **FR-6**: Cloud escalation must be configurable via environment variable
  (`CLOUD_ESCALATION_MODEL`)
- **FR-7**: System health check panel showing LLM gateway status, model loaded,
  latency

### Non-functional

- **NFR-1**: Offline mode must start and run in < 2 seconds on R720 hardware
- **NFR-2**: LLM-assisted mode must respond within 30 seconds for a typical
  finding (10-20 findings)
- **NFR-3**: All tests must pass in < 30 seconds
- **NFR-4**: Bilingual output (EN/FR) for all user-facing text
- **NFR-5**: Mode switching must not require app restart

## Constraints

- Python 3.10+ / openpyxl / streamlit (existing stack)
- Cascade 2 at `http://192.168.2.170:8080` (M40 GPU)
- LiteLLM proxy at `http://192.168.2.170:4000`
- OpenRouter free-tier for cloud escalation
- Local git persistence (`~/.tvc_data/`)
- Free/local models only for cron/subagents (OpenRouter gate enforced)
- Forgejo as single source of truth

## Open Questions

- [ ] Should auto-fix apply to the workbook file directly or generate a
  diff/patch document?
- [ ] Should the system support batch accept/reject of suggestions?
- [ ] What's the optimal Cascade 2 prompt for fix suggestions?
- [ ] Should we cache LLM responses for identical findings across revisions?

## Adversarial Scenarios

### A1 — LLM gateway unavailable
**Attack:** Cascade 2 or LiteLLM proxy is down
**Defense:** System detects health check failure, falls back to offline mode
  automatically with a clear warning banner
**Test:** Disconnect gateway, verify mode degrades gracefully

### A2 — LLM returns hallucinated fix
**Attack:** Cascade 2 proposes a fix that would corrupt the workbook structure
**Defense:** All suggestions are presented as *suggestions* only — reviewer
  must accept. System validates structural integrity (openpyxl can open it)
  before applying.
**Test:** Send corrupted/conflicting suggestion, verify it's not auto-applied

### A3 — Empty workbook upload
**Attack:** User uploads an empty .xlsx with no data or charts
**Defense:** Inspector returns appropriate findings (no source line, no symbols,
  empty cells). System does not crash.
**Test:** Empty workbook → expected findings, not crash

### A4 — Malformed Excel file
**Attack:** User uploads a non-Excel file with .xlsx extension, or a corrupted
  workbook
**Defense:** openpyxl raises clear error → Streamlit shows user-friendly error
  message, no stack trace exposed
**Test:** Corrupt file → user-friendly error, not traceback

### A5 — Huge workbook (500+ sheets)
**Attack:** User uploads a workbook with hundreds of tables
**Defense:** System processes with reasonable timeout (60s max), shows progress
  indicator. Findings limited to first 200 for UI performance.
**Test:** Large workbook → progress shown, truncated findings

### A6 — Language mismatch
**Attack:** User marks workbook as "fr" but content is actually English
**Defense:** Language setting only affects the FR-NUMBER-FORMAT rule; all other
  rules are language-neutral. No incorrect findings from wrong language flag.
**Test:** EN workbook marked "fr" → only FR-NUMBER-FORMAT affected

### A7 — Concurrent access to same project
**Attack:** Two reviewers open the same project simultaneously
**Defense:** Last-write-wins with git commit; no locking. Amendment audit trail
  captures both changes.
**Test:** Simulated concurrent write → both amendments preserved