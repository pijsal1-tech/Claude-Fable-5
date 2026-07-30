# -*- coding: utf-8 -*-
"""ProjectIndex (R-702 / T-049): فهرس مقلوب يقتل O(files) لكل رسالة.

═══════════════════ Index Design Note (وثيقة التصميم المطلوبة) ═══════════════════

**المشكلة:** كل رسالة دردشة كانت تبني ``ProjectScan`` جديدًا — مشية شجرية
كاملة O(files) لكل رسالة — ثم تفلتر المصادر القائمة خطيًا لكل مصطلح.
على مشروع بآلاف الملفات هذا زمن ملموس *في مسار كل-رسالة الساخن*.

**الحل:** ``ProjectIndex`` يُبنى **مرة واحدة عند فتح المشروع** ويعيش في
خانة ``ProjectHandle.index`` (المحجوزة منذ T-005 لـ R-702). يقدّم
``scan()`` الذي يعيد ``IndexedScan`` — بديل drop-in لـ ``ProjectScan``
بنفس العقد (``root`` / ``files`` / ``rel`` / ``lookup_*``) لكن **صفر
مشيات شجرية وقت الاستعلام**.

**الطزاجة (freshness) بآليتين متكاملتين:**

1. **Write-through hooks** — ``attach(fm)`` يسجّل ``notify_write`` في
   ``FileManager.add_write_hook``؛ كل ``write_file``/``edit_file`` يبلّغ
   الفهرس بالمسار النسبي فور ``os.replace``. ملف جديد يُدرَج بـ
   ``bisect.insort`` (يحفظ الترتيب العالمي) ويعاد اشتقاق القواميس.
   ⇒ يضمن معيار القبول "write-then-mention freshness".

2. **mtime-age sweep** — ``refresh_if_stale()`` يعيد البناء إذا تجاوز
   عمر الفهرس ``max_age_seconds`` (افتراضي 2.0s). يلتقط التعديلات
   الخارجية (out-of-band: محرر المستخدم، git checkout، ...) خلال
   sweep واحد ⇒ معيار القبول الثاني. ``scan()`` ينادي sweep تلقائيًا،
   فكل gather يرى شجرة بعمر ≤ 2 ثانية بلا مشية إلا عند الحاجة.

**البنى:**
- ``_files``: قائمة Path مفروزة — **نفس ترتيب** ``sorted(rglob-walk)``
  الذي ثبّتته goldens T-017 (فرز Path = فرز نص المسار الكامل).
- ``_by_name``: dict[basename → [paths]] — استعلام exact-name O(1).
- ``_by_ext``: dict[suffix → [paths]] — استعلام بالامتداد O(1).
- ``_names``: أزواج (name, path) مفروزة — أساس مطابقة الجذوع والـ
  lookup المرتّب (exact > prefix > substring).

**حدود صارمة:**
- البناء يستخدم ``os.walk`` — **ليس** rglob (بوابة grep في check.sh
  تمنع نداءات rglob في مسارات السياق).
- وقت الاستعلام: صفر I/O شجري؛ ``lookup_name`` قاموسي، ``lookup_stem``
  مسح ذاكرة على أسماء فقط (لا Path.name المكلف في الحلقة).
- ``IndexedScan`` لا ينادي ``ProjectScan.__init__`` (الذي يمشي الشجرة)
  — يستعير القائمة الحية من الفهرس مباشرة.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import bisect
import os
import pathlib
import time
from typing import Any, Callable

from context.engine import ProjectScan


class ProjectIndex:
    """فهرس ملفات المشروع — يُبنى عند الفتح، يبقى طازجًا بالخطافات + sweep."""

    def __init__(self, root: str | pathlib.Path,
                 max_age_seconds: float = 2.0,
                 clock: Callable[[], float] = time.monotonic,
                 snapshot_path: str | pathlib.Path | None = None) -> None:
        self.root = pathlib.Path(root).resolve()
        self.max_age_seconds = max_age_seconds
        self._clock = clock
        self._files: list[pathlib.Path] = []
        self._by_name: dict[str, list[pathlib.Path]] = {}
        self._by_ext: dict[str, list[pathlib.Path]] = {}
        self._names: list[tuple[str, pathlib.Path]] = []
        self._built_at: float = float("-inf")
        self.rebuild_count: int = 0
        # TSK-719 (FI-05/2): snapshot اختياري — تحميل ناجح يبذر الفهرس
        # بلا مشية شجرية (الفتح فوري)؛ الطزاجة تبقى على عقد T-049 القائم
        # (نافذة staleness واحدة ≤ max_age حتى أول sweep — نفس عقد
        # التعديلات الخارجية). فاشل/غائب ⇒ rebuild كالسابق.
        self._snapshot_path = (pathlib.Path(snapshot_path)
                               if snapshot_path is not None else None)
        self._snapshot_rels: list[str] | None = None   # آخر محفوظ/محمَّل
        if not self._seed_from_snapshot():
            self.rebuild()

    # ═══════════════════════ البناء والاشتقاق ═══════════════════════

    @property
    def files(self) -> list[pathlib.Path]:
        """قائمة الملفات المفروزة عالميًا (عقد ترتيب goldens T-017)."""
        return self._files

    def rebuild(self) -> None:
        """مشية شجرية واحدة (os.walk) ثم اشتقاق القواميس."""
        files: list[pathlib.Path] = []
        for dirpath, _dirnames, filenames in os.walk(self.root):
            base = pathlib.Path(dirpath)
            for fname in filenames:
                p = base / fname
                if p.is_file():          # يستبعد الروابط الميتة إلخ
                    files.append(p)
        files.sort()                     # فرز Path = فرز نص المسار الكامل
        self._files = files
        self._reindex()
        self._built_at = self._clock()
        self.rebuild_count += 1
        self._save_snapshot_if_changed()   # TSK-719: حفظ فقط عند التغيّر

    # ═══════════════ snapshot (TSK-719 / FI-05) ═══════════════

    def _seed_from_snapshot(self) -> bool:
        """بذر الفهرس من snapshot صالح — يعيد True عند النجاح.

        لا مشية شجرية: القائمة تُبنى من المسارات النسبية المحفوظة
        (فرز دفاعي يعيد فرض عقد الترتيب العالمي T-017)؛ ``_built_at``
        يُختم الآن فتنطبق نافذة sweep القياسية (≤ max_age) — أول
        استعلام بعدها يجري rebuild يلتقط أي انحراف خارجي.
        """
        if self._snapshot_path is None:
            return False
        from core.index_snapshot import load_snapshot
        rels = load_snapshot(self._snapshot_path, self.root)
        if rels is None:
            return False
        self._files = sorted(self.root / r for r in rels)
        self._reindex()
        self._built_at = self._clock()
        self._snapshot_rels = [self.rel(p) for p in self._files]
        return True

    def _save_snapshot_if_changed(self) -> None:
        """حفظ snapshot بعد rebuild — **فقط** إذا تغيّرت القائمة.

        يمنع churn الكتابة من sweep الدوري (rebuild كل ~2s على مشروع
        ساكن = صفر كتابات). الحفظ لا-يرفع (عقد core/index_snapshot).
        """
        if self._snapshot_path is None:
            return
        rels = [self.rel(p) for p in self._files]
        if rels == self._snapshot_rels:
            return
        from core.index_snapshot import save_snapshot
        if save_snapshot(self._snapshot_path, self.root, rels):
            self._snapshot_rels = rels

    def _reindex(self) -> None:
        """اشتقاق الفهارس المقلوبة من ``_files`` (المفروزة مسبقًا)."""
        by_name: dict[str, list[pathlib.Path]] = {}
        by_ext: dict[str, list[pathlib.Path]] = {}
        names: list[tuple[str, pathlib.Path]] = []
        for p in self._files:
            by_name.setdefault(p.name, []).append(p)
            by_ext.setdefault(p.suffix, []).append(p)
            names.append((p.name, p))
        self._by_name = by_name
        self._by_ext = by_ext
        self._names = names

    # ═══════════════════════ الطزاجة ═══════════════════════

    def refresh_if_stale(self, force: bool = False) -> bool:
        """sweep بالعمر: يعيد البناء إذا تجاوز العمر ``max_age_seconds``.

        يعيد True إذا حدث rebuild. يلتقط التعديلات الخارجية
        (out-of-band) خلال sweep واحد — معيار قبول T-049.
        """
        age = self._clock() - self._built_at
        if force or age > self.max_age_seconds:
            self.rebuild()
            return True
        return False

    def notify_write(self, rel_path: str) -> None:
        """خطاف write-through من FileManager — طزاجة فورية بعد الكتابة.

        ملف جديد يُدرَج في موضعه المفروز (bisect) ويعاد الاشتقاق؛
        الكتابة فوق ملف مفهرس لا تغيّر البنية (المحتوى لا يُفهرَس).
        """
        try:
            full = (self.root / rel_path).resolve()
        except (OSError, ValueError):
            return
        if not full.is_file():
            return
        idx = bisect.bisect_left(self._files, full)
        if idx < len(self._files) and self._files[idx] == full:
            return                       # موجود مسبقًا — no-op
        self._files.insert(idx, full)
        self._reindex()

    def attach(self, fm: Any) -> None:
        """تسجيل الخطاف في FileManager (تسامحيًا مع fm بلا خطافات)."""
        add_hook = getattr(fm, "add_write_hook", None)
        if callable(add_hook):
            add_hook(self.notify_write)

    # ═══════════════════════ الاستعلام المرتّب ═══════════════════════

    def rel(self, p: pathlib.Path) -> str:
        return str(p.relative_to(self.root)).replace("\\", "/")

    def lookup_name(self, basename: str) -> list[pathlib.Path]:
        """مطابقة اسم كامل — O(1) قاموسية (يطابق rglob-basename القديم)."""
        return list(self._by_name.get(basename, ()))

    def lookup_stem(self, stem: str) -> list[pathlib.Path]:
        """مطابقة جذع (substring في الاسم) — مسح ذاكرة على الأسماء فقط."""
        return [p for name, p in self._names if stem in name]

    def lookup_ext(self, ext: str) -> list[pathlib.Path]:
        """كل الملفات بامتداد معيّن — O(1) قاموسية."""
        return list(self._by_ext.get(ext, ()))

    def lookup(self, term: str) -> list[str]:
        """بحث مرتّب: exact > prefix > substring؛ ترتيب عالمي داخل كل رتبة."""
        exact: list[str] = []
        prefix: list[str] = []
        substr: list[str] = []
        for name, p in self._names:
            if name == term:
                exact.append(self.rel(p))
            elif name.startswith(term):
                prefix.append(self.rel(p))
            elif term in name:
                substr.append(self.rel(p))
        return exact + prefix + substr

    # ═══════════════════════ جسر المحرّك ═══════════════════════

    def scan(self) -> "IndexedScan":
        """مسح جاهز للمحرّك — sweep طزاجة ثم عرض بلا مشية شجرية."""
        self.refresh_if_stale()
        return IndexedScan(self)


class IndexedScan(ProjectScan):
    """بديل drop-in لـ ProjectScan يستعير قائمة الفهرس — صفر مشيات.

    **عمدًا لا ينادي** ``super().__init__`` (الذي يمشي الشجرة):
    يستعير ``files`` الحية من الفهرس، فأي notify_write لاحق داخل نفس
    الـ gather ينعكس فورًا (نفس القائمة بالمرجع).
    """

    def __init__(self, index: ProjectIndex) -> None:   # noqa: D107
        self.root = index.root
        self.files = index.files
        self._index = index

    def lookup_name(self, basename: str) -> list[pathlib.Path]:
        return self._index.lookup_name(basename)

    def lookup_stem(self, stem: str) -> list[pathlib.Path]:
        return self._index.lookup_stem(stem)
