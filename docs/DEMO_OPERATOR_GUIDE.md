# StatCan Tables/Charts Validator — Demo Operator Guide

**Audience:** Clerk, demo operator, or client-support person running the application without changing code.

**Purpose:** Demonstrate that the validator can identify compliant and
non-compliant Statistics Canada table/chart workbooks and resolve findings
entirely deterministically — no LLM, no gateway, no network required.

## 1. What the demo demonstrates

The application checks Excel workbooks against deterministic requirements derived from:

- `Tables-101-Guide(1).docx` — Tables 101 visual guide
- `chart101-eng.pdf` — Charts 101 visual guide

The validator produces findings with:

- rule ID;
- severity;
- worksheet and location;
- English and French title/description;
- deterministic per-rule resolution options (change cell value, select symbol, remove fill, etc.);
- reviewer decision and audit trail support.

**Important:** The validator is fully deterministic. There is no LLM, no
LLM-assisted mode, and no gateway toggle. Findings and resolutions are
identical on every machine in every environment.

## 2. Before the client arrives

Run these steps once on the demo machine.

### 2.1 Open the repository

```bash
cd /home/agent/statcan-tablechart-validator
source .venv/bin/activate
```

If the virtual environment does not exist:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2.2 Run the release check

```bash
python -m pytest -q
```

Expected result:

```text
139 passed
```

If this does not pass, do not present the application as release-ready. Contact the technical owner.

### 2.3 Start the Streamlit application

```bash
streamlit run app/main.py --server.port 8502
```

Open the URL printed by Streamlit, normally:

```text
http://localhost:8502
```

For a client on the same network, use the Network URL printed by Streamlit.

### 2.4 Startup

The application has no LLM mode and no gateway toggle. Launch it, open
`http://localhost:8502` (or the Network URL printed by Streamlit for a client
on the same network), and it is ready to demo. There is nothing to enable,
provide, or configure.

## 3. Create a demonstration project

1. Open the **New Project** tab.
2. Enter a clear label, for example `Client demo — Tables and Charts`.
3. Enter the operator/reviewer name.
4. Select **Create**.
5. Open the new project from the **Projects** tab.

Use one project for several uploads if you want to demonstrate revisions. Each replacement is stored as a new audited revision.

## 4. Upload and validate a workbook

For every test case:

1. Open the active project.
2. Select the workbook language (`en` or `fr`).
3. Select **Upload workbook**.
4. Choose a fixture from:

   ```text
   tests/fixtures/test_cases/
   ```

5. Select **Validate**.
6. Review the compliance status and findings.
7. Expand a finding to show its bilingual description and worksheet location.
8. For a client-facing demo, record a decision only if you want to demonstrate the audit workflow. A decision should include a reason and note.
9. Use the report download buttons to demonstrate the English and French reports.

## 5. Expected results for each demo workbook

The following are the expected results from the current committed release. Counts are deterministic and may be used as a quick operator check.

### 5.1 Passing workbooks

| File | Expected result | What to say |
|---|---:|---|
| `t101_perfect_en.xlsx` | **0 findings**; `COMPLIANT` | A compliant English Tables 101 workbook passes cleanly. |
| `t101_perfect_fr.xlsx` | **0 findings**; `COMPLIANT` | A compliant French workbook passes cleanly. |
| `c101_perfect.xlsx` | **0 findings**; `COMPLIANT` | A compliant Charts 101 workbook passes cleanly. |
| `daily_employment_chart_2026.xlsx` | **0 findings**; `COMPLIANT` | A realistic LFS employment chart passes cleanly. |

A passing workbook must not show a false warning merely because it contains a source line, notes, or approved symbols.

### 5.2 Deliberately failing workbooks

| File | Expected result | Main findings to point out |
|---|---:|---|
| `t101_fail_all.xlsx` | **13 findings** (11 unique rules); `NOT_COMPLIANT` | Wrong sheet naming, gridlines off, formulas, empty cells, color fill, missing symbols, missing unit row, missing source, leading-space indentation, row-spanning merge, and missing row stubs. |
| `c101_fail_all.xlsx` | **7 findings**; `NOT_COMPLIANT` | Empty cells, more than six series, invalid chart dimensions, title with superscript, missing source, and missing standard symbols. |

The deliberately failing workbooks are synthetic teaching fixtures, not published StatCan products. Do not describe them as official source material.

### 5.3 Fresh fixtures from recent StatCan publications

These are modeled on recent StatCan Daily releases with engineered failures built in.

| File | Expected result | Purpose |
|---|---:|---|
| `daily_retail_2026.xlsx` | **7 findings**; `NOT_COMPLIANT` | Retail Trade Daily with gridlines off, formula, color fill, row span, empty cells, no source, wrong sheet name. |
| `daily_gdp_q2_2026.xlsx` | **2 findings** | GDP by Industry with gridlines off and abbreviations in headers. Low-severity demo. |
| `daily_cpi_chart_2026.xlsx` | **4 findings**; `NOT_COMPLIANT` | CPI chart with 7 series, title superscript, narrow width, short height. |

### 5.4 Mixed and edge-case workbooks

