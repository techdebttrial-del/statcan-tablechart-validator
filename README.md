# StatCan Tables/Charts Validator (MVP)

See `docs/README.md` for full documentation, `docs/ARCHITECTURE.md` for the
system design, `docs/INTEGRATION_WITH_ACCELERATOR.md` for the path to merge
this into the broader StatCan ESR Accelerator, and `docs/DECISIONS_LOG.md`
for the scoping rationale behind every design choice in this MVP.

Quick start:
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py --server.port 8502
```
