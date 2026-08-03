# -*- coding: utf-8 -*-
"""TSK-CEV-117 (CEV-F-018): تطبيع اسم الملف قبل مطابقة قوائم حجب الأسرار.

الخلفية (جولة G7 Red Team): `is_secret_file` كانت تطابق
`path.name.lower()` **حرفيًا**، فأي لاحقة لا تغيّر الملف الذي يفتحه
Win32 فعليًا كانت تُمرِّر الاسم كـ«غير سري»:
  - مسافة/تاب لاحق: `.env `  (NTFS يقلّم اللواحق ⇒ نفس الملف)
  - نقاط لاحقة مع مسافات متناوبة: `.env . . `
  - محارف خفية: `.env<ZWSP>` / `.env<BOM>` (لا يراها str.strip)
  - NTFS ADS: `.env::$DATA` / `.env:$DATA` (نفس تيار البيانات)
  - كسر مجموعة الامتدادات: `cert.pem ` كان `path.suffix == '.pem '`

**حدّ الخطورة الموثَّق (CEV-R3 — لا مبالغة)**: على POSIX الاسم
`'.env '` ملفٌ *مختلف* عن `'.env'`، فالثغرة هناك **ليست** قراءةً
مباشرة للسر الحقيقي بل **إفلات عضو من عائلة قائمة الحجب** من الحجب
(ملف أُنشئ بذلك الاسم — مثل مستودع مُعَدّ أو مخرَج أداة). على Win32
(المنصة الأولى للمشروع — TSK-727) اللواحق تُقلَّم على مستوى النظام
فيصير **نفس** الملف ⇒ قراءة السر الحقيقي. الاختبارات أدناه تثبّت
السلوك المستقل عن المنصة: قرار الحجب يجب أن يكون واحدًا في الحالتين.

المصفوفة (فئة بفئة، كما يقتضي أمر المالك):
1. فرع `.env` التام + استثناء `.env.example` (يجب أن يبقى مسموحًا)
2. `SECRETS_DENYLIST_NAMES` (مطابقة تامة)
3. `SECRETS_DENYLIST_EXTENSIONS` (مشتقة من الاسم المطبَّع)
4. `SECRETS_DENYLIST_DIRS` (مقاطع المسار)
5. عدم الانكسار: أسماء شرعية تبقى مسموحة (صفر إيجابيات زائفة)
6. البوابة الشاملة `resolve_workspace_path` ترفض فعليًا
7. خصائص التطبيع نفسها (idempotence + لا يُرخّي حجبًا قائمًا)
"""
from __future__ import annotations

import pathlib

import pytest

from chain.path_policy import (
    SECRETS_DENYLIST_EXTENSIONS,
    SECRETS_DENYLIST_NAMES,
    is_secret_file,
    normalize_secret_name,
    resolve_workspace_path,
)

# ── لواحق التجاوز التي يجب ألا تُنجي اسمًا سريًا ──────────────────
EVASIONS = [
    "",            # الأساس (بلا لاحقة)
    " ",           # مسافة لاحقة
    "  ",          # مسافتان
    "\t",          # تاب
    ".",           # نقطة لاحقة
    "..",          # نقطتان
    " . . ",       # نقاط ومسافات متناوبة (Win32 يقلّمها كلها)
    "\u00a0",      # NBSP (str.strip يراها بيضاء)
    "\u3000",      # IDEOGRAPHIC SPACE
    "\u200b",      # ZWSP (str.strip لا يراها ⇒ يحتاج إزالة صريحة)
    "\ufeff",      # BOM
    "\u2060",      # WORD JOINER
    "::$DATA",     # NTFS ADS الصريح
    ":stream",     # NTFS ADS مسمّى
]


def _ids(prefix, items):
    return [f"{prefix}:{it!r}" for it in items]


# ═══ الفئة 1 — فرع `.env` ═══════════════════════════════════════
@pytest.mark.parametrize("evasion", EVASIONS, ids=_ids("ev", EVASIONS))
def test_env_exact_blocked_under_every_evasion(evasion):
    """`.env` يبقى محجوبًا مهما أُلحق به من محارف تجاوز."""
    assert is_secret_file(pathlib.Path(f".env{evasion}")) is True


