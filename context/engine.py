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

import pathlib
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

    مسح rglob واحد مفروز (نفس ترتيب goldens T-017: فرز Path يعطي
    العناصر المطابقة بنفس ترتيب sorted(rglob(pattern)) بعد الفلترة).
    المصادر تفلتر هذه القائمة في الذاكرة — لا تمشي الشجرة أبدًا.
    """

    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        self.files: list[pathlib.Path] = sorted(
            p for p in root.rglob("*") if p.is_file()
        )

    def rel(self, p: pathlib.Path) -> str:
        return str(p.relative_to(self.root)).replace("\\", "/")


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
            try:
                bundle.extend(source.collect(request, scan))
            except Exception:
                # مصدر معطوب لا يُسقط الجمع كله — نفس تسامح legacy
                pass
        return bundle
