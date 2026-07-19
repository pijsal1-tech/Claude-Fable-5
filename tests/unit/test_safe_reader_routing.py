# -*- coding: utf-8 -*-
"""T-026 (R-204): توجيه كل قراءات السياق عبر SafeReader.

معيار القبول: ملف ``.env`` (وأي ملف سري) **لا يمكن الوصول لقيمته** عبر
المسارات الثلاثة — mention وkeyword وstructure — والقيمة تُستبدل بـ stub
الحجب. الحدود مضمونة أيضًا بفحص grep في scripts/check.sh (ولها نسخة
pytest هنا حتى يلتقطها من يشغّل pytest وحده).
"""
from __future__ import annotations

import pathlib
import re

import pytest

from context.facade import gather_message_context
from context.safe_reader import REDACTION_STUB
from context.sources.mention import build_items
from context.engine import ProjectScan

# قيم سرية زائفة — fixtures فقط، ليست أسرارًا حقيقية
FAKE_AWS = "AKIAIOSFODNN7EXAMPLE"
FAKE_ASSIGN = "super-secret-value-1234567890"


@pytest.fixture()
def project(tmp_path: pathlib.Path) -> pathlib.Path:
    """مشروع فيه ملف عادي + ملفان سريان بقيم زائفة قابلة للرصد."""
    (tmp_path / "app.py").write_text(
        "def main():\n    return 42\n", encoding="utf-8")
    (tmp_path / ".env").write_text(
        f'SECRET_TOKEN="{FAKE_AWS}"\n', encoding="utf-8")
    # production-style: الاسم ليس ".env" لكن اللاحقة ".env" — كان يمر
    # عبر WEB_EXTENSIONS قبل توجيه SafeReader
    (tmp_path / "secrets.env").write_text(
        f"API_SECRET={FAKE_ASSIGN}\n", encoding="utf-8")
    return tmp_path


def _assert_no_secret(text: str) -> None:
    assert FAKE_AWS not in text
    assert FAKE_ASSIGN not in text


# ═════════════════ المسارات الثلاثة (معيار القبول) ═════════════════

class TestThreePathRedaction:
    """`.env` غير قابل للوصول عبر mention/keyword/structure."""

    def test_mention_path_returns_stub_never_value(self, project):
        # اسم كامل بامتداد → مسار الـ exact-match (MentionSource)
        ctx = gather_message_context(project, "اقرأ secrets.env وشوف المشكلة")
        assert "secrets.env" in ctx.mentioned_files
        assert REDACTION_STUB in ctx.user_text_with_files
        _assert_no_secret(ctx.user_text_with_files)

    def test_keyword_path_returns_stub_never_value(self, project):
        # جذع بلا امتداد → مسار الـ stem-match (KeywordSource)
        ctx = gather_message_context(project, "فيه مشكلة في secrets")
        assert "secrets.env" in ctx.mentioned_files
        assert REDACTION_STUB in ctx.user_text_with_files
        _assert_no_secret(ctx.user_text_with_files)

    def test_structure_path_never_lists_dotenv(self, project):
        # بنية المشروع (StructureSource → get_project_context)
        ctx = gather_message_context(project, "اشرح لي بنية المشروع")
        _assert_no_secret(ctx.project_context)
        # `.env` نفسه لا يُدرج إطلاقًا (is_secret_file في _walk)
        listed = [ln for ln in ctx.project_context.splitlines()
                  if ln.strip().startswith("- ")]
        assert not any(re.search(r"(^|/)\.env\b", ln) for ln in listed)

    def test_bare_dotenv_unreachable_via_mention_and_keyword(self, project):
        # `.env` ذاته: regex الاستخراج لا يلتقطه واللاحقة الفارغة
        # ليست في WEB_EXTENSIONS — لا يظهر ولا تتسرب قيمته
        ctx = gather_message_context(project, "عدل .env وشغل env من جديد")
        assert ".env" not in ctx.mentioned_files
        _assert_no_secret(ctx.user_text_with_files)


# ═════════════════ سلوك build_items الموجّه ═════════════════

class TestRoutedBuildItems:

    def test_normal_file_content_numbered_as_before(self, project):
        # regression: الملف العادي يصل بمحتواه المرقّم كما في legacy
        items = build_items(ProjectScan(project), ["app.py"], "mention")
        assert len(items) == 1
        assert items[0].content == "1: def main():\n2:     return 42"

    def test_secret_file_content_is_stub_not_numbered(self, project):
        items = build_items(ProjectScan(project), ["secrets.env"], "mention")
        assert items[0].content == REDACTION_STUB   # بلا ترقيم أسطر
        _assert_no_secret(items[0].content or "")

    def test_missing_file_still_silent_none(self, project):
        # huge-file/الملف الغائب quirk: content=None يُتخطى بصمت
        items = build_items(ProjectScan(project), ["ghost.py"], "mention")
        assert items[0].content is None

    def test_huge_file_quirk_preserved(self, project):
        # أكبر من سقف legacy (500KB) → content=None لا قراءة جزئية
        (project / "big_data.js").write_text(
            "x" * (500 * 1024 + 1), encoding="utf-8")
        items = build_items(ProjectScan(project), ["big_data.js"], "mention")
        assert items[0].content is None


# ═════════════════ حدود الـ CI grep (نسخة pytest) ═════════════════

class TestBoundaryGrep:
    """لا قراءة خام داخل context/ خارج safe_reader.py."""

    def test_no_raw_reads_in_context_package(self):
        repo = pathlib.Path(__file__).resolve().parents[2]
        pattern = re.compile(r"open\(|\.read_text\(|\.read_bytes\(")
        violations: list[str] = []
        for py in sorted((repo / "context").rglob("*.py")):
            if py.name == "safe_reader.py":
                continue
            for i, line in enumerate(
                    py.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line) and "reader.read_text(" not in line:
                    violations.append(f"{py.relative_to(repo)}:{i}: {line.strip()}")
        assert violations == []
