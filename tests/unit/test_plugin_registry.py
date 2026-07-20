# -*- coding: utf-8 -*-
"""T-100 (R-801): StrategyPluginRegistry — مصفوفة تحميل/تحقق/حجر صحي.

يغطي (بنود قبول T-100):
- entry points تمثيلية (صالح / شكل-سيئ / خطأ-استيراد / انهيار-dry-run)
  ⇒ الصالح وحده يُحمّل، وثلاثة سجلات حجر صحي بمرحلة+سبب صحيحين.
- الاكتشاف مع صفر إضافات مثبتة ⇒ سجل فارغ، لا خطأ.
- سلوكيات إضافية: build() يرجع None ⇒ حجر dry_run؛ تكرار الاسم ⇒
  الأول يفوز والثاني يُحجر؛ discover() idempotent-بالمسح؛ النسخ
  المكشوفة دفاعية؛ to_dict قابل للتسلسل.

الحقن: `entry_points_fn` تُستبدل بدوالّ ترجع entry points مزيفة —
لا حاجة لتثبيت حزم فعلية (نمط ثبّته spike T-052: الاستيراد معزول
داخل ep.load() فمحاكاته باستثناء من load() مكافئة تمامًا).
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chain.plugin_registry import (  # noqa: E402
    ENTRY_POINT_GROUP,
    QuarantineRecord,
    StrategyPluginRegistry,
)


# ═══════════════ أدوات: entry points مزيفة ═══════════════

class FakeEntryPoint:
    """entry point مزيف — load() يرجع كائنًا أو يرمي استثناء."""

    def __init__(self, name, obj=None, load_exc=None):
        self.name = name
        self._obj = obj
        self._load_exc = load_exc

    def load(self):
        if self._load_exc is not None:
            raise self._load_exc
        return self._obj


class GoodStrategy:
    """إضافة صالحة — صنف بـ build() وrouting_hints قاموس."""
    routing_hints = {"tier": "chained", "score_min": 3}

    def build(self, user_request, **kwargs):
        return {"steps": [{"id": "s1", "prompt": user_request}]}


class BadShapeNoBuild:
    """شكل سيئ — بلا build()."""
    routing_hints = {}


class BadShapeHintsNotDict:
    """شكل سيئ — routing_hints ليست dict."""
    routing_hints = "chained"

    def build(self, user_request, **kwargs):
        return {}


class DryRunCrash:
    """ينهار عند build() على الـ fixture."""
    routing_hints = {}

    def build(self, user_request, **kwargs):
        raise RuntimeError("plan explosion on fixture")


class DryRunNone:
    """build() يرجع None — خطة غائبة = فشل."""
    routing_hints = {}

    def build(self, user_request, **kwargs):
        return None


class InitCrash:
    """ينهار عند الإنشاء نفسه (قبل build) — يُحجر بمرحلة dry_run."""
    routing_hints = {}

    def __init__(self):
        raise ValueError("constructor bomb")

    def build(self, user_request, **kwargs):  # pragma: no cover
        return {}


def _registry_with(eps):
    """سجل بحقن قائمة entry points ثابتة + تأكيد المجموعة الصحيحة."""
    def fake_entry_points(*, group):
        assert group == ENTRY_POINT_GROUP
        return list(eps)
    reg = StrategyPluginRegistry(entry_points_fn=fake_entry_points)
    reg.discover()
    return reg


# ═══════════════ 1) المصفوفة الأساسية (بند القبول) ═══════════════

class TestLoadValidateQuarantineMatrix:
    def test_only_good_plugin_loads(self):
        reg = _registry_with([
            FakeEntryPoint("good", obj=GoodStrategy),
            FakeEntryPoint("bad_shape", obj=BadShapeNoBuild),
            FakeEntryPoint("broken_import",
                           load_exc=ImportError("no module named x")),
            FakeEntryPoint("crashy", obj=DryRunCrash),
        ])
        assert list(reg.loaded) == ["good"]
        assert reg.get("good") is GoodStrategy
        assert len(reg.quarantined) == 3

    def test_quarantine_stages_and_reasons(self):
        reg = _registry_with([
            FakeEntryPoint("good", obj=GoodStrategy),
            FakeEntryPoint("bad_shape", obj=BadShapeNoBuild),
            FakeEntryPoint("broken_import",
                           load_exc=ImportError("no module named x")),
            FakeEntryPoint("crashy", obj=DryRunCrash),
        ])
        by_name = {q.name: q for q in reg.quarantined}
        assert by_name["bad_shape"].stage == "shape"
        assert "build" in by_name["bad_shape"].reason
        assert by_name["broken_import"].stage == "import"
        assert by_name["broken_import"].reason.startswith("ImportError:")
        assert "no module named x" in by_name["broken_import"].reason
        assert by_name["crashy"].stage == "dry_run"
        assert by_name["crashy"].reason.startswith("RuntimeError:")
        assert "plan explosion" in by_name["crashy"].reason

    def test_get_unknown_or_quarantined_is_none(self):
        reg = _registry_with([
            FakeEntryPoint("crashy", obj=DryRunCrash),
        ])
        assert reg.get("crashy") is None
        assert reg.get("never_existed") is None

    def test_host_never_crashes_even_if_all_fail(self):
        reg = _registry_with([
            FakeEntryPoint("a", load_exc=SyntaxError("bad code")),
            FakeEntryPoint("b", obj=BadShapeHintsNotDict),
            FakeEntryPoint("c", obj=InitCrash),
        ])
        assert reg.loaded == {}
        stages = [q.stage for q in reg.quarantined]
        assert stages == ["import", "shape", "dry_run"]


# ═══════════════ 2) المجموعة الفارغة ═══════════════

class TestEmptyGroup:
    def test_zero_plugins_yields_empty_registry_no_error(self):
        reg = _registry_with([])
        assert reg.loaded == {}
        assert reg.quarantined == []

    def test_real_default_entry_points_smoke(self):
        # الافتراضي هو importlib.metadata الحقيقي — بيئة الاختبار لا
        # تثبّت إضافات، فالاكتشاف الحقيقي يجب ألا يرمي شيئًا.
        reg = StrategyPluginRegistry()
        reg.discover()
        assert isinstance(reg.loaded, dict)
        assert isinstance(reg.quarantined, list)


# ═══════════════ 3) حالات إضافية للبوابة ═══════════════

class TestGateEdgeCases:
    def test_build_returning_none_is_dry_run_quarantine(self):
        reg = _registry_with([FakeEntryPoint("noneplan", obj=DryRunNone)])
        assert reg.loaded == {}
        (q,) = reg.quarantined
        assert (q.stage, q.name) == ("dry_run", "noneplan")
        assert "None" in q.reason

    def test_non_class_object_is_shape_quarantine(self):
        reg = _registry_with([
            FakeEntryPoint("func", obj=lambda: {"steps": []}),
        ])
        (q,) = reg.quarantined
        assert q.stage == "shape"
        assert "expected a class" in q.reason

    def test_duplicate_name_first_valid_wins(self):
        class SecondGood(GoodStrategy):
            pass
        reg = _registry_with([
            FakeEntryPoint("dup", obj=GoodStrategy),
            FakeEntryPoint("dup", obj=SecondGood),
        ])
        assert reg.get("dup") is GoodStrategy
        (q,) = reg.quarantined
        assert (q.name, q.stage) == ("dup", "shape")
        assert "duplicate" in q.reason

    def test_init_crash_is_dry_run_stage(self):
        reg = _registry_with([FakeEntryPoint("boom", obj=InitCrash)])
        (q,) = reg.quarantined
        assert q.stage == "dry_run"
        assert q.reason.startswith("ValueError:")


# ═══════════════ 4) دورة الحياة + الكشف الدفاعي ═══════════════

class TestLifecycle:
    def test_discover_is_idempotent_by_reset(self):
        calls = []

        def eps(*, group):
            calls.append(group)
            return [FakeEntryPoint("good", obj=GoodStrategy),
                    FakeEntryPoint("bad", obj=BadShapeNoBuild)]

        reg = StrategyPluginRegistry(entry_points_fn=eps)
        reg.discover()
        reg.discover()
        assert len(calls) == 2
        # لا تراكم: نفس الحجم بعد نداءين.
        assert list(reg.loaded) == ["good"]
        assert len(reg.quarantined) == 1

    def test_exposed_views_are_defensive_copies(self):
        reg = _registry_with([FakeEntryPoint("good", obj=GoodStrategy)])
        loaded_view = reg.loaded
        loaded_view["evil"] = object
        assert "evil" not in reg.loaded
        q_view = reg.quarantined
        q_view.append(QuarantineRecord("x", "shape", "fake"))
        assert reg.quarantined == []

    def test_quarantine_record_to_dict_serializable(self):
        rec = QuarantineRecord("p", "import", "ImportError: nope")
        payload = json.dumps(rec.to_dict())
        assert json.loads(payload) == {
            "name": "p", "stage": "import",
            "reason": "ImportError: nope"}


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-v"]))
