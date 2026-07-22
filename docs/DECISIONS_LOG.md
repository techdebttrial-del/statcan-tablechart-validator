# Scoping Decisions Log

This MVP was scoped through an interactive clarification process. This log
captures each decision so the rationale is preserved alongside the code.

## 1. Bilingual interface from the start

**Decision:** English and French UI from the start, not added later.
**Rationale:** The broader StatCan ESR Accelerator captured in this space is
already fully bilingual end-to-end (its own `OBJECTIVES.md` incorrectly
claims English-only, which the review flagged as documentation drift). This
validator adopts the same bilingual-first posture for consistency and to
avoid repeating that documentation drift.

## 2. Bilingual audit reports for every run

**Decision:** Every validation run produces both an English and a French
human-readable report, regardless of the reviewer's interface language or
the workbook's language.
**Rationale:** Matches the broader Accelerator's "bilingual publication
artifact" output convention (stage 8, `format_publication`).

## 3. Free-text note translation labeling

**Decision:** Reviewer free-text notes are stored in their original
language with a clear label, and shown in the alternate-language report as
a machine translation, explicitly labeled as such and identifying the
source language. A human-verified translation may be attached later and
takes display precedence over the machine translation, without replacing
the original note.
**Rationale:** Preserves audit fidelity (the original reviewer's exact words
are authoritative) while still supporting bilingual readability, matching
the spirit of the broader Accelerator's stage 5 "FR auto-translate...
falls back to placeholder on exception" pattern, but implemented with
explicit, always-visible labeling rather than silent substitution.

## 4. No "reviewed and acceptable" state for machine translations

**Decision:** Explicitly deferred / not built in the MVP.
**Rationale:** Keeps the decision-state model small: a translation is either
machine-generated (default) or has an attached human-verified version. No
intermediate "reviewed but not verified" status.

## 5. Structured decision capture

**Decision:** Every finding decision requires: a decision type (accepted
fix / rejected / waived), a structured reason from a fixed enum
(`DecisionReason`), and a free-text bilingual note. Waived decisions may
optionally carry a target resolution date (distinguishing temporary
"pending correction" from a "permanent waiver") and a follow-up owner.
**Rationale:** Produces a queryable, consistent audit trail while still
capturing reviewer nuance in free text — mirrors the broader Accelerator's
`ReviewComment` / peer-review decision-capture pattern.

## 6. Saved projects, replacement, and closure

**Decision:**
- Projects are persisted indefinitely with an auto-generated immutable ID
  (`TVC-YYYYMMDD-XXXXXXXX`) plus a human-editable label.
- A reviewer can replace the workbook within the same project (new,
  fully-revalidated revision, with a structured replacement reason and
  note) or start a new, separate project instead.
- Revalidation on replacement is always a full, fresh pass — no diffing
  logic in the MVP.
- Projects can be closed and reopened; closing does not delete history.
**Rationale:** Matches the broader Accelerator's amendment-based audit
trail philosophy ("Analyst amends, system proposes... every stage records
amendments") while keeping the MVP's replacement logic simple.

## 7. Rule pack source material

**Decision:** Deterministic rules were extracted directly from the
Statistics Canada **Tables 101** and **Charts 101** reference guides
provided in this space (`tables101-eng.pdf`, `chart101-eng.pdf`), covering
Excel-only authoring, one-table/chart-per-sheet naming, gridlines, no
formulas/no fill color, standard symbol usage and definitions, empty-cell
prohibition, six-series chart limit, chart sizing bounds, source-line
presence, and related structural requirements.
**Rationale:** Ensures the rule set is traceable to StatCan's own published
corporate standards rather than inferred.
