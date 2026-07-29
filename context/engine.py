# -*- coding: utf-8 -*-
"""ContextEngine (R-201 / T-018): جامع سياق واحد بمصادر قابلة للتركيب.

الهدف النهائي (R-201): كل ما "يراه الموديل" يمر من هنا — بدل ثلاث نسخ
متباعدة (كتلة server.py المضمّنة، ChainBuilder، AgentLoop._auto_prefetch).

T-018 يبني الهيكل + أول مصدر (MentionSource) **بدون توصيل** بأي مسار
إنتاجي — الـ goldens المثبّتة في T-017 هي عقد الـ parity.

المبدأ الأدائي المركزي: **مسح واحد لنظام الملفات لكل طلب**.
`ContextEngine.gather()` ينفّذ `ProjectScan` واحدًا ويمرره لكل المصادر —
ممنوع على أي مصدر أن يمشي الشجرة بنفسه (كتلة legacy كانت تعمل
`rglob` لكل كلمة في الرسالة: O(files × words) لكل رسالة).

Wiring diagram (بعد التوصيل في مهام R-201 اللاحقة):

    WS message ──► ContextEngine.gather(ContextRequest)
                        │  (ProjectScan واحد)
                        ├─► MentionSource   (T-018)
                        ├─► KeywordSource   (لاحقًا)
                        ├─► ProjectStructureSource (لاحقًا)
                        └─► HistorySource   (لاحقًا)
                        ▼
                   ContextBundle (مرتّب + بلا تكرار)
"""
from __future__ import annotations

import os
import pathlib
import time
from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

# T-021 (R-202): نموذج البيانات والحاوية انتقلا إلى context/bundle.py
# (sha256 content-dedupe + provenance + renderer). يُعاد تصديرهما من هنا
# للحفاظ على كل مسارات الاستيراد القائمة (المصادر/الـ facade/الاختبارات).
from context.bundle import (   # noqa: F401  (re-export مقصود)
    BundleEntry,
    ContextBundle,
    ContextItem,
    content_hash,
)


# ═══════════════════════════ نموذج البيانات ═══════════════════════════

@dataclass(frozen=True)
class ContextRequest:
    """طلب جمع سياق لرسالة واحدة."""
    message: str
    project_root: pathlib.Path


# ═══════════════════════ المسح الواحد المُخزَّن ═══════════════════════

class ProjectScan:
    """قائمة ملفات المشروع — تُبنى **مرة واحدة** لكل gather وتُشارَك.

    مشية os.walk واحدة مفروزة (T-049: كان rglob؛ نفس ترتيب goldens
    T-017 — فرز Path يعطي العناصر المطابقة بنفس ترتيب
    ``sorted(walk-results)`` بعد الفلترة). المصادر تستعلم عبر
    ``lookup_name``/``lookup_stem`` — لا تمشي الشجرة أبدًا.
    """

    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        files: list[pathlib.Path] = []
        for dirpath, _dirnames, filenames in os.walk(root):
            base = pathlib.Path(dirpath)
            for fname in filenames:
                p = base / fname
                if p.is_file():
                    files.append(p)
        files.sort()
        self.files: list[pathlib.Path] = files

    def rel(self, p: pathlib.Path) -> str:
        return str(p.relative_to(self.root)).replace("\\", "/")

    # ── واجهة الاستعلام الموحّدة (T-049 / R-702) ──
    # المصادر تنادي lookup_* بدل المسح الخطي المباشر؛ ``IndexedScan``
    # (context/index.py) يعيد تعريفهما بقواميس الفهرس المقلوب.

    def lookup_name(self, basename: str) -> list[pathlib.Path]:
        """مطابقة اسم كامل (مكافئ نمط glob بالـ basename) — خطية هنا."""
        return [p for p in self.files if p.name == basename]

    def lookup_stem(self, stem: str) -> list[pathlib.Path]:
        """مطابقة جذع (substring في الاسم) — خطية هنا."""
        return [p for p in self.files if stem in p.name]


ScanFactory = Callable[[pathlib.Path], ProjectScan]


# ═══════════════════════════ عقد المصدر ═══════════════════════════

@runtime_checkable
class ContextSource(Protocol):
    """عقد أي مصدر سياق — راجع context/AUTHORING.md قبل كتابة مصدر جديد."""

    kind: str

    def collect(self, request: ContextRequest,
                scan: ProjectScan) -> list[ContextItem]:
        """جمع عناصر هذا المصدر. يعمل على scan.files فقط — لا I/O شجري."""
        ...


# ═══════════════════════════ المحرّك ═══════════════════════════

class ContextEngine:
    """ينسّق المصادر: مسح واحد → collect بالترتيب → bundle بلا تكرار."""

    def __init__(self, sources: list[ContextSource],
                 scan_factory: ScanFactory = ProjectScan) -> None:
        self._sources = list(sources)
        self._scan_factory = scan_factory

    @property
    def sources(self) -> list[ContextSource]:
        return list(self._sources)

    def gather(self, request: ContextRequest) -> ContextBundle:
        """جمع سياق الرسالة — **مسح نظام ملفات واحد** مهما تعددت المصادر."""
        scan = self._scan_factory(request.project_root)
        bundle = ContextBundle()
        for source in self._sources:
            # TSK-609 (PM-04): توقيت collect لكل مصدر — نفس نمط chain
            # (monotonic → int ms). رصد إضافي بحت: المصدر الفاشل يسجَّل
            # زمنه أيضًا والاستثناء يُبتلع كما كان (نفس تسامح legacy).
            _t0 = time.monotonic()
            try:
                bundle.extend(source.collect(request, scan))
            except Exception:
                # مصدر معطوب لا يُسقط الجمع كله — نفس تسامح legacy
                pass
            kind = getattr(source, "kind", source.__class__.__name__)
            elapsed = int((time.monotonic() - _t0) * 1000)
            # مصدران بنفس kind (نظريًا): تجميع بالمجموع — لا فقدان رصد.
            bundle.source_timings_ms[kind] = (
                bundle.source_timings_ms.get(kind, 0) + elapsed)
        return bundle