@pytest.mark.parametrize("evasion", EVASIONS, ids=_ids("ev", EVASIONS))
def test_env_dotted_family_blocked(evasion):
    """`.env.local` وعائلته (`startswith`) تبقى محجوبة كذلك."""
    assert is_secret_file(pathlib.Path(f".env.local{evasion}")) is True


def test_env_case_insensitive_with_evasion():
    assert is_secret_file(pathlib.Path(".ENV ")) is True
    assert is_secret_file(pathlib.Path(".Env\u200b")) is True


@pytest.mark.parametrize("name", [
    ".env.example",
    ".env.example ",       # التطبيع لا يجوز أن يحوّل المسموح إلى محجوب
    ".ENV.EXAMPLE",
    ".env.example\u200b",
])
def test_env_example_stays_allowed(name):
    """استثناء `.env.example` محفوظ — التطبيع يُشدِّد ولا يُوسّع خطأً."""
    assert is_secret_file(pathlib.Path(name)) is False


# ═══ الفئة 2 — SECRETS_DENYLIST_NAMES ═══════════════════════════
@pytest.mark.parametrize("secret", sorted(SECRETS_DENYLIST_NAMES))
@pytest.mark.parametrize("evasion", EVASIONS, ids=_ids("ev", EVASIONS))
def test_denylist_names_blocked_under_every_evasion(secret, evasion):
    """كل اسم في قائمة الأسماء محجوب تحت كل لاحقة تجاوز."""
    assert is_secret_file(pathlib.Path(f"{secret}{evasion}")) is True


def test_denylist_names_case_and_dir_combo():
    assert is_secret_file(pathlib.Path("ID_RSA ")) is True
    assert is_secret_file(pathlib.Path("sub/dir/id_ed25519.")) is True


# ═══ الفئة 3 — SECRETS_DENYLIST_EXTENSIONS ══════════════════════
@pytest.mark.parametrize("ext", sorted(SECRETS_DENYLIST_EXTENSIONS))
@pytest.mark.parametrize("evasion", EVASIONS, ids=_ids("ev", EVASIONS))
def test_denylist_extensions_blocked_under_every_evasion(ext, evasion):
    """`cert.pem ` كان يفلت لأن path.suffix احتفظ بالمسافة."""
    assert is_secret_file(pathlib.Path(f"cert{ext}{evasion}")) is True


def test_extension_uppercase_with_evasion():
    assert is_secret_file(pathlib.Path("my.KEY ")) is True


def test_bare_extension_word_is_not_secret():
    """اسم بلا نقطة يساوي امتدادًا نصًّا ليس سرًّا (`pem` وحده)."""
    for name in ("pem", "key", "asc", "p12"):
        assert is_secret_file(pathlib.Path(name)) is False


# ═══ الفئة 4 — SECRETS_DENYLIST_DIRS ════════════════════════════
@pytest.mark.parametrize("d", [".ssh", ".aws", ".git", ".gcloud", ".kube"])
@pytest.mark.parametrize("evasion", ["", " ", ".", "\u200b"])
def test_denylist_dirs_blocked_under_evasion(d, evasion):
    """مقاطع المسار تُطبَّع أيضًا: `.ssh /known_hosts` محجوب."""
    assert is_secret_file(pathlib.Path(f"{d}{evasion}/known_hosts")) is True


# ═══ الفئة 5 — صفر إيجابيات زائفة (عدم انكسار) ══════════════════
@pytest.mark.parametrize("name", [
    "main.py", "README.md", "notes.txt", "certificate.md",
    "env", "environment.yml", "passwords.md", "my.env.example",
    "keys.txt.bak.md", "package.json", "test_key_utils.py",
])
def test_legitimate_names_remain_allowed(name):
    assert is_secret_file(pathlib.Path(name)) is False


