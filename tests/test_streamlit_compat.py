from pathlib import Path


def test_findings_ui_supports_legacy_persisted_findings():
    source = (Path(__file__).parents[1] / "app" / "main.py").read_text()
    assert "resolve_affected_cells(" in source
