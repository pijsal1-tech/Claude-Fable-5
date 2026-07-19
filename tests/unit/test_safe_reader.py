# -*- coding: utf-8 -*-
"""اختبارات T-025: SafeReader + إزالة `.env` من _TEXT_EXTENSIONS (R-204).

- مصفوفة denylist (بند R-204: `.env`, `.env.local`, `id_rsa`, `*.pem`
  مقابل `.env.example`).
- وحدات شمّ الإنتروبيا (مفاتيح معروفة + إسناد عالي الإنتروبيا،
  والملفات العادية لا تتأثر).
- E2E الحجب: fixture فيه `.env` → البرومبت/الماسح لا يحملان القيمة أبدًا.
"""
import pathlib

import pytest

from context.safe_reader import (
    REDACTION_STUB,
    SafeReader,
    shannon_entropy,
    sniff_secret_content,
)
from chain.bridge import _TEXT_EXTENSIONS, scan_folder_for_chain

SECRET_VALUE = "AKIAIOSFODNN7EXAMPLE"          # نمط AWS معروف
ENV_BODY = f"API_SECRET=super-secret-value-123456\nAWS_KEY={SECRET_VALUE}\n"


@pytest.fixture()
def project(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "app.py").write_text("def main():\n    return 42\n",
                                     encoding="utf-8")
    (tmp_path / ".env").write_text(ENV_BODY, encoding="utf-8")
    (tmp_path / ".env.example").write_text("API_SECRET=\nAWS_KEY=\n",
                                           encoding="utf-8")
    return tmp_path


# ═══════════════════ denylist matrix (R-204) ═══════════════════

class TestDenylistMatrix:
    @pytest.mark.parametrize("name", [
        ".env", ".env.local", ".env.production",
        "id_rsa", "id_ed25519", "credentials",
        "server.pem", "private.key", "keys.txt",
        "production.env",           # امتداد *.env — كان يمر قبل T-025
    ])
    def test_blocked(self, tmp_path, name):
        reader = SafeReader(tmp_path)
        assert reader.is_denied(tmp_path / name) is True

    @pytest.mark.parametrize("name", [
        ".env.example",             # بند مخاطر R-204: مسموح صراحةً
        "app.py", "README.md", "config.yaml", "environment.md",
    ])
    def test_allowed(self, tmp_path, name):
        reader = SafeReader(tmp_path)
        assert reader.is_denied(tmp_path / name) is False

    def test_secret_dirs_blocked(self, tmp_path):
        reader = SafeReader(tmp_path)
        assert reader.is_denied(tmp_path / ".ssh" / "known_hosts") is True
        assert reader.is_denied(tmp_path / ".aws" / "config") is True

    def test_extra_denylist_extensible(self, tmp_path):
        reader = SafeReader(tmp_path, extra_deny_names=("secrets.yaml",),
                            extra_deny_extensions=(".vault",))
        assert reader.is_denied(tmp_path / "secrets.yaml") is True
        assert reader.is_denied(tmp_path / "prod.vault") is True
        # التوسعة لا تحجب العادي
        assert reader.is_denied(tmp_path / "app.py") is False


# ═══════════════════ redaction stub ═══════════════════

class TestRedaction:
    def test_env_read_returns_stub_never_value(self, project):
        reader = SafeReader(project)
        r = reader.read_text(".env")
        assert r.ok and r.redacted
        assert r.content == REDACTION_STUB
        assert r.reason == "denylist"
        assert SECRET_VALUE not in (r.content or "")

    def test_env_example_reads_normally(self, project):
        reader = SafeReader(project)
        r = reader.read_text(".env.example")
        assert r.ok and not r.redacted
        assert "API_SECRET=" in r.content

    def test_normal_file_unaffected(self, project):
        reader = SafeReader(project)
        r = reader.read_text("app.py")
        assert r.ok and not r.redacted
        assert r.content == "def main():\n    return 42\n"
        assert r.size > 0

    def test_denied_without_touching_disk(self, project):
        """الحجب يُحسم من المسار — حتى لو الملف غير موجود."""
        reader = SafeReader(project)
        r = reader.read_text("missing/.env.local")
        assert r.redacted and r.content == REDACTION_STUB

    def test_missing_file_reported(self, project):
        r = SafeReader(project).read_text("nope.py")
        assert not r.ok and r.reason == "not_found"
        assert r.prompt_text == ""

    def test_too_large_rejected_not_partial(self, project):
        (project / "big.txt").write_text("x" * 5000, encoding="utf-8")
        r = SafeReader(project, max_file_size=1000).read_text("big.txt")
        assert not r.ok and r.reason == "too_large"
        assert r.content is None       # لا قراءة جزئية

    def test_escape_outside_root_policy_error(self, project):
        r = SafeReader(project).read_text("../outside.txt")
        assert not r.ok and r.reason.startswith("policy:")


