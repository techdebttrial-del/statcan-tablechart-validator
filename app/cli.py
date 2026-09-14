"""Console entry point for the packaged StatCan Tables/Charts Validator.

Installing the distribution (``pip install .``) exposes a ``tvc`` command that
launches the Streamlit application. Works from a source checkout or an installed
wheel; resolves the app/main.py path relative to this module so it does not
depend on the current working directory.
"""
from __future__ import annotations

import os
import sys


def _app_entry() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "main.py")


def main(argv: list = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    # Insert app/package root on sys.path first (parity with running the
    # checkout directly) so core.* imports resolve regardless of launch cwd.
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    if root not in sys.path:
        sys.path.insert(0, root)

    import streamlit.web.cli as stcli

    # Positional launch: `tvc [--port N]` → streamlit run app/main.py.
    entry = _app_entry()
    streamlit_args = ["run", entry]
    # Accept a single optional numeric port or allow passthrough of extra flags.
    if args and args[0].lstrip("-").isdigit():
        streamlit_args += ["--server.port", args.pop(0)]
    streamlit_args += args
    rc = stcli.main(prog_name="tvc", args=streamlit_args)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())