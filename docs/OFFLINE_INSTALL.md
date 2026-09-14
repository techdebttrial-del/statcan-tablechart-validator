# StatCan Tables & Charts Validator — Offline Installation (Air-Gapped)

This guide covers installing the validator on a machine with **no internet
access** (no GitHub, no PyPI). It complements `DEPLOYMENT_GUIDE.md`
(online install) and `OPERATOR_GUIDE.md` (daily use, bilingual EN/FR).

## What you need

A single **offline bundle** containing:

- `wheelhouse/` — the application wheel plus every dependency wheel
- `install_offline.sh` — the one-command, no-network installer
- the application source tree (`app/`, `core/`, `config/`, `docs/`, `tests/`)

Hand the whole bundle over on a `.zip`, USB stick, or internal file share.
**Keep the folder contents together** — do not move files around.

## Installation (operator-friendly)

1. Copy the bundle to the target machine.
2. Open a terminal and go to the folder:
   - Linux/macOS: `cd /path/to/folder`
   - Windows: `cd path\to\folder`
3. Run the installer:
   ```
   bash install_offline.sh
   ```
   It creates an isolated virtual environment (`tvc-venv`), installs the app
   **and all dependencies from the bundled wheels** (`--no-index`, so the
   network is never touched), runs a health check, and prints the launch command.

4. Start the app:
   ```
   bash tvc-venv/bin/streamlit run app/main.py --server.port 8502
   ```
   Open `http://localhost:8502` in a browser.

## Target environment

- Linux x86-64 (`manylinux2014`), Python **3.10–3.13**.
- Compiled dependencies (numpy, pandas, pyarrow, pillow, PyYAML) are bundled
  as `cp311` wheels (plus cp310/cp312/cp313 PyYAML). Pure-Python wheels apply
  to other Python versions; for a fully pinned wheelhouse of another column,
  regenerate with:
  ```
  pip download --only-binary=:all: --platform manylinux2014_x86_64 \
    --python-version <PY> -r requirements.txt -d wheelhouse/
  pip download --only-binary=:all: --python-version <PY> -r requirements.txt -d wheelhouse/
  ```
- Deterministic-only: no LLM, no external API, works fully air-gapped once installed.

## Verify

The installer runs a health check automatically. To run the full test suite:
```
bash tvc-venv/bin/python -m pytest tests/ -q   # expect: 172 passed
```

## Developer: refresh the bundle

From a machine with network access:
```
python -m build                                   # builds dist/*.whl + sdist
mkdir -p wheelhouse && cp dist/*.whl wheelhouse/
pip download --only-binary=:all: -r requirements.txt -d wheelhouse/   # full closure
# bundle the source tree + wheelhouse + install_offline.sh + this guide
```
The bundled wheel includes the console entry point `tvc` (`pip install .` on
an online machine exposes `tvc` → starts Streamlit).