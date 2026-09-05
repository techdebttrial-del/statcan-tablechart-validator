"""Documentation consistency tests (R2-T6 / spec RH9).

The docs must tell the truth: stated test counts equal the actual collected
count, run commands reference the canonical port, and the client deployment
section exists.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
DOC_FILES = [
    ROOT / "docs" / "DEMO_OPERATOR_GUIDE.md",
    ROOT / "README.md",
    ROOT / "docs" / "README.md",
    ROOT / ".hermes.md",
]


def _collected_test_count() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120,
    )
    match = re.search(r"(\d+)\s+tests? collected", result.stdout)
    if match:
        return int(match.group(1))
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    return len([ln for ln in lines if "::" in ln or ln.startswith("<")])


def test_documented_test_counts_match_reality():
    actual = _collected_test_count()
    assert actual >= 150, f"expected a full suite, collected only {actual}"
    for doc in DOC_FILES:
        if not doc.exists():
            continue
        text = doc.read_text()
        for match in re.finditer(r"(\d+)\s+passed", text):
            claimed = int(match.group(1))
            assert claimed == actual, (
                f"{doc.name} claims '{claimed} passed' but {actual} tests "
                f"are collected — update the doc"
            )


def test_docs_reference_canonical_port():
    for doc in [ROOT / "docs" / "DEMO_OPERATOR_GUIDE.md", ROOT / ".hermes.md"]:
        text = doc.read_text()
        assert "8502" in text, f"{doc.name} must reference the canonical port 8502"
        assert ":8503" not in text, f"{doc.name} still references stale port 8503"


def test_operator_guide_has_client_deployment_section():
    guide = (ROOT / "docs" / "DEMO_OPERATOR_GUIDE.md").read_text()
    assert re.search(r"^#+\s*(\d+\.?\s*)?Client deployment", guide, re.MULTILINE), (
        "DEMO_OPERATOR_GUIDE.md needs a 'Client deployment' section"
    )
    # Deployment must cover the essentials
    for needle in ["git clone", "python -m venv", "pip install", "streamlit run",
                   "TVC_DATA_ROOT"]:
        assert needle in guide, f"deployment section missing: {needle}"


def test_fixture_counts_doc_matches_engine():
    """Every 'N findings' claim in FIXTURES.md matches the real engine run."""
    doc = ROOT / "docs" / "FIXTURES.md"
    if not doc.exists():
        return
    sys.path.insert(0, str(ROOT))
    from core.excel_inspector import ExcelInspector

    text = doc.read_text()
    insp = ExcelInspector()
    for match in re.finditer(r"`([a-z0-9_]+\.xlsx)`[^`]*?(\d+)\s+findings", text):
        fixture_name, claimed = match.group(1), int(match.group(2))
        fixture_path = ROOT / "tests" / "fixtures" / "test_cases" / fixture_name
        if not fixture_path.exists():
            continue
        actual = len(insp.inspect_workbook(str(fixture_path)))
        assert actual == claimed, (
            f"FIXTURES.md says {fixture_name} has {claimed} findings; "
            f"engine reports {actual}"
        )
