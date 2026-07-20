# -*- coding: utf-8 -*-
"""T-100 (R-801): StrategyPluginRegistry — اكتشاف إضافات الاستراتيجيات.

دورة حياة السجل (Registry lifecycle):

1. **الاكتشاف (discover)** — `importlib.metadata.entry_points(
   group="webdev_ai.strategies")`. الاكتشاف نفسه لا يستورد أي كود
   إضافة (كسول)؛ الاستيراد يحدث فقط داخل `ep.load()` لكل إضافة على
   حدة (نتيجة spike T-052 §1: العزل لكل-إضافة يعطي بالضبط سلوك
   "الفشل يعزل الإضافة، لا المضيف").

2. **بوابة التحقق (validation gate)** — ثلاث مراحل متتابعة، وأي
   استثناء في أي مرحلة ⇒ سجل حجر صحي مُهيكل ولا انهيار للمضيف أبدًا:

   - ``import``  — ‏`ep.load()` نفسه (ImportError/SyntaxError/أي شيء).
   - ``shape``   — فحص الشكل: الكائن **صنف** يكشف `build()` قابلة
     للنداء و`routing_hints` من نوع `dict`.
   - ``dry_run`` — إنشاء نسخة ثم نداء `build()` على طلب fixture
     ثابت (`_FIXTURE_REQUEST`)؛ إرجاع None يُعامل كفشل أيضًا
     (الإضافة التي لا تنتج خطة لا تنفع الراوتر).

3. **الكشف (exposure)** — بعد `discover()`:
   - ``loaded``       — قاموس name → صنف الإضافة الصالح (نسخة دفاعية).
   - ``quarantined``  — قائمة `QuarantineRecord(name, stage, reason)`
     (تُعرض في السجلات/الواجهة لاحقًا — أبدًا لا crash).
   - ``get(name)``    — الصنف الصالح أو None.

ملاحظات تصميم:
- **الأسماء المكررة**: أول إضافة صالحة بالاسم تفوز؛ التالية بنفس
  الاسم تُحجر بمرحلة ``shape`` وسبب صريح (تبديل صامت لاستراتيجية
  محمّلة = مخاطرة أمنية).
- **حقن الاكتشاف**: `entry_points_fn` قابل للحقن في المُنشئ حتى
  تختبر الوحدة مصفوفة الفشل بأكملها بدون تثبيت حزم فعلية — الافتراضي
  هو `importlib.metadata.entry_points` الحقيقي.
- السجل **مستقل** حتى T-102 (لا يلمس core/strategy.py ولا الراوتر)؛
  نطاق الصلاحيات (PluginContext) موضوع T-101 وليس مشكلة تحميل
  (خلاصة الـ spike §1 نقطة 3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib.metadata import entry_points as _real_entry_points
from typing import Any, Callable, Iterable, Protocol


ENTRY_POINT_GROUP = "webdev_ai.strategies"

# طلب الـ fixture الثابت للـ dry-run — عمدًا تافه وثابت بايت-بايت:
# البوابة تختبر أن الإضافة *تعمل*، لا جودة خطتها.
_FIXTURE_REQUEST = "Add a hello-world route to the project (dry-run fixture)."


class _EntryPointLike(Protocol):
    """الحد الأدنى المطلوب من entry point — يسمح بحقن بدائل للاختبار."""
    name: str

    def load(self) -> Any: ...  # pragma: no cover — بروتوكول


@dataclass(frozen=True)
class QuarantineRecord:
    """سجل حجر صحي مُهيكل لإضافة فشلت في البوابة.

    - ``stage``: أين فشلت — ``import`` | ``shape`` | ``dry_run``.
    - ``reason``: نص مقروء (نوع الاستثناء + رسالته، أو وصف فشل الشكل).
    """
    name: str
    stage: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        """تمثيل قابل للتسلسل — للسجلات/الواجهة لاحقًا."""
        return {"name": self.name, "stage": self.stage,
                "reason": self.reason}


@dataclass
class StrategyPluginRegistry:
    """سجل إضافات الاستراتيجيات — اكتشاف + تحقق + حجر صحي.

    الاستخدام::

        registry = StrategyPluginRegistry()
        registry.discover()
        cls = registry.get("my_strategy")   # صنف صالح أو None
    """
    entry_points_fn: Callable[..., Iterable[_EntryPointLike]] = \
        _real_entry_points
    _loaded: dict[str, type] = field(default_factory=dict, init=False)
    _quarantined: list[QuarantineRecord] = field(
        default_factory=list, init=False)

    # ───────────────────────────────────────────────
    #   الكشف (exposure)
    # ───────────────────────────────────────────────

    @property
    def loaded(self) -> dict[str, type]:
        """الأصناف الصالحة name → class (نسخة دفاعية)."""
        return dict(self._loaded)

    @property
    def quarantined(self) -> list[QuarantineRecord]:
        """سجلات الحجر الصحي بترتيب الاكتشاف (نسخة دفاعية)."""
        return list(self._quarantined)

    def get(self, name: str) -> type | None:
        """الصنف الصالح بالاسم — None للمجهول/المحجور."""
        return self._loaded.get(name)

    # ───────────────────────────────────────────────
    #   الاكتشاف + بوابة التحقق
    # ───────────────────────────────────────────────

    def discover(self) -> None:
        """اكتشاف وتحميل والتحقق من كل إضافات المجموعة.

        idempotent-بالمسح: كل نداء يعيد بناء الحالة من الصفر (لا
        تراكم عبر النداءات). مجموعة فارغة ⇒ سجل فارغ بلا خطأ.
        """
        self._loaded = {}
        self._quarantined = []

        for ep in self.entry_points_fn(group=ENTRY_POINT_GROUP):
            name = ep.name

            # المرحلة 1: import — الاستيراد معزول داخل ep.load().
            try:
                obj = ep.load()
            except Exception as exc:  # noqa: BLE001 — عزل مقصود
                self._quarantine(name, "import", exc)
                continue

            # المرحلة 2: shape — صنف بـ build() قابلة للنداء
            # وrouting_hints من نوع dict.
            shape_error = self._shape_error(name, obj)
            if shape_error is not None:
                self._quarantined.append(
                    QuarantineRecord(name, "shape", shape_error))
                continue

            # المرحلة 3: dry_run — إنشاء نسخة + build() على الـ fixture.
            try:
                instance = obj()
                plan = instance.build(_FIXTURE_REQUEST)
            except Exception as exc:  # noqa: BLE001 — عزل مقصود
                self._quarantine(name, "dry_run", exc)
                continue
            if plan is None:
                self._quarantined.append(QuarantineRecord(
                    name, "dry_run",
                    "build() returned None on the fixture request"))
                continue

            self._loaded[name] = obj

    # ───────────────────────────────────────────────
    #   أدوات داخلية
    # ───────────────────────────────────────────────

    def _shape_error(self, name: str, obj: Any) -> str | None:
        """فحص الشكل — يرجع سبب الفشل نصًا أو None عند الصلاحية."""
        if name in self._loaded:
            return (f"duplicate plugin name {name!r} — a valid plugin "
                    "with this name is already loaded (first wins)")
        if not isinstance(obj, type):
            return (f"entry point resolved to {type(obj).__name__!r}, "
                    "expected a class")
        if not callable(getattr(obj, "build", None)):
            return "class has no callable build() method"
        if not isinstance(getattr(obj, "routing_hints", None), dict):
            return "class has no dict routing_hints attribute"
        return None

    def _quarantine(self, name: str, stage: str, exc: Exception) -> None:
        """تسجيل استثناء كسجل حجر صحي مُهيكل."""
        self._quarantined.append(QuarantineRecord(
            name, stage, f"{type(exc).__name__}: {exc}"))
