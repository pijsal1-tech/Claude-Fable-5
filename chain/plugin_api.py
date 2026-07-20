# -*- coding: utf-8 -*-
"""T-101 (R-801): PluginContext — عقد مؤلّف الإضافة (Plugin Author Contract).

**العقد**: `PluginContext` هو الكائن *الوحيد* الذي يُسلَّم إلى
`build()` في إضافات الاستراتيجيات. ما ليس على سطحه غير موجود
بالنسبة للإضافة — لا مدير ملفات خام، لا مخزن جلسات، لا مقابض خادم.
النطاق مفروض بتوقيع المُنشئ + بوابة grep في `scripts/check.sh`
(خلاصة spike T-052 §1 نقطة 3: نطاق الصلاحيات مشكلة تصميم واجهة،
لا مشكلة آلية استيراد).

سطح الصلاحيات الكامل (ما تراه الإضافة):

1. **بيانات الطلب (للقراءة)**:
   - ``user_request: str`` — نص طلب المستخدم.
   - ``run_id: str`` — معرّف التشغيلة (لترقيم الأحداث).
   - ``metadata`` — خاصية ترجع **نسخة دفاعية** من قاموس البيانات
     الوصفية (التعديل على النسخة لا يمس الأصل).

2. **عروض سياق للقراءة فقط** (ContextEngine views — من
   ``ContextBundle`` المُجمَّعة مسبقًا؛ الإضافة لا تمشي الشجرة ولا
   تفتح ملفات بنفسها):
   - ``context_paths() -> list[str]`` — مسارات عناصر السياق (نسخة).
   - ``context_content(path) -> str | None`` — محتوى عنصر بالمسار
     (None للمجهول أو لعنصر بلا محتوى — quirk الـ huge-file).
   - ``context_items() -> list[tuple[str, str | None]]`` — أزواج
     (مسار، محتوى) بترتيب الحزمة (نسخة).

3. **خطاف بثّ الأحداث**:
   - ``emit(frame_type, payload)`` — يمرّر لحقّاقة emit المحقونة
     (مثل ناشر ``StepProgress`` على الـ EventBus عبر
     ``event_bus_emitter``). حمولة كل نداء **تُنسَخ** قبل التمرير —
     الإضافة لا تحتفظ بمقبض على ما استُهلك.

**ما لا تراه الإضافة (بالتصميم)**: مدير الملفات (الكتابة تمر حصريًا
من مسار actions المحروس بالبوابة)، مخزن الجلسات، كائن الخادم، الـ
providers pool. بوابة `scripts/check.sh` ترفض أي إشارة لتلك الأسماء
داخل هذه الوحدة وداخل ``chain/plugin_registry.py``.

المُنشئان المساعدان:
- ``fixture_context()`` — سياق dry-run الثابت الذي تستخدمه بوابة
  التحقق في السجل (حزمة فارغة + emit جامع مهمل).
- ``event_bus_emitter(bus, run_id)`` — يبني حقّاقة emit تنشر
  ``StepProgress`` مكتوب النوع على EventBus حقيقي.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from context.bundle import ContextBundle
from core.events import EventBus, StepProgress


# نص طلب الـ fixture لبوابة dry-run — ثابت بايت-بايت (يطابق دلالة
# بوابة T-100: نختبر أن الإضافة *تعمل*، لا جودة خطتها).
FIXTURE_REQUEST = "Add a hello-world route to the project (dry-run fixture)."

EmitFn = Callable[[str, dict[str, Any]], None]


def _noop_emit(frame_type: str, payload: dict[str, Any]) -> None:
    """حقّاقة emit مهملة — للـ fixtures والاختبارات."""


@dataclass(frozen=True)
class PluginContext:
    """السطح الكامل الممنوح لإضافة استراتيجية — راجع رأس الوحدة.

    frozen: الإضافة لا تستطيع تعليق حالة على السياق ولا استبدال
    الحقّاقات. كل ما يخرج منه نسخ دفاعية.
    """
    user_request: str
    run_id: str = ""
    _bundle: ContextBundle = field(default_factory=ContextBundle)
    _emit_fn: EmitFn = _noop_emit
    _metadata: Mapping[str, Any] = field(default_factory=dict)

    # ───────────── بيانات الطلب ─────────────

    @property
    def metadata(self) -> dict[str, Any]:
        """نسخة دفاعية من البيانات الوصفية."""
        return dict(self._metadata)

    # ───────────── عروض السياق (قراءة فقط) ─────────────

    def context_paths(self) -> list[str]:
        """مسارات عناصر السياق بترتيب الحزمة — نسخة."""
        return self._bundle.paths()

    def context_content(self, path: str) -> str | None:
        """محتوى أول عنصر بهذا المسار — None للمجهول/بلا محتوى."""
        for item in self._bundle.items:
            if item.path == path:
                return item.content
        return None

    def context_items(self) -> list[tuple[str, str | None]]:
        """أزواج (مسار، محتوى) بترتيب الحزمة — نسخة."""
        return [(item.path, item.content) for item in self._bundle.items]

    # ───────────── خطاف البث ─────────────

    def emit(self, frame_type: str, payload: dict[str, Any]) -> None:
        """بثّ حدث تقدّم — الحمولة تُنسَخ قبل التمرير."""
        self._emit_fn(frame_type, dict(payload))


# ═══════════════════════ المُنشئان المساعدان ═══════════════════════

def fixture_context() -> PluginContext:
    """سياق dry-run الثابت لبوابة التحقق في السجل (T-100 → T-101)."""
    return PluginContext(user_request=FIXTURE_REQUEST,
                         run_id="plugin-dry-run")


def event_bus_emitter(bus: EventBus, run_id: str) -> EmitFn:
    """حقّاقة emit تنشر ``StepProgress`` مكتوب النوع على الـ bus."""
    def _emit(frame_type: str, payload: dict[str, Any]) -> None:
        bus.publish(StepProgress(run_id=run_id, frame_type=frame_type,
                                 payload=payload))
    return _emit
