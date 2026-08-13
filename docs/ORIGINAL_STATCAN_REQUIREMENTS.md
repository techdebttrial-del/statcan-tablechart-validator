# Governing StatCan requirements

This project is governed by the supplied original visual guides, preserved in
this environment as `Tables-101-Guide(1).docx` and `chart101-eng.pdf`.

## Tables 101

- Excel workbook; one table per worksheet; tabs named `tblXX`.
- Consistent, unique numbering; gridlines on; no formulas or colour.
- French numeric content uses English number formatting.
- Include units where possible; prefer full text such as “percent”.
- Row stub relates to the data section; no empty data cells.
- Use approved StatCan symbols and definitions; symbols are superscript in a
  separate column beside the data.
- Avoid row spanning; use Excel indentation rather than leading spaces.
- Each footer note, symbol definition, and footnote occupies its own row.

## Charts 101

- Charts are created in Excel, with chart data on the same worksheet.
- One chart/data table per worksheet unless part of a chart group.
- Remove unnecessary calculations; chart data has no empty cells and uses
  approved symbols where required.
- Width is 22.5–30 cm; height starts at 11 cm and increases as needed.
- Maximum six data series; no superscripts in chart titles.
- Units are not embedded in axis labels; gridlines and data labels are not
  used together; do not duplicate tick marks on one axis.
- Symbols, horizontal reference lines, confidence intervals, and superscripts
  require corresponding notes.
- Every chart has consistent unique numbering, notes, and a source.
- Maps/figures/images without a data table require descriptive text in a
  separate document; avoid multi-chart images where possible.

The validator reports deterministic checks where `openpyxl` can observe the
workbook and documents drawing-level limitations rather than inventing results.
