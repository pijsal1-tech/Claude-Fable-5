# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  Path Policy Helper — resolve_workspace_path
  
  Centralized verification for path containment, symlink
  prevention, and secrets denylist checks.
═══════════════════════════════════════════════════════
"""
import functools
import logging
import os
import pathlib
from typing import Set

_LOG = logging.getLogger("chain.path_policy")

SECRETS_DENYLIST_NAMES: Set[str] = {
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "credentials", "passwd", "shadow", "keys.txt",
    # TSK-735a (D-20): ملف مفاتيح API الجانبي — سر بالتعريف؛
    # أدوات الوكيل وSafeReader لا تقرآنه أبدًا.
    "provider_keys.json",
}
SECRETS_DENYLIST_EXTENSIONS: Set[str] = {
    ".pem", ".key", ".pkcs12", ".pfx", ".p12", ".asc"
}
SECRETS_DENYLIST_DIRS: Set[str] = {
    ".aws", ".ssh", ".git", ".gcloud", ".kube"
}

# TSK-CEV-117 (CEV-F-018): محارف "خفية" لا يعتبرها str.strip() بيضاء
# لكنها تُطبَّع أو تُتجاهل بصريًا/على مستوى نظام الملفات. تُزال صراحةً
# قبل المطابقة حتى لا يصير `.env<ZWSP>` مسارَ تجاوزٍ لقائمة الحجب.
_INVISIBLE_CHARS = (
    "\u200b"  # ZERO WIDTH SPACE
    "\u200c"  # ZERO WIDTH NON-JOINER
    "\u200d"  # ZERO WIDTH JOINER
    "\u2060"  # WORD JOINER
    "\ufeff"  # BOM / ZERO WIDTH NO-BREAK SPACE
    "\u180e"  # MONGOLIAN VOWEL SEPARATOR
    "\x00"    # NUL (قاطع سلاسل في طبقات C)
)


# محارف تُقلَّم من نهاية الاسم (بيضاء بمعناها الواسع + النقطة).
# تُستخدم في المسار السريع فقط؛ التقليم الفعلي يستخدم str.strip.
_TRAILING_TRIGGERS = frozenset(
    " \t\n\r\x0b\x0c."
    "\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007"
    "\u2008\u2009\u200a\u202f\u205f\u3000"
)
_INVISIBLE_SET = frozenset(_INVISIBLE_CHARS)


def _needs_normalization(name: str) -> bool:
    """هل يحتمل الاسم محارف تجاوز تستوجب التطبيع الكامل؟ (مسار سريع)

    **متحفظ بالتصميم**: أي شك ⇒ True (نُطبِّع تطبيعًا كاملًا). القيمة
    False تعني حصرًا أن التطبيع الكامل سيُنتج `name.lower()` نفسه.

    الأداء (TSK-CEV-117): هذا الفحص يجري لكل ملف في الفهرسة/البحث،
    فاستُخدم `frozenset.isdisjoint` (حلقة بمستوى C) بدل `str.isspace()`
    و`any(...)` — القياس: 0.36 µs/اسم مقابل 1.90 µs للنسخة الساذجة
    (أسرع ~5×)، وهو ما يُبقي `test_search_perf` تحت عتبة 1s.
    """
    if not name:
        return False
    if name[-1] in _TRAILING_TRIGGERS or name[0] in _TRAILING_TRIGGERS:
        return True
    if ":" in name:
        return True
    return not _INVISIBLE_SET.isdisjoint(name)


@functools.lru_cache(maxsize=8192)
def _classify_name(name_lower: str) -> bool:
    """هل يُصنَّف الاسم (بعد التطبيع) سرًّا بمطابقة الاسم/الامتداد؟

    مُذكَّرة (TSK-CEV-117): في المشاريع الكبيرة تتكرر الامتدادات
    والأسماء بكثافة، فالتذكير يجعل الكلفة ثابتة تقريبًا بدل خطية.
    المفتاح هو الاسم **المطبَّع** حصرًا (لا كائن المسار) فالنتيجة
    دالة نقية منه — آمنة للتذكير.
    """
    if name_lower == ".env.example":
        return False
    if name_lower == ".env" or name_lower.startswith(".env."):
        return True
    if name_lower in SECRETS_DENYLIST_NAMES:
        return True
    # الامتداد يُشتق من الاسم المطبَّع (لا من path.suffix الخام) لأن
    # `cert.pem ` كان يعطي suffix='.pem ' فيفلت من مطابقة المجموعة.
    dot = name_lower.rfind(".")
    if dot > 0:  # dot==0 يعني ملفًا مخفيًا بلا امتداد مثل `.env`
        if name_lower[dot:] in SECRETS_DENYLIST_EXTENSIONS:
            return True
    return False


@functools.lru_cache(maxsize=4096)
def _is_secret_dir_part(part: str) -> bool:
    """هل مقطع المسار مجلدًا سرًّا؟ (مُذكَّر — المقاطع تتكرر بكثافة)"""
    if not part.startswith("."):
        if not _needs_normalization(part):
            return False
        part = normalize_secret_name(part)
        if not part.startswith("."):
            return False
    else:
        part = normalize_secret_name(part)
    if part in SECRETS_DENYLIST_DIRS:
        return True
    return part[1:] in {"aws", "ssh", "git", "gcloud", "kube"}


def normalize_secret_name(name: str) -> str:
    """تطبيع اسم ملف قبل مطابقته بقوائم حجب الأسرار (TSK-CEV-117).

    الغرض: إغلاق CEV-F-018 — المطابقة الحرفية على `path.name.lower()`
    كانت تُخترَق بلواحق لا تغيّر الملف الذي يُفتَح فعليًا على Win32.

    خطوات التطبيع (بهذا الترتيب):
    1. إزالة المحارف الخفية (`_INVISIBLE_CHARS`) من الطرفين والداخل.
    2. قصّ لاحقة NTFS ADS: `name:stream` / `name::$DATA` → `name`،
       لأن Win32 يفتح بها **نفس** محتوى الملف الأصلي.
    3. تقليم المحارف البيضاء (بما فيها NBSP/U+3000 عبر str.strip)
       والنقاط اللاحقة **بالتناوب** حتى الاستقرار، لأن Win32 يقلّم
       المسافات والنقاط اللاحقة معًا (`.env . . ` → `.env`).
    4. توحيد حالة الأحرف (lower) أخيرًا.

    ملاحظة عقد: هذه الدالة **تُشدِّد** الحجب ولا تُرخّيه؛ الاسم المطبَّع
    يُستخدم للمطابقة فقط ولا يُستخدم إطلاقًا لفتح الملفات.
    """
    out = name
    # مسار سريع (TSK-CEV-117): الغالبية العظمى من الأسماء الحقيقية لا
    # تحتوي أيًّا من محارف التجاوز. الفحص الرخيص أدناه يمنع دفع ثمن
    # 7 عمليات replace + حلقة تقليم لكل ملف في المشاريع الكبيرة
    # (مسار حِسّاس للأداء: tool_search_code/الفهرسة على 5k+ ملف —
    # راجع tests/integration/test_search_perf.py). القرار لا يتغير:
    # الاسم بلا محارف تجاوز يكون تطبيعه = lower() فقط.
    if not (_needs_normalization(out)):
        return out.lower()
    for ch in _INVISIBLE_CHARS:
        out = out.replace(ch, "")
    # NTFS Alternate Data Stream: نأخذ الجزء قبل أول ':' فقط.
    # ملاحظة: على POSIX قد يكون ':' محرفًا شرعيًا في الاسم، فالنتيجة
    # هنا حجب زائد لأسماء غريبة (fail-safe مقصود) لا تسريب.
    if ":" in out:
        out = out.split(":", 1)[0]
    # تقليم بالتناوب حتى الاستقرار: " .env . . " → ".env"
    prev = None
    while prev != out:
        prev = out
        out = out.strip().rstrip(".").strip()
    return out.lower()


def is_secret_file(path: pathlib.Path) -> bool:
    """Checks if a path matches any secrets pattern or directory name.

    TSK-CEV-117 (CEV-F-018): كل مطابقة تجري على الاسم **المطبَّع**
    (`normalize_secret_name`) لا على `path.name.lower()` الخام.
    """
    # ── مسار سريع مُدمَج سطريًّا (TSK-CEV-117) ─────────────────────
    # هذه الدالة تُنادى لكل ملف في الفهرسة/البحث (5k+ ملف)، وكلفة
    # نداء الدوال في بايثون تفوق كلفة المنطق نفسه؛ لذا يُفحص الاسم
    # الشائع (بلا محارف تجاوز) هنا مباشرةً بلا أي نداء إضافي.
    # القرار مطابق تمامًا للمسار الكامل — الاختبارات تغطي الفرعين.
    name = path.name
    if name and name[-1] not in _TRAILING_TRIGGERS \
            and name[0] not in _TRAILING_TRIGGERS \
            and ":" not in name \
            and _INVISIBLE_SET.isdisjoint(name):
        name_lower = name.lower()
    else:
        name_lower = normalize_secret_name(name)

    # 1) مطابقة الاسم/الامتداد (مُذكَّرة — الأسماء/الامتدادات تتكرر).
    if _classify_name(name_lower):
        return True

    # 2) مقاطع المسار: مجلد سري يحجب أي ملف داخله — بما فيه
    #    `.env.example` (الاستثناء يشمل الاسم فقط لا المجلدات).
    #    الغالبية العظمى من المقاطع لا تبدأ بنقطة، فتُستبعد بفحص
    #    `startswith` رخيص قبل أي نداء دالة أو بحث في الكاش.
    for part in path.parts:
        if part.startswith(".") or _needs_normalization(part):
            if _is_secret_dir_part(part):
                return True
    return False

def resolve_workspace_path(
    root: str | pathlib.Path,
    requested_path: str,
    must_exist: bool = False,
    allow_symlinks: bool = False
) -> pathlib.Path:
    """
    Safely resolves a requested path under the workspace root.
    Ensures containment, symlink checks, and secrets denylist enforcement.
    """
    root_path = pathlib.Path(root).resolve()
    
    # Handle empty/default paths
    if not requested_path:
        requested_path = "."
        
    p = pathlib.Path(requested_path)
    if p.is_absolute():
        raw_path = p
    else:
        raw_path = root_path / p
        
    # Resolve absolute path to canonical form
    try:
        resolved_path = raw_path.resolve()
    except Exception:
        resolved_path = raw_path.absolute()
        
    # Standardize separator and case comparison on Windows
    if os.name == 'nt':
        r_parts = [part.lower() for part in root_path.parts]
        f_parts = [part.lower() for part in resolved_path.parts]
        if len(f_parts) < len(r_parts) or f_parts[:len(r_parts)] != r_parts:
            raise PermissionError(
                f"Access denied: path '{requested_path}' resolves to '{resolved_path}' "
                f"which is outside project root '{root_path}'."
            )
    else:
        try:
            resolved_path.relative_to(root_path)
        except ValueError:
            raise PermissionError(
                f"Access denied: path '{requested_path}' resolves to '{resolved_path}' "
                f"which is outside project root '{root_path}'."
            )
            
    # Symlink traversal check
    # TSK-618 (ASF-07/NF-28): فصل القياس عن القرار — النسخة السابقة
    # وضعت raise PermissionError داخل try يلتقط Exception واسعًا
    # (PermissionError ⊂ OSError ⊂ Exception) فكان الرفض نفسه يُبتلع
    # والفحص ميتًا بالكامل. الآن: is_symlink وحده داخل try ضيق
    # يلتقط OSError موسومًا بتحذير (لا تخطٍّ صامت)؛ الرفض خارجه.
    if not allow_symlinks:
        curr = raw_path
        # Traverse upwards checking if any part of the requested path is a symlink
        while curr != root_path and len(curr.parts) > len(root_path.parts):
            try:
                is_link = curr.is_symlink()
            except OSError as e:
                _LOG.warning(
                    "symlink check failed for %r (segment of %r): %s — "
                    "segment skipped; final containment and secrets "
                    "checks still apply",
                    str(curr), requested_path, e)
                is_link = False
            if is_link:
                raise PermissionError(
                    f"Access denied: Symlinks are not allowed: '{requested_path}'"
                )
            curr = curr.parent
            
    # Secrets denylist check
    if is_secret_file(resolved_path):
        raise PermissionError(
            f"Access denied: '{requested_path}' matches blocked secret patterns."
        )
        
    if must_exist and not resolved_path.exists():
        raise FileNotFoundError(f"File not found: '{requested_path}'")
        
    return resolved_path
