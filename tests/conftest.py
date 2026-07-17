"""Shared pytest fixtures (T-001).

Ensures the repository root is importable so tests can do
`import server`, `import chain.models`, etc. without installing a package.
"""
import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ── T-002 fixtures ──────────────────────────────────────
import shutil
import pytest

FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


@pytest.fixture
def sample_project(tmp_path):
    """Isolated copy of the fixture project; each test gets its own tmp copy."""
    src = FIXTURES_DIR / "sample_project"
    dst = tmp_path / "sample_project"
    shutil.copytree(src, dst)
    return dst


@pytest.fixture
def fake_provider():
    """Fresh FakeProvider per test."""
    from tests.fakes.fake_provider import FakeProvider
    return FakeProvider()
