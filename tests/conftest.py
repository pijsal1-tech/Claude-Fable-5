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

# ── TSK-CEV-111 (CEV-F-003): fixture `.env` is GENERATED at test time ──
# History: the stored fixture file was deleted twice by the owner-side
# Auto-Uploader cleanup (ba2d9f0, 37a371f) despite the explicit
# .gitignore negation, forcing 36 manual restores. The content below is
# the verbatim historical body (a9f52b5) — FAKE credentials, documented
# NOT real secrets, required by R-204 SafeReader redaction tests.
SAMPLE_ENV_BODY = (
    "# FAKE credentials — fixture for R-204 SafeReader tests."
    " NOT real secrets.\n"
    "API_KEY=sk-FAKE-1234567890abcdefFAKEFAKE\n"
    "DATABASE_URL=postgres://fake_user:fake_pass@localhost:5432/fake_db\n"
    "SECRET_TOKEN=ghp_FAKEFAKEFAKEFAKEFAKEFAKEFAKE0000\n"
)


def write_sample_env(project_dir):
    """Materialize the FAKE `.env` inside a tmp copy of sample_project.

    Shared by the conftest fixture and the golden capture/replay
    harnesses so all environments stay byte-identical (TSK-CEV-111
    documented limit: single source of truth, no drift).
    """
    (project_dir / ".env").write_text(SAMPLE_ENV_BODY, encoding="utf-8")


@pytest.fixture
def sample_project(tmp_path):
    """Isolated copy of the fixture project; each test gets its own tmp copy."""
    src = FIXTURES_DIR / "sample_project"
    dst = tmp_path / "sample_project"
    shutil.copytree(src, dst)
    write_sample_env(dst)
    return dst


@pytest.fixture
def fake_provider():
    """Fresh FakeProvider per test."""
    from tests.fakes.fake_provider import FakeProvider
    return FakeProvider()
