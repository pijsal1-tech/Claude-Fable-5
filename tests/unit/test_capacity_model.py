# -*- coding: utf-8 -*-
"""T-038 (R-403): CapacityModel — سعة صادقة من حالة pool + قواطع T-037.

يغطي:
- خصائص السعة (property tests): الإجمالي = مجموع مساهمات الأصحاء فقط؛
  مزود قاطعه OPEN يساهم بصفر؛ فشل الاستعلام (-1) يساهم بصفر ويرفع
  estimated؛ sentinel «غير المحدود» (999) يرفع estimated؛ الأرقام
  الدقيقة لا ترفعه.
- تتبع أرقام إطار الحالة: /api/capacity عبر Flask test client —
  الأرقام المعروضة مشتقة حرفياً من report() نفسه.
- بوابة grep: لا حساب MIN_ACCOUNTS ثابت في كود الإنتاج
  (T-036 نقلها للـ config؛ هنا نثبّت عدم عودتها — بند قبول T-038).
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from providers.capacity import (  # noqa: E402
    UNLIMITED_SENTINEL,
    CapacityModel,
    CapacityReport,
    ProviderCapacity,
)
from providers.pool import CircuitBreaker, ProviderPool  # noqa: E402
from tests.fakes.fake_provider import FakeProvider  # noqa: E402


# ═══════════════ أدوات ═══════════════

class _CountedProvider(FakeProvider):
    """FakeProvider مع عدّاد remaining_calls قابل للتعيين."""

    def __init__(self, remaining: int, **kw):
        super().__init__(**kw)
        self._remaining = remaining

    def get_remaining_calls(self) -> int:
        if isinstance(self._remaining, Exception):
            raise self._remaining
        return self._remaining


def _pool_with(providers: dict[str, int | Exception],
               threshold: int = 1):
    """Pool بساعة وهمية — يرجع (pool, now, المزودون)."""
    now = [0.0]
    pool = ProviderPool(breaker_factory=lambda: CircuitBreaker(
        failure_threshold=threshold, cooldown_base_s=30.0,
        clock=lambda: now[0]))
    provs = {}
    for name, remaining in providers.items():
        p = _CountedProvider(remaining, default_response=name.upper())
        pool.add(name, p)
        provs[name] = p
    return pool, now, provs


# ═══════════════ 1) خصائص السعة ═══════════════

class TestCapacityProperties:

    def test_total_is_sum_of_healthy_effective_calls(self):
        pool, _, _ = _pool_with({"use_ai": 3, "genspark": 5})
        report = CapacityModel(pool).report()
        assert report.total_available == 8
        assert report.healthy_count == 2
        assert report.estimated is False  # أرقام دقيقة < sentinel

    def test_open_breaker_zeroes_contribution(self):
        pool, _, provs = _pool_with({"use_ai": 3, "genspark": 5},
                                    threshold=1)
        provs["use_ai"].fail_always = RuntimeError("down")
        text, name = pool.send_with_fallback("hi")  # use_ai يفشل → قاطعه OPEN
        assert name == "genspark"

        report = CapacityModel(pool).report()
        by_name = {p.name: p for p in report.providers}
        assert by_name["use_ai"].healthy is False
        assert by_name["use_ai"].breaker_state == "open"
        assert by_name["use_ai"].effective_calls == 0  # رغم remaining=3
        assert by_name["use_ai"].remaining_calls == 3  # الخام محفوظ للتتبع
        assert report.total_available == 5             # genspark فقط
        assert report.healthy_count == 1

    def test_recovery_restores_contribution(self):
        """التعافي عبر القاطع (T-037) يعيد السعة تلقائياً — بلا restart."""
        pool, now, provs = _pool_with({"use_ai": 3, "genspark": 5},
                                      threshold=1)
        provs["use_ai"].fail_always = RuntimeError("down")
        pool.send_with_fallback("hi")
        assert CapacityModel(pool).report().total_available == 5

        provs["use_ai"].fail_always = None
        now[0] += 30.0  # انقضى الـ cooldown → HALF_OPEN = صحي
        report = CapacityModel(pool).report()
        assert report.total_available == 8  # عاد للمجموع
        by_name = {p.name: p for p in report.providers}
        assert by_name["use_ai"].breaker_state == "half_open"
        assert by_name["use_ai"].healthy is True

    def test_query_failure_is_zero_and_estimated(self):
        pool, _, _ = _pool_with({"use_ai": RuntimeError("api err"),
                                 "genspark": 5})
        report = CapacityModel(pool).report()
        by_name = {p.name: p for p in report.providers}
        # get_pool_status يحوّل فشل get_remaining_calls إلى -1
        assert by_name["use_ai"].remaining_calls == -1
        assert by_name["use_ai"].effective_calls == 0
        assert by_name["use_ai"].estimated is True
        assert report.total_available == 5
        assert report.estimated is True  # مزود صحي رقمه مجهول

    def test_unlimited_sentinel_is_estimated(self):
        """999 الافتراضي من BaseProvider = خيال معلن لا قياس."""
        pool, _, _ = _pool_with({"deepseek": UNLIMITED_SENTINEL})
        report = CapacityModel(pool).report()
        assert report.total_available == UNLIMITED_SENTINEL
        assert report.estimated is True

    def test_unhealthy_estimate_does_not_taint_flag(self):
        """غير الصحي مساهمته صفر بالتعريف — تقديريته لا تلوّث العلم."""
        pool, _, provs = _pool_with(
            {"use_ai": UNLIMITED_SENTINEL, "genspark": 5}, threshold=1)
        provs["use_ai"].fail_always = RuntimeError("down")
        pool.send_with_fallback("hi")  # use_ai → OPEN
        report = CapacityModel(pool).report()
        assert report.total_available == 5
        assert report.estimated is False  # المساهم الوحيد (genspark) دقيق

    def test_empty_pool_and_none_pool(self):
        assert CapacityModel(ProviderPool()).report().total_available == 0
        report = CapacityModel(None).report()
        assert report == CapacityReport()
        assert report.total_available == 0
        assert report.estimated is False

    def test_report_is_pure_no_side_effects(self):
        pool, _, provs = _pool_with({"use_ai": 3})
        model = CapacityModel(pool)
        r1, r2 = model.report(), model.report()
        assert r1 == r2                       # frozen dataclass تساوٍ قيمي
        assert provs["use_ai"].call_count == 0  # لا send/stream أُطلق

    def test_monotonicity_more_failures_never_increase_capacity(self):
        """خاصية: كل فشل إضافي لا يزيد السعة أبداً."""
        pool, _, provs = _pool_with({"use_ai": 3, "genspark": 5},
                                    threshold=2)
        provs["use_ai"].fail_always = RuntimeError("down")
        model = CapacityModel(pool)
        totals = [model.report().total_available]
        for _ in range(3):
            pool.send_with_fallback("x")  # use_ai يفشل ثم genspark ينجح
            totals.append(model.report().total_available)
        assert all(b <= a for a, b in zip(totals, totals[1:])), totals
        assert totals[-1] == 5  # القاطع فُتح في الطريق

    def test_to_dict_traceable_fields(self):
        pool, _, _ = _pool_with({"use_ai": 3})
        d = CapacityModel(pool).report().to_dict()
        assert d["total_available"] == 3
        assert d["healthy_count"] == 1
        assert d["estimated"] is False
        (p,) = d["providers"]
        assert p == {"name": "use_ai", "healthy": True,
                     "breaker_state": "closed", "remaining_calls": 3,
                     "effective_calls": 3, "estimated": False}


# ═══════════════ 2) تتبع أرقام إطار الحالة ═══════════════

class TestStatusFrameIntegration:

    def test_api_capacity_numbers_traceable_to_model(self, monkeypatch):
        """أرقام /api/capacity == report().to_dict() حرفياً."""
        import server
        pool, _, provs = _pool_with({"use_ai": 3, "genspark": 5},
                                    threshold=1)
        provs["use_ai"].fail_always = RuntimeError("down")
        pool.send_with_fallback("hi")  # use_ai → OPEN

        model = CapacityModel(pool)
        monkeypatch.setattr(server, "capacity_model", model)

        body = server.app.test_client().get("/api/capacity").get_json()
        assert body["ok"] is True
        assert body["capacity"] == model.report().to_dict()  # تتبع كامل
        assert body["capacity"]["total_available"] == 5

    def test_api_capacity_503_before_boot(self, monkeypatch):
        import server
        monkeypatch.setattr(server, "capacity_model", None)
        resp = server.app.test_client().get("/api/capacity")
        assert resp.status_code == 503
        assert resp.get_json()["ok"] is False


# ═══════════════ 3) بوابة grep — لا MIN_ACCOUNTS ثابتة ═══════════════

class TestMinAccountsGone:

    def test_grep_gate_no_hardcoded_min_accounts(self):
        """بند القبول (T-038): ثوابت MIN_ACCOUNTS الصلبة غير موجودة —
        (حُذفت في T-036 لصالح config؛ هذا يثبّت عدم عودتها)."""
        cmd = ["grep", "-rn", "--include=*.py",
               "-e", "MIN_ACCOUNTS",
               "chain/", "core/", "providers/", "context/",
               "sessions/", "routes/", "server.py"]  # TSK-613: +routes/
        proc = subprocess.run(cmd, cwd=REPO_ROOT,
                              capture_output=True, text=True)
        assert proc.returncode == 1, (
            f"ثوابت MIN_ACCOUNTS عادت لكود الإنتاج:\n{proc.stdout}")
