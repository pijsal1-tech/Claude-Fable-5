# -*- coding: utf-8 -*-
"""SafeReader (R-204 / T-025): بوابة القراءة الوحيدة للمحتوى المتجه للموديل.

## ملاحظة أمنية (security note)

المشكلة: `path_policy.is_secret_file` موجودة لكنها **سياسة اختيارية** —
مكتبة على المستدعي أن يتذكرها. `scan_folder_for_chain` كانت تضم `.env`
في `_TEXT_EXTENSIONS` وتقرأه داخل سياق السلسلة؛ مسارات قراءة أخرى تطبق
السياسة بشكل غير متسق. النتيجة: مفاتيح حية يمكن أن تُشحن لمزودي موديلات
طرف ثالث — عيب أمني، ليس مجرد smell.

الحل: `SafeReader` — **الحدود (boundary) لا المكتبة**: كل قراءة ملف
متجهة لبرومبت يجب أن تمر من هنا (التوصيل الكامل لكل المسارات في T-026):

1. الحلّ عبر ``resolve_workspace_path`` (احتواء + منع symlinks).
2. ملف سري (denylist بالاسم/الامتداد/المجلد) ⇒ **بديل حجب**
   ``«redacted: secret file»`` — المحتوى لا يُقرأ من القرص أصلًا.
3. شمّ المحتوى (entropy sniff): حتى ملف غير مُدرج بالاسم يُحجب إذا
   احتوى أنماط مفاتيح معروفة (AWS/GitHub/OpenAI/Slack/Google/private
   key blocks) أو سطر إسناد سري بقيمة عالية الإنتروبيا.
4. سقف حجم — الملفات الأضخم من الحد تُرفض بسبب مرصود (لا قراءة جزئية).

## denylist

بالاسم: `.env` وكل `.env.*` (عدا `.env.example`)، `id_rsa*`،
`credentials*`، `passwd`، `shadow`، `keys.txt`.
بالامتداد: `.pem`, `.key`, `.pkcs12`, `.pfx`, `.p12`, `.asc`,
و`*.env` (مثل `production.env`).
بالمجلد: `.aws`, `.ssh`, `.git`, `.gcloud`, `.kube`.

## إجراء التجاوز (override procedure)

لا يوجد علم «اقرأ السر رغم ذلك» — **بالتصميم**. المسارات الشرعية:
- قوالب البيئة: سمِّ الملف ``.env.example`` (مسموح صراحةً — بند مخاطر
  R-204: السياسة تطابق أنماط الأسرار الدقيقة لا ``*.example``).
- محتوى غير سري أطلق الشمّ خطأً: انقل القيمة لملف عادي أو علّق السطر —
  الشمّ يفحص أسطر الإسناد ذات المفاتيح السرية الصريحة فقط
  (`secret|token|password|api[_-]?key|private[_-]?key|...`).
- توسيع الحجب (لا تضييقه) متاح عبر ``extra_deny_names`` /
  ``extra_deny_extensions`` في المُنشئ.
"""
from __future__ import annotations

import math
import pathlib
import re
from dataclasses import dataclass
from typing import Iterable, Optional

from chain.path_policy import is_secret_file, resolve_workspace_path

# بديل الحجب — النص الوحيد الذي يراه الموديل مكان أي سر
REDACTION_STUB = "«redacted: secret file»"

DEFAULT_MAX_FILE_SIZE = 200 * 1024   # نفس سقف scan_folder_for_chain

# ═══════════════════ شمّ المحتوى (entropy sniff) ═══════════════════

# أنماط مفاتيح معروفة — كشف مباشر بغض النظر عن الإنتروبيا
_KEY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private_key_block",
     re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
]

# سطر إسناد سري: KEY = "VALUE" حيث الاسم سري صراحةً والقيمة طويلة
_SECRET_ASSIGNMENT = re.compile(
    r"(?im)^[^\n#/]{0,80}?"
    r"(secret|token|passwd|password|api[_-]?key|apikey|private[_-]?key|"
    r"access[_-]?key|auth)\w*"
    r"\s*[=:]\s*[\"']?"
    r"(?P<value>[A-Za-z0-9+/_.=-]{16,})"
    r"(?!\()"   # ليس استدعاء دالة — get_password_from_vault() ليس سرًا
)

_SNIFF_SCAN_LIMIT = 64 * 1024   # نفحص أول 64KB فقط — كافٍ وحتمي


def shannon_entropy(text: str) -> float:
    """إنتروبيا شانون بالبِت/حرف — 0.0 لنص فارغ."""
    if not text:
        return 0.0
    counts: dict[str, int] = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(text)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def sniff_secret_content(text: str) -> Optional[str]:
    """هل يبدو المحتوى حاملًا لسر؟ يرجع سبب الكشف أو None.

    مسارا كشف:
    1. أنماط مفاتيح معروفة (_KEY_PATTERNS) — مطابقة مباشرة.
    2. سطر إسناد باسم سري صريح وقيمة ≥16 حرفًا بإنتروبيا ≥ 3.5 بت/حرف
       (كلمات إنجليزية عادية ≈ 3.0؛ مفاتيح عشوائية base64/hex ≈ 4.0+).

    محافظ عمدًا: كود عادي/نص عادي لا يُعلَّم (بند الانحدار:
    normal files unaffected).
    """
    scan = text[:_SNIFF_SCAN_LIMIT]
    for reason, pattern in _KEY_PATTERNS:
        if pattern.search(scan):
            return reason
    for m in _SECRET_ASSIGNMENT.finditer(scan):
        value = m.group("value")
        if shannon_entropy(value) >= 3.5:
            return "high_entropy_assignment"
    return None


