# Auto-Fix Suggestion Workflow

When the validator is in LLM-Assisted mode, each finding can have
auto-generated fix suggestions from Cascade 2 (or escalated to cloud models).

## Workflow

```
Finding detected → LLM proposes 1-3 fixes → Reviewer reviews → Accept/Reject
                                                          ↓
                                              (Accept-Modified → edit + accept)
                                                          ↓
                                              Fix applied to workbook
                                                          ↓
                                              Re-validation
```

## Fix Suggestion Format

Each suggestion includes:
- **finding_id**: Links to the original finding
- **rule_id**: Which rule was violated
- **description**: What needs to change
- **proposed_change**: Specific edit to the workbook cell/property
- **confidence**: 0.0–1.0 (how confident the LLM is in this fix)
- **applies_to**: Cell reference or sheet property
- **validation_status**: `pending`, `validated`, `invalid`

## Review Actions

| Action | Behaviour |
|--------|-----------|
| **Accept** | Fix is immediately applied, workbook re-validated |
| **Accept Modified** | Opens an inline text editor, user edits the proposed fix, then applies |
| **Reject** | Fix is discarded, user can provide reason |
| **Escalate** | Manually force cloud model to suggest an alternative |

## Confidence Thresholds

| Confidence | Behaviour |
|------------|-----------|
| ≥ 0.8 | Auto-highlight as "recommended" (green) |
| 0.5 – 0.79 | Show normally (yellow) |
| < 0.5 | Auto-escalate to cloud model before showing |

## Security / Integrity

1. All suggestions are **never auto-applied** — human must approve
2. Before applying, `validate_suggestion()` verifies the workbook can be
   opened by openpyxl after the edit
3. Original workbook is preserved as a backup in git history
4. Each applied fix generates an amendment in the audit trail

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `CONFIDENCE_THRESHOLD` | 0.5 | Minimum confidence to show suggestion |
| `MAX_SUGGESTIONS_PER_FINDING` | 3 | Max suggestions per finding |
| `MAX_CLOUD_ESCALATIONS` | 3 | Cloud escalation budget per session |
| `CLOUD_ESCALATION_MODEL` | `cloud-*-free` | OpenRouter model for escalation |