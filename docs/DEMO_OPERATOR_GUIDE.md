# StatCan Tables/Charts Validator — Demo Operator Guide

**Audience:** Clerk, demo operator, or client-support person running the application without changing code.

**Purpose:** Demonstrate that the validator can identify compliant and non-compliant Statistics Canada table/chart workbooks, operate without an LLM, and optionally use the local Cascade 2 LLM for suggestions.

## 1. What the demo demonstrates

The application checks Excel workbooks against deterministic requirements derived from:

- `Tables-101-Guide(1).docx` — Tables 101 visual guide
- `chart101-eng.pdf` — Charts 101 visual guide

The validator produces findings with:

- rule ID;
- severity;
- worksheet and location;
- English and French title/description;
- reviewer decision and audit trail support.

**Important:** The LLM never changes the deterministic findings. It can add translations and per-finding fix suggestions only.

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
84 passed
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

### 2.4 Choose the operating mode

The sidebar contains **Enable LLM assistance**.

- **Offline demonstration:** uncheck it. This requires no LLM gateway and is the safest first demo.
- **LLM-assisted demonstration:** check it. The sidebar should show `LLM-Assisted` and `r720-cascade2` when the local gateway is available.

If the local gateway is unavailable, the application should fall back to offline behavior and display a warning. The deterministic validation still works.

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

A passing workbook must not show a false warning merely because it contains a source line, notes, or approved symbols.

### 5.2 Deliberately failing workbooks

| File | Expected result | Main findings to point out |
|---|---:|---|
| `t101_fail_all.xlsx` | **11 findings**; `NOT_COMPLIANT` | Wrong sheet naming, gridlines off, formulas, empty cells, missing symbols, missing unit row, missing source, leading-space indentation, and related table failures. |
| `c101_fail_all.xlsx` | **5 findings**; `NOT_COMPLIANT` | More than six series, invalid chart dimensions, missing source, and missing standard symbols. |

The deliberately failing workbooks are synthetic teaching fixtures, not published StatCan products. Do not describe them as official source material.

### 5.3 Mixed and edge-case workbooks

These are useful if the client wants to see realistic variation rather than a perfect/failing binary demo.

| File | Expected result | Purpose |
|---|---|---|
| `mixed_realistic_cpi.xlsx` | Findings expected | Mixed CPI-style table/chart content. Demonstrates review of a realistic mixed workbook. |
| `mixed_realistic_lfs.xlsx` | Findings expected | Mixed Labour Force Survey-style content. Demonstrates a realistic revision candidate. |
| `bilingual_gdp.xlsx` | Findings expected | English/French GDP-style sheets. Demonstrates language selection and bilingual output. |
| `edge_cases.xlsx` | Findings expected; no crash | Empty, header-only, single-cell, and minimal-sheet cases. Demonstrates resilience to incomplete workbooks. |
| `t101_fail_specific.xlsx` | Targeted findings | Individual table-rule examples. Use when the client asks to isolate one rule. |

For these files, the exact finding count is not the primary demonstration assertion because they intentionally combine several scenarios. Point to the specific finding and explain that the operator can review, record a decision, replace the workbook, and revalidate.

## 6. Recommended client demonstration sequence

### Demonstration A — Clean pass, offline

1. Disable **Enable LLM assistance**.
2. Create/open a project.
3. Upload `t101_perfect_en.xlsx`.
4. Select English and validate.
5. Show `COMPLIANT` and zero findings.
6. Upload `t101_fail_all.xlsx` as a replacement revision.
7. Show that the same deterministic engine identifies 11 findings.
8. Expand one finding and show its severity, rule ID, sheet, location, and bilingual text.

**Expected message:** Offline mode is fully useful; it does not require an LLM to perform the compliance checks.

### Demonstration B — Charts

1. Upload `c101_perfect.xlsx`.
2. Show zero findings.
3. Replace it with `c101_fail_all.xlsx`.
4. Show five findings, especially the series-count, size, source, and symbol checks.

### Demonstration C — Local LLM assistance

1. Enable **Enable LLM assistance**.
2. Confirm the sidebar shows `LLM-Assisted` and `r720-cascade2`.
3. Validate `t101_fail_all.xlsx`.
4. Expand a finding.
5. Show the suggestion panel if Cascade 2 returns a suggestion.
6. Explain that suggestions are per-finding and require explicit reviewer action.
7. Reject a suggestion to demonstrate that no workbook change is made.
8. If a suggestion is accepted, revalidate and show the resulting revision/history.

If no suggestion is returned within the configured timeout, continue the demo using the deterministic findings. This is not a validation failure: LLM suggestions are an optional enhancement.

### Demonstration D — Bilingual workflow

1. Select French as the UI language, or upload `t101_perfect_fr.xlsx` with language `fr`.
2. Show the French titles and descriptions.
3. Download both the English and French reports.
4. Explain that offline mode uses clearly marked passthrough translation, while LLM mode can provide machine translation through Cascade 2.

## 7. What counts as a successful demo

The demo is successful when the operator can show all of the following:

- the app starts and is reachable in a browser;
- a compliant table returns zero findings;
- a compliant chart returns zero findings;
- a deliberately failing table returns 11 findings;
- a deliberately failing chart returns five findings;
- offline mode works with the LLM disabled;
- local LLM mode identifies the Cascade 2 gateway when it is available;
- findings remain the same when switching between offline and LLM-assisted modes;
- findings include bilingual text and locations;
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

### The sidebar shows offline while LLM assistance is enabled

This means the local gateway is unavailable or the model is not listed. Continue with the offline demo. The rule engine does not depend on the gateway.

The technical check is:

```bash
curl http://192.168.2.170:4000/v1/models
```

The response should include `r720-cascade2`.

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

Expected result: **84 passed**.