# ═══════════════════ نتيجة القراءة ═══════════════════

@dataclass(frozen=True)
class SafeReadResult:
    """نتيجة قراءة واحدة — القرار مرصود دائمًا (لا حجب صامت).

    - ``ok=True``: ``content`` هو النص الكامل.
    - ``redacted=True``: ``content`` هو ``REDACTION_STUB`` و``reason``
      يشرح (denylist/sniff reason) — هذا ما يصل للبرومبت، أبدًا القيمة.
    - ``ok=False`` بلا حجب: فشل عادي (غير موجود/ضخم/قراءة) — ``content``
      هو None و``reason`` يشرح.
    """
    path: str
    ok: bool
    content: Optional[str]
    redacted: bool = False
    reason: Optional[str] = None
    size: int = 0

    @property
    def prompt_text(self) -> str:
        """النص الآمن للحقن في برومبت — stub للسري، "" للفشل."""
        if self.content is None:
            return ""
        return self.content


# ═══════════════════ SafeReader ═══════════════════

class SafeReader:
    """بوابة القراءة الوحيدة للمحتوى المتجه للموديل (R-204).

    الاستخدام:
        reader = SafeReader(project_root)
        r = reader.read_text("src/app.py")
        if r.ok:
            prompt += r.content        # stub تلقائيًا لو الملف سري

    كل مصادر السياق وأداة ``read_file`` وماسحات المجلدات تمر من هنا
    (التوصيل في T-026).
    """

    def __init__(self, root: str | pathlib.Path,
                 max_file_size: int = DEFAULT_MAX_FILE_SIZE,
                 extra_deny_names: Iterable[str] = (),
                 extra_deny_extensions: Iterable[str] = ()) -> None:
        self.root = pathlib.Path(root).resolve()
        self.max_file_size = max_file_size
        self._extra_names = {n.lower() for n in extra_deny_names}
        self._extra_exts = {e.lower() for e in extra_deny_extensions}

    # ── التصنيف ──

    def is_denied(self, path: pathlib.Path) -> bool:
        """denylist: سياسة path_policy المركزية + توسعات المُنشئ +
        امتداد ``*.env`` (مثل production.env — كان يمر عبر
        _TEXT_EXTENSIONS قبل T-025)."""
        if is_secret_file(path):
            return True
        name = path.name.lower()
        if name in self._extra_names:
            return True
        suffix = path.suffix.lower()
        if suffix in self._extra_exts:
            return True
        if suffix == ".env" and name != ".env.example":
            return True
        return False

    # ── القراءة ──

    def read_text(self, rel_path: str) -> SafeReadResult:
        """قراءة آمنة لملف داخل الجذر.

        الترتيب: denylist (قبل أي لمس للقرص) → احتواء/symlink →
        وجود/حجم → قراءة → شمّ محتوى. أخطاء الاحتواء تُرجع نتيجة فشل
        مرصودة (لا استثناء — الحدود لا تفجّر مسار التجميع).
        """
        raw = pathlib.Path(rel_path)
        probe = raw if raw.is_absolute() else self.root / raw

        # 1) denylist — يُحسم من المسار وحده، المحتوى لا يُقرأ أصلًا
        if self.is_denied(probe):
            return SafeReadResult(
                path=rel_path, ok=True, content=REDACTION_STUB,
                redacted=True, reason="denylist",
            )

        # 2) احتواء + symlinks (سياسة المسار المركزية)
        try:
            full = resolve_workspace_path(
                self.root, rel_path, must_exist=False, allow_symlinks=False)
        except PermissionError as exc:
            return SafeReadResult(path=rel_path, ok=False, content=None,
                                  reason=f"policy: {exc}")

        # 3) وجود + حجم
        if not full.is_file():
            return SafeReadResult(path=rel_path, ok=False, content=None,
                                  reason="not_found")
        size = full.stat().st_size
        if size > self.max_file_size:
            return SafeReadResult(path=rel_path, ok=False, content=None,
                                  reason="too_large", size=size)

        # 4) قراءة + 5) شمّ المحتوى
        try:
            text = full.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return SafeReadResult(path=rel_path, ok=False, content=None,
                                  reason=f"read_error: {exc}", size=size)

        sniff = sniff_secret_content(text)
        if sniff is not None:
            return SafeReadResult(
                path=rel_path, ok=True, content=REDACTION_STUB,
                redacted=True, reason=f"sniff: {sniff}", size=size,
            )
        return SafeReadResult(path=rel_path, ok=True, content=text,
                              size=size)
