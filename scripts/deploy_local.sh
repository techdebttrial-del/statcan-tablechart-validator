#!/usr/bin/env bash
# ============================================================================
# deploy_local.sh — One-command local deployment for non-technical operators.
# StatCan Tables & Charts Validator (deterministic — no LLM, no network needed
# beyond the initial package download).
#
# Usage:   bash scripts/deploy_local.sh [PORT]
# Default: PORT=8502
#
# What it does:
#   1. Checks prerequisites (python3.10+, git)
#   2. Creates an isolated Python virtual environment (.venv)
#   3. Installs the pinned dependencies from requirements.txt
#   4. Runs scripts/verify_deployment.sh (full test suite + health gates)
#   5. Prints the exact command to start the app
#
# Idempotent: safe to re-run any time (re-running refreshes deps and re-tests).
# ============================================================================
set -euo pipefail
PORT="${1:-8502}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

say()  { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  OK\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mFAIL\033[0m %s\n' "$*"; exit 1; }

say "Step 1/5 — Checking prerequisites"
command -v python3 >/dev/null 2>&1 || fail "python3 not found. Install Python 3.10+ and re-run."
PYV=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
python3 - "$PYV" <<'PYEOF' || fail "Python $PYV found, but 3.10+ is required."
import sys
v = sys.argv[1]
maj, minr = (int(x) for x in v.split("."))
sys.exit(0 if (maj, minr) >= (3, 10) else 1)
PYEOF
ok "python3 $PYV"
command -v git >/dev/null 2>&1 && ok "git $(git --version | awk '{print $3}')" || fail "git not found. Install git and re-run."

say "Step 2/5 — Creating isolated Python environment (.venv)"
if [ ! -d .venv ]; then
  python3 -m venv .venv || fail "Could not create .venv (on Debian/Ubuntu: sudo apt install python3-venv)"
fi
ok ".venv ready"

say "Step 3/5 — Installing dependencies (this can take a minute)"
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt
ok "dependencies installed"

say "Step 4/5 — Verifying the deployment (full test suite + gates)"
bash scripts/verify_deployment.sh

say "Step 5/5 — Done. To start the application:"
cat <<EOF

    cd "$HERE"
    .venv/bin/streamlit run app/main.py --server.port $PORT

Then open:  http://localhost:$PORT

(French UI: use the language selector in the app sidebar.)
Full operator instructions: docs/OPERATOR_GUIDE_EN.md / docs/OPERATOR_GUIDE_FR.md
If anything failed above: docs/DEPLOYMENT_GUIDE_EN.md § Troubleshooting.
EOF