| File | Expected result | Purpose |
|---|---|---|
| `mixed_realistic_cpi.xlsx` | Findings expected | Mixed CPI-style table/chart content. Demonstrates review of a realistic mixed workbook. |
| `mixed_realistic_lfs.xlsx` | Findings expected | Mixed Labour Force Survey-style content. Demonstrates a realistic revision candidate. |
| `bilingual_gdp.xlsx` | Findings expected | English/French GDP-style sheets. Demonstrates language selection and bilingual output. |
| `edge_cases.xlsx` | Findings expected; no crash | Empty, header-only, single-cell, and minimal-sheet cases. Demonstrates resilience to incomplete workbooks. |
| `t101_fail_specific.xlsx` | Targeted findings | Individual table-rule examples. Use when the client asks to isolate one rule. |

## 6. Recommended client demonstration sequence

### Demonstration A — Clean pass

1. Create/open a project.
2. Upload `t101_perfect_en.xlsx`.
3. Select English and validate.
4. Show `COMPLIANT` and zero findings.
5. Upload `t101_fail_all.xlsx` as a replacement revision.
6. Show that the same deterministic engine identifies 13 findings across 11 unique rules.
7. Expand one finding and show its severity, rule ID, sheet, location, and bilingual text.

**Expected message:** Everything the validator does is deterministic and
requires no LLM or network.

### Demonstration B — Charts

1. Upload `c101_perfect.xlsx`.
2. Show zero findings.
3. Replace it with `c101_fail_all.xlsx`.
4. Show seven findings, especially the series-count, size, title-superscript, source, and symbol checks.

### Demonstration C — Resolve a finding deterministically

1. Validate `t101_fail_all.xlsx`.
2. Expand a finding (e.g. `T101-NO-EMPTY-CELLS`).
3. Pick a resolution from the **Deterministic resolution options** — for
   example choose an approved symbol for the empty cell.
4. Select **Create new workbook iteration**.
5. Show that a fresh immutable iteration was created, committed to git, and is
   downloadable.
6. Explain that the change is deterministic and explicit — no AI "guess", and
   the reviewer always approves the actionable change.

**Note:** Use `T101-NO-EMPTY-CELLS` for the remediation demo. Chart rule
remediation options (resize, remove series) require manual Excel handling
and are not auto-applied.

### Demonstration D — Bilingual workflow

1. Select French as the UI language, or upload `t101_perfect_fr.xlsx` with language `fr`.
2. Show the French titles and descriptions.
3. Download both the English and French reports.
4. Explain that the alternate-language text is clearly marked as
   translation-unavailable (a deterministic passthrough), with a spot for a
   human-verified translation.

### Demonstration E — Fresh real-world fixtures

1. Upload `daily_retail_2026.xlsx` to show a realistic Retail Trade Daily with multiple failures.
2. Upload `daily_cpi_chart_2026.xlsx` to show a realistic CPI chart with chart-specific failures.
3. Upload `daily_employment_chart_2026.xlsx` to show a realistic LFS chart that passes cleanly.

## 7. What counts as a successful demo

The demo is successful when the operator can show all of the following:

- the app starts and is reachable in a browser;
- a compliant table returns zero findings;
- a compliant chart returns zero findings;
- a deliberately failing table returns 13 findings across 11 unique rules;
- a deliberately failing chart returns seven findings;
- findings include bilingual text and locations;
- a reviewer can resolve a finding through the deterministic resolution options and download the new iteration;
- an operator can create a project, upload a revision, and download reports;
- a reviewer can record a decision with a reason and note.

## 8. Troubleshooting

### The page does not open

Confirm that the terminal running Streamlit is still open. Restart with:

```bash
cd /home/agent/statcan-tablechart-validator
source .venv/bin/activate
streamlit run app/main.py --server.port 8502
```

### A passing fixture shows findings

Stop the demo and run:

```bash
python -m pytest -q
```

Then check that the repository is on the verified `main` commit. Do not manually edit the workbook during the demo.

### The upload is rejected

Confirm that the selected file is an `.xlsx` workbook and that the file was selected from the repository fixture directory. A corrupted or incorrectly renamed file should not be used for the main demo.

### The client asks about unsupported chart checks

Answer honestly: the deterministic engine covers the checks observable through `openpyxl`. Some detailed drawing-level semantics, such as certain tick-mark or horizontal-line properties, are limited by the Excel parser and are documented in the repository. They remain review items rather than being falsely reported as verified.

## 9. After the demo

- Do not delete the project or its revisions if the audit trail is needed.
- Download the English and French reports.
- Record any client feedback as a reviewer note.
- Close the project only after confirming that reports and decisions are saved.
- Do not commit client workbooks to the source repository unless the technical owner explicitly approves it. The repository fixtures are demonstration data.

## 10. Technical owner handoff

The authoritative project and release evidence are in Forgejo. The operator guide is accompanied by:

- `.g3/spec.md` — requirements and adversarial scenarios;
- `.g3/eval.md` — acceptance criteria;
- `docs/FIXTURES.md` — fixture inventory and expected findings;
- `docs/ORIGINAL_STATCAN_REQUIREMENTS.md` — source-guide requirements;
- `tests/test_release_acceptance.py` — automated release gates.

The expected release test command is:

```bash
source .venv/bin/activate
python -m pytest -q
```

Expected result: **139 passed**.
