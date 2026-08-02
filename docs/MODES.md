# StatCan Tables/Charts Validator v2.0 — Dual-Flavour Architecture

## Overview

The validator runs in two distinct modes, controlled by a single flag.
Both modes produce the **identical set of findings** from the rule engine;
the LLM only adds value on top (suggestions, translations).

## Mode Comparison

| Feature | Offline Mode | LLM-Assisted Mode |
|---------|-------------|-------------------|
| Rule checking | ✅ Full | ✅ Full |
| Bilingual reports | ✅ (Passthrough markers) | ✅ (LLM translated) |
| Fix suggestions | ❌ | ✅ (Cascade 2 local) |
| Cloud escalation | ❌ | ✅ (when needed) |
| Network required | ❌ No | ✅ LiteLLM proxy |
| Start time | < 1s | ~2s (health check) |
| Hardware needed | Any | M40 GPU (Cascade 2) |

## Mode Selection

The mode is selected via:
1. **Environment variable**: `USE_LLM=true` or `USE_LLM=false` (default: `true`)
2. **Streamlit toggle**: Sidebar checkbox "Enable LLM assistance"
3. **Auto-degradation**: If LLM gateway health check fails, drops to offline automatically

## Health Check System

The ModeManager runs a health probe on startup:
- Checks LiteLLM proxy (`http://192.168.2.170:4000/health`)
- Verifies Cascade 2 model is loaded (`GET /v1/models`)
- Returns: `healthy`, `degraded`, or `offline`

If the gateway is unreachable or Cascade 2 is not loaded, the system:
1. Shows a yellow warning banner in the UI
2. Falls back to offline mode for rule checking
3. Still allows project management and report generation

## Cloud Escalation

When in LLM-Assisted mode, the fix suggester can escalate to cloud models:
- **Trigger**: Confidence score < 0.5 on the local Cascade 2 suggestion
- **Cloud model**: `cloud-*-free` aliases (OpenRouter free-tier)
- **Config**: `CLOUD_ESCALATION_MODEL` env var
- **User visible**: Banner shows "Escalating to cloud model..."
- **Cost guard**: Limited to 3 escalations per session (configurable via `MAX_CLOUD_ESCALATIONS`)

## Translation

| Scenario | EN→FR Translation |
|----------|-------------------|
| Offline mode | `[FR translation unavailable]` + original text (clearly marked) |
| LLM mode | Translated by Cascade 2 via LiteLLM |
| LLM mode + fallback | Cascade 2 failure → `[LLM translation failed]` + Passthrough marker |

## File Structure

```
core/
├── mode_manager.py       # ModeManager — health checks, mode state, escalation
├── fix_suggester.py      # FixSuggester — per-finding LLM suggestions
├── excel_inspector.py    # (unchanged — rule engine is mode-independent)
└── llm_translator.py     # Existing LLM-backed Translator (via LiteLLM)

app/
├── main.py               # Updated with mode toggle + suggestion panel
└── services.py           # Updated with ModeManager + FixSuggester wiring
```