# ═══════════════════ entropy sniff units ═══════════════════

class TestEntropySniff:
    def test_shannon_entropy_bounds(self):
        assert shannon_entropy("") == 0.0
        assert shannon_entropy("aaaa") == 0.0
        assert shannon_entropy("ab") == 1.0
        # مفتاح base64 عشوائي → إنتروبيا عالية
        assert shannon_entropy("A7f9Kq2ZxL0mN8pR4sT6uVwB") > 3.5

    @pytest.mark.parametrize("text,expected", [
        ("-----BEGIN RSA PRIVATE KEY-----\nMIIE...", "private_key_block"),
        (f"aws_access_key_id = {SECRET_VALUE}", "aws_access_key"),
        ("token = ghp_Abc123Def456Ghi789Jkl012Mno345", "github_token"),
        ("OPENAI_API_KEY=sk-proj1234567890abcdefghij", "openai_key"),
        ("SLACK=xoxb-1234567890-abcdefghij", "slack_token"),
        ("key=AIzaSyA1234567890abcdefghijklmnopqrstu", "google_api_key"),
    ])
    def test_known_key_patterns(self, text, expected):
        assert sniff_secret_content(text) == expected

    def test_high_entropy_assignment_detected(self):
        text = 'DB_PASSWORD = "Xk9mP2vQ7rT4wY8zA3cF6hJ1nL5s"'
        assert sniff_secret_content(text) == "high_entropy_assignment"

    @pytest.mark.parametrize("text", [
        "def main():\n    return 42\n",                    # كود عادي
        "password = get_password_from_vault()",           # قيمة قصيرة/دالة
        "# api_key documentation notes about tokens",     # تعليق بلا إسناد
        "The token endpoint is documented in README.",    # نثر عادي
        'name = "abcabcabcabcabcabcabc"',                 # ليس اسمًا سريًا
    ])
    def test_normal_content_not_flagged(self, text):
        assert sniff_secret_content(text) is None

    def test_sniff_redacts_unlisted_file(self, project):
        """ملف باسم بريء يحمل مفتاحًا → stub عبر الشمّ."""
        (project / "notes.txt").write_text(
            f"my key: aws_access_key = {SECRET_VALUE}", encoding="utf-8")
        r = SafeReader(project).read_text("notes.txt")
        assert r.redacted and r.content == REDACTION_STUB
        assert r.reason == "sniff: aws_access_key"


# ═══════════════════ extension removal + scanner E2E ═══════════════════

class TestScannerBoundary:
    def test_env_removed_from_text_extensions(self):
        """البند الصريح: `.env` لم تعد امتدادًا مقروءًا."""
        assert ".env" not in _TEXT_EXTENSIONS

    def test_scan_folder_never_returns_env(self, project):
        files = scan_folder_for_chain(str(project))
        assert "app.py" in files                     # العادي غير متأثر
        assert ".env" not in files
        joined = "\n".join(files.values())
        assert SECRET_VALUE not in joined            # القيمة لا تصل أبدًا

    def test_scan_skips_secret_named_files_with_allowed_ext(self, tmp_path):
        """امتداد مسموح باسم سري (credentials.json مثلًا) → يُتخطى."""
        (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "server.pem").write_text("PEMDATA", encoding="utf-8")
        (tmp_path / "id_rsa").write_text("RSAKEY", encoding="utf-8")
        files = scan_folder_for_chain(str(tmp_path))
        assert "ok.py" in files
        assert "server.pem" not in files and "id_rsa" not in files
        assert "PEMDATA" not in "\n".join(files.values())

    def test_redaction_e2e_prompt_path(self, project):
        """معيار القبول: ذكر `.env` في مسار سياق → stub لا القيمة.

        نستخدم SafeReader كما ستستهلكه المسارات بعد التوصيل (T-026):
        النص المتجه للبرومبت هو prompt_text — يجب أن يكون stub.
        """
        reader = SafeReader(project)
        prompt_block = f"📄 .env:\n{reader.read_text('.env').prompt_text}"
        assert REDACTION_STUB in prompt_block
        assert SECRET_VALUE not in prompt_block
        assert "super-secret-value" not in prompt_block