# ═══ الفئة 6 — البوابة الشاملة ترفض فعليًا ══════════════════════
@pytest.mark.parametrize("requested", [
    ".env ", ".env.", ".env . . ", ".env\u200b", ".env::$DATA",
    "id_rsa ", "cert.pem ", ".ssh /id_rsa",
])
def test_resolve_workspace_path_rejects_evasions(tmp_path, requested):
    """التكامل: الرفض يحدث عند بوابة المسارات لا في الدالة معزولة."""
    (tmp_path / ".env").write_text("API_KEY=secret\n", encoding="utf-8")
    with pytest.raises(PermissionError, match="blocked secret patterns"):
        resolve_workspace_path(tmp_path, requested)


def test_resolve_workspace_path_still_allows_normal_file(tmp_path):
    """المسار الشائع بلا تغيير (لا انحدار في السلوك السليم)."""
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    out = resolve_workspace_path(tmp_path, "app.py", must_exist=True)
    assert out.name == "app.py"


def test_resolve_workspace_path_still_allows_env_example(tmp_path):
    (tmp_path / ".env.example").write_text("API_KEY=\n", encoding="utf-8")
    out = resolve_workspace_path(tmp_path, ".env.example", must_exist=True)
    assert out.name == ".env.example"


# ═══ الفئة 7 — خصائص التطبيع ════════════════════════════════════
@pytest.mark.parametrize("raw,expected", [
    (".env ", ".env"),
    (".env . . ", ".env"),
    (".env\u200b", ".env"),
    (".env::$DATA", ".env"),
    ("cert.pem ", "cert.pem"),
    ("ID_RSA", "id_rsa"),
    (".env.example", ".env.example"),
    ("main.py", "main.py"),
])
def test_normalize_secret_name_cases(raw, expected):
    assert normalize_secret_name(raw) == expected


@pytest.mark.parametrize("raw", [
    ".env ", ".env . . ", "cert.pem ", ".env::$DATA", "main.py", "",
])
def test_normalize_is_idempotent(raw):
    """التطبيع مستقر: تطبيقه مرتين = مرة واحدة (لا حلقة لا نهائية)."""
    once = normalize_secret_name(raw)
    assert normalize_secret_name(once) == once


def test_normalization_never_unblocks_previously_blocked():
    """حارس اتجاه: التطبيع يُشدِّد الحجب ولا يُرخّيه.

    كل اسم كان محجوبًا قبل الإصلاح يجب أن يبقى محجوبًا بعده.
    """
    previously_blocked = [
        ".env", ".env.local", ".env.production",
        *sorted(SECRETS_DENYLIST_NAMES),
        "cert.pem", "a.key", "b.pkcs12", "c.pfx", "d.p12", "e.asc",
        ".ssh/id_rsa", ".aws/credentials", ".git/config",
    ]
    for name in previously_blocked:
        assert is_secret_file(pathlib.Path(name)) is True, name


def test_normalize_handles_empty_and_dot_only():
    """أسماء حدّية لا ترفع استثناءً ولا تُصنَّف سرًّا."""
    for name in ("", ".", "..", "   ", "..."):
        normalize_secret_name(name)          # لا استثناء
        is_secret_file(pathlib.Path(name))   # لا استثناء


# ═══ إثبات مستقل عن المنصة لعائلة الحجب على القرص ═══════════════
def test_on_disk_evasion_family_is_blocked(tmp_path):
    """POSIX: `'.env '` ملف مختلف موجود فعلًا — القرار يجب أن يحجبه.

    هذا هو جوهر CEV-F-018 بحدّه الصحيح: عضو من عائلة قائمة الحجب
    كان يفلت. على Win32 نفس الاسم = الملف الأصلي ⇒ الحجب يمنع
    قراءة السر الحقيقي.
    """
    real = tmp_path / ".env"
    real.write_text("API_KEY=real\n", encoding="utf-8")
    spaced = tmp_path / ".env "
    spaced.write_text("API_KEY=spaced\n", encoding="utf-8")

    for f in sorted(tmp_path.iterdir()):
        assert is_secret_file(f) is True, f.name
