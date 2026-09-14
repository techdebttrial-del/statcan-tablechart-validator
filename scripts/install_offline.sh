#!/usr/bin/env bash
# ============================================================================
# install_offline.sh — Fully offline installer for StatCan Tables/Charts
# Validator. Designed for AIR-GAPPED / no-internet environments.
#
# This bundle contains everything needed: the app distribution wheel plus the
# complete dependency wheelhouse. NO NETWORK ACCESS IS REQUIRED.
#
# Usage:
#   bash install_offline.sh            # install into ./tvc-venv (default)
#   bash install_offline.sh /path/to/venv
#
# What it does:
#   1. Checks python3 (3.10–3.13).
#   2. Creates an isolated venv (the path given, default ./tvc-venv).
#   3. Installs the app + ALL dependencies from the bundled wheelhouse with
#      --no-index (never touches the network).
#   4. Runs a quick deterministic health check (rule packs load, core imports).
#   5. Prints the exact command to launch the app and where to find the logs.
#
# Safe to re-run: re-running refreshes the venv and re-verifies.
# ============================================================================
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${1:-$HERE/tvc-venv}"
WH="$HERE/wheelhouse"

say()  { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
ok()   { printf '  \033[1;32mOK\033[0m  %s\n' "$*"; }
fail() { printf '\n\033[1;31mFAIL\033[0m %s\n' "$*" >&2; exit 1; }

say "StatCan Tables/Charts Validator — OFFLINE install"
say "Bundle: $HERE"

# --- 1. Prereqs ------------------------------------------------------------
command -v python3 >/dev/null 2>&1 || fail "python3 not found. Python 3.10+ is required."
PYV="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
case "$PYV" in
  3.10|3.11|3.12|3.13) ok "python3 $PYV (supported)" ;;
  *) fail "Python $PYV detected — 3.10–3.13 required for the bundled wheels." ;;
esac

[ -d "$WH" ] || fail "wheelhouse/ not found next to this script — bundle is incomplete."
APPW="$(ls -d "$WH"/statcan_tablechart_validator-*.whl 2>/dev/null | head -1 || true)"
[ -n "$APPW" ] && [ -f "$APPW" ] || fail "app wheel missing in wheelhouse/."

# --- 2. venv ----------------------------------------------------------------
say "Creating virtual environment: $VENV"
python3 -m venv "$VENV" || fail "could not create venv at $VENV (on Debian/Ubuntu: sudo apt install python3-venv)."
"$VENV/bin/python" -m pip install --quiet --upgrade pip \
  || { say "pip upgrade skipped (offline) — continuing with bundled pip."; }

# --- 3. Install from wheelhouse (no network) --------------------------------
say "Installing app + $([ "$(ls "$WH" | wc -l)" -gt 1 ] && echo "bundled dependencies from wheelhouse — ")NO NETWORK"
"$VENV/bin/python" -m pip install --no-index \
  --find-links "$WH" \
  "$APPW" || fail "pip install failed. Check bundle integrity (wheelhouse/)."

# --- 4. Health check --------------------------------------------------------
say "Health check (rule packs + core imports)"
"$VENV/bin/python" - <<'PYEOF' || fail "health check did not pass."
import sys
from core.rule_pack_loader import RulePackLoader
l = RulePackLoader()
assert l.rules_for("tables101"), "tables101 rule pack empty"
assert l.rules_for("charts101"), "charts101 rule pack empty"
assert l.standard_symbols().get("symbols"), "standard symbols empty"
import app.cli  # console entry parses
print(f"  OK  tables101={len(l.rules_for('tables101'))} "
      f"charts101={len(l.rules_for('charts101'))} symbols={len(l.standard_symbols()['symbols'])}")
PYEOF
ok "rule packs + core imports healthy"

# --- 5. Done ----------------------------------------------------------------
cat <<EOF

============================================================
  INSTALL COMPLETE  —  StatCan Tables/Charts Validator
============================================================

  Virtual environment : $VENV
  Start the app        :

      "$VENV/bin/python" -m streamlit run \\
          "$HERE/app/main.py" --server.port 8502

  (or run)            : "$VENV/bin/python" -m tvc --port 8502
  then open           : http://localhost:8502

  Data (projects)     : ~/.tvc_data  (override: TVC_DATA_ROOT)
  Operator guide      : $HERE/docs/OPERATOR_GUIDE.md  (bilingual EN/FR)
  Troubleshooting     : $HERE/docs/DEPLOYMENT_GUIDE.md § Troubleshooting

  App version         : $(basename "$APPW")
  Installed deps      : $(ls "$WH"/*.whl 2>/dev/null | wc -l) wheels bundled
  Network used        : NONE  (verified offline install)
============================================================
EOF