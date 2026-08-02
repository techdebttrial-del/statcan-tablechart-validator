# Plan: StatCan Tables/Charts Validator v2.0

## Overview
Enhance the existing v0.5 validator with complete rule coverage, dual-flavour
architecture (offline + LLM-assisted), real-world test fixtures, and full test suite.

## Tasks (in order)

### T1 — Complete Tables 101 rule engine
- [ ] T1.1: Implement `T101-NO-EMPTY-CELLS` — check every data cell for empty values
- [ ] T1.2: Implement `T101-STANDARD-SYMBOLS` — verify symbols match standard registry
- [ ] T1.3: Implement `T101-SYMBOL-SUPERSCRIPT-COLUMN` — detect superscript formatting
- [ ] T1.4: Implement `T101-FOOTNOTES-OWN-ROW` — check footer row separation
- [ ] T1.5: Implement `T101-ROW-STUB-RELATED` — semantic check on row stub relevance
- [ ] T1.6: Implement `T101-FULL-TEXT-OVER-SYMBOLS` — heuristic preference check
- [ ] T1.7: Implement `T101-EXCEL-ONLY` — verify file format is xlsx

### T2 — Complete Charts 101 rule engine
- [ ] T2.1: Implement `C101-EXCEL-ONLY` — verify chart source is Excel
- [ ] T2.2: Implement `C101-ONE-CHART-DATA-PER-SHEET` — verify chart table count
- [ ] T2.3: Implement `C101-NO-EXTRA-CALCULATIONS` — detect helper calculations
- [ ] T2.4: Implement `C101-C101-NO-TITLE-SUPERSCRIPT` — check chart title
- [ ] T2.5: Implement `C101-NO-UOM-IN-AXIS-LABELS` — detect units in axis labels
- [ ] T2.6: Implement `C101-SYMBOL-REQUIRES-NOTE` — verify symbol → note matching
- [ ] T2.7: Implement `C101-HORIZONTAL-LINE-NOTE` — check reference line notes
- [ ] T2.8: Implement `C101-MAP-IMAGE-DESCRIPTIVE-TEXT` — check alt text
- [ ] T2.9: Implement `C101-NO-DUAL-TICKMARKS` — detect duplicate tick marks
- [ ] T2.10: Implement `C101-GRIDLINES-NO-DATALABELS` — gridline/label conflict

### T3 — Dual-flavour architecture
- [ ] T3.1: Create `core/mode_manager.py` — config flag + health check logic
- [ ] T3.2: Implement offline detector (no HTTP calls, no LLM dependency)
- [ ] T3.3: Implement LLM-assisted connector (Cascade 2 via LiteLLM)
- [ ] T3.4: Implement cloud escalation path (OpenRouter free-tier)
- [ ] T3.5: Wire mode selection into Streamlit sidebar
- [ ] T3.6: Show mode indicator + health status in Streamlit

### T4 — Auto-fix suggestion engine
- [ ] T4.1: Create `core/fix_suggester.py` — per-finding LLM suggestion logic
- [ ] T4.2: Each suggestion includes: finding_id, description, proposed_change
- [ ] T4.3: Streamlit panel for accept/reject/accept-modified
- [ ] T4.4: Apply accepted fix to workbook and trigger re-validation
- [ ] T4.5: Cache suggestions per finding for repeat view

### T5 — Real-world test fixtures
- [ ] T5.1: Create perfect-compliant table workbook (tables101)
- [ ] T5.2: Create perfect-compliant chart workbook (charts101)
- [ ] T5.3: Create table failure workbook (one failure per rule)
- [ ] T5.4: Create chart failure workbook (one failure per rule)
- [ ] T5.5: Create realistic CPI inflation chart (based on StatCan Daily)
- [ ] T5.6: Create realistic LFS employment table (based on StatCan Daily)
- [ ] T5.7: Create realistic GDP-by-industry table (based on StatCan ESR)
- [ ] T5.8: Create mixed pass/fail workbook (realistic publication)
- [ ] T5.9: Create bilingual (EN/FR) workbook
- [ ] T5.10: Document expected findings for each fixture

### T6 — Comprehensive test suite
- [ ] T6.1: Tests for every Tables 101 rule (pass + fail cases)
- [ ] T6.2: Tests for every Charts 101 rule (pass + fail cases)
- [ ] T6.3: Tests for offline mode — verify zero LLM/HTTP calls
- [ ] T6.4: Tests for LLM-assisted mode — verify Cascade 2 integration
- [ ] T6.5: Tests for mode switching — toggle without restart
- [ ] T6.6: Tests for bilingual report generation
- [ ] T6.7: Tests for real-world fixtures against expected findings
- [ ] T6.8: Tests for edge cases (empty workbook, corrupt file, huge workbook)

### T7 — Documentation
- [ ] T7.1: Update ARCHITECTURE.md with dual-flavour design
- [ ] T7.2: Create docs/MODES.md — offline vs LLM-assisted guide
- [ ] T7.3: Create docs/FIXTURES.md — test case documentation
- [ ] T7.4: Create docs/AUTO_FIX.md — fix suggestion workflow
- [ ] T7.5: Update README.md with v2.0 features
- [ ] T7.6: Push all to Forgejo with proper commit messages

## Milestones

| Milestone | Tasks | Estimate |
|-----------|-------|----------|
| M1: Complete rule engine | T1, T2 | ~2 hours |
| M2: Dual-flavour architecture | T3, T4 | ~1.5 hours |
| M3: Test fixtures + test suite | T5, T6 | ~2 hours |
| M4: Documentation + commit | T7 | ~30 min |