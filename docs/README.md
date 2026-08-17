# StatCan Tables/Charts Validator (MVP)

A standalone Streamlit application that inspects `.xlsx` workbooks against
Statistics Canada's **Tables 101** and **Charts 101** publication standards,
records reviewer decisions with a structured reason + free-text bilingual
note, and produces bilingual (English/French) audit reports.

This tool is designed to **stand on its own** for the MVP, while deliberately
mirroring the architecture, naming, and conventions of the broader
**StatCan ESR Accelerator** captured elsewhere in this space, so it can be
folded into that project later as an additional deterministic pipeline stage
with minimal rework. See `docs/ARCHITECTURE.md` and
`docs/INTEGRATION_WITH_ACCELERATOR.md` for details.

## Quick start

```bash
cd statcan-tablechart-validator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py --server.port 8502
```

Run tests:

```bash
python -m pytest tests -q
```

## What it does

1. A reviewer creates a **saved review project** (auto-generated ID + human
   label, e.g. `TVC-20260721-8F3A — Labour Force Tables, July 2026`).
2. The reviewer uploads a workbook. The engine runs every deterministic rule
   in `config/rule_packs/tables101.yaml` and `config/rule_packs/charts101.yaml`
   against the workbook and produces a list of **Findings**.
3. For each finding, the reviewer records a **Decision**: accept the fix,
   reject, or waive — each with a structured reason plus a free-text note in
   the reviewer's language, optionally with a target resolution date for
   pending items.
4. Free-text notes are stored in their original language. The alternate
   language shows a clearly labelled translation-unavailable marker plus the
   original text (deterministic — no LLM); a human-verified translation can be
   attached later.
5. Reviewers can **replace the workbook** in the same project (creating a new
   revision, fully revalidated from scratch — no diffing in the MVP) or start
   a brand-new project referencing the prior one.
6. Projects can be **closed** (and reopened) without deleting history.
7. Every validation run produces **two bilingual audit reports** (English and
   French), plus machine-readable JSON, and a full audit trail of amendments.

## Repository layout

```
statcan-tablechart-validator/
├── app/                     Streamlit UI (thin entry point + services)
├── core/                    Deterministic domain logic (no LLM dependency)
├── config/
│   ├── rule_packs/          tables101.yaml, charts101.yaml
│   └── symbols/             standard_symbols.yaml
├── tests/                   pytest unit tests + fixtures
├── docs/                    This documentation set
└── requirements.txt
```

## Key design decisions (from project scoping)

| Decision | Resolution |
|---|---|
| Decision capture | Structured reason (dropdown) + free-text note, both required for rejections/waivers |
| Unresolved findings | Optional target resolution date distinguishes pending correction vs. permanent waiver |
| Saved projects | Persistent list backed by Git, reopenable at any time |
| Workbook replacement | Both "new revision in same project" and "new separate project" supported, both fully audited |
| Revalidation | Always a fresh, full revalidation — no diffing in MVP |
| Project naming | Automatically generated immutable ID + human-readable label |
| Project closure | Supported (low priority for MVP), reversible |
| UI language | English and French from the start |
| Report language | Both English and French reports generated for every run |
| Note translation | Original + labeled machine translation from source language; optional human-verified override |
| Translation review state | Not implemented in MVP (explicitly deferred) |

See `docs/DECISIONS_LOG.md` for the full scoping conversation this MVP was
built from.
