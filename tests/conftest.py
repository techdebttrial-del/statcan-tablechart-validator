"""
Shared pytest fixtures for the StatCan Table/Chart Validator test suite.

All tests import from `core.*`; the sys.path hack previously duplicated in
every test file is now handled centrally here via the `pythonpath` setting
in pyproject.toml plus the `project_root` fixture for any absolute-path needs.
"""
import os
import sys
import pytest

from core.repository_client import InMemoryRepositoryClient
from core.project_store import ProjectStore
from core.rule_pack_loader import RulePackLoader

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
SAMPLE_WORKBOOK = os.path.join(FIXTURES_DIR, "sample_workbook.xlsx")


@pytest.fixture
def project_root() -> str:
    """Absolute path to the repository root."""
    return PROJECT_ROOT


@pytest.fixture
def fixtures_dir() -> str:
    """Absolute path to tests/fixtures/."""
    return FIXTURES_DIR


@pytest.fixture
def config_dir() -> str:
    """Absolute path to the config/ directory."""
    return CONFIG_DIR


@pytest.fixture
def sample_workbook_path() -> str:
    """Path to the sample .xlsx fixture used by most integration tests."""
    assert os.path.isfile(SAMPLE_WORKBOOK), (
        f"Missing test fixture: {SAMPLE_WORKBOOK}"
    )
    return SAMPLE_WORKBOOK


# ---------------------------------------------------------------------------
# In-memory repository (no git dependency)
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_repo() -> InMemoryRepositoryClient:
    """Fresh InMemoryRepositoryClient for each test."""
    return InMemoryRepositoryClient()


# ---------------------------------------------------------------------------
# ProjectStore wired to in-memory repo
# ---------------------------------------------------------------------------

@pytest.fixture
def project_store(in_memory_repo: InMemoryRepositoryClient) -> ProjectStore:
    """ProjectStore backed by an in-memory repo (no disk, no git)."""
    return ProjectStore(repo=in_memory_repo)


# ---------------------------------------------------------------------------
# Rule-pack loader (reads actual YAML config files)
# ---------------------------------------------------------------------------

@pytest.fixture
def rule_pack_loader(config_dir: str) -> RulePackLoader:
    """RulePackLoader seeded from the real config/ directory."""
    return RulePackLoader(config_dir)


# ---------------------------------------------------------------------------
# Convenience: a pre-populated project with one workbook revision
# ---------------------------------------------------------------------------

@pytest.fixture
def project_with_revision(project_store: ProjectStore, sample_workbook_path: str):
    """
    Returns (project, revision) — a ProjectState that already has one
    workbook revision with findings, backed by an in-memory repo.
    """
    project = project_store.create_project(
        label="Test Project",
        reviewer="Fixture Reviewer",
    )
    revision = project_store.add_workbook_revision(
        project,
        sample_workbook_path,
        original_filename="sample.xlsx",
        uploaded_by="Fixture Reviewer",
    )
    return project, revision