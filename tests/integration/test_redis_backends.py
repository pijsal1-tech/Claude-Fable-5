# -*- coding: utf-8 -*-
"""T-109 (R-804): Redis Backends عبر Streams — أدلة القبول.

Acceptance Criteria (حرفيًّا):
- conformance suite from T-108 passes on Redis backends —
  `EventBusBackendContractMixin` تُورَّث كما هي فوق Redis حقيقي.
- ordered replay of an event stream matches emission order —
  ``history`` تقرأ من الـ stream وتطابق ترتيب النشر، حتى من
  «عملية» أخرى (backend ثانٍ بنفس البادئة).
- queue entry from a killed consumer is reclaimed — worker يستلم
  ولا يؤكّد (يُحاكي الانهيار) ⇒ XAUTOCLAIM ينقل مدخلته لآخر.
- no ``redis`` import without the extra installed — grep على
  الاستيرادات العلوية + استيراد الموديول لا يمس redis.

كل الاختبارات ضد Redis **حقيقي** (service container في CI؛ محليًّا
skip-إن-غاب — نفس نمط pytest.mark.skipif). العزل بمفاتيح uuid لكل
اختبار — لا flushdb (لا نمس بيانات نسخة مشتركة).
"""
from __future__ import annotations

import pathlib
import sys
import uuid

import pytest

from core.events import StepProgress
from tests.unit.test_backends import EventBusBackendContractMixin

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _redis_available() -> bool:
    try:
        import redis
        redis.Redis.from_url("redis://localhost:6379/0",
                             socket_connect_timeout=1).ping()
        return True
    except Exception:
        return False


REDIS_UP = _redis_available()
needs_redis = pytest.mark.skipif(
    not REDIS_UP, reason="Redis غير متاح محليًّا — يعمل في CI (service)")


def _client():
    from core.backends_redis import redis_client_from_env
    return redis_client_from_env("redis://localhost:6379/0")


# ═══════════ 1) بند القبول: extra اختياري ═══════════


class TestOptionalDependencyGuard:
    """يعمل **بلا** Redis — يفحص الشيفرة لا الخدمة."""

    def test_no_top_level_redis_import(self):
        """grep: كل ``import redis`` داخل دوال/أصناف (مسافة بادئة) —
        صفر استيراد علوي (نفس نمط بوابات check.sh)."""
        src = (ROOT / "core" / "backends_redis.py").read_text(
            encoding="utf-8")
        top_level = [
            ln for ln in src.splitlines()
            if ln.startswith(("import redis", "from redis"))
        ]
        assert top_level == [], f"استيراد redis علوي: {top_level}"

    def test_module_import_does_not_touch_redis(self):
        """استيراد الموديول لا يستورد redis — الكسل مُثبَت تشغيليًّا."""
        for mod in ("core.backends_redis", "redis"):
            sys.modules.pop(mod, None)
        import core.backends_redis  # noqa: F401
        assert "redis" not in sys.modules
        # تنظيف: لا نترك نسخة الموديول بلا redis محمَّلة للاختبارات التالية
        sys.modules.pop("core.backends_redis", None)

    def test_memory_backends_module_untouched(self):
        """انحدار T-108: backends.py لا يستورد Redis إطلاقًا (ذكره
        في التوثيق كنقطة توسعة مسموح — الاستيراد هو الممنوع)."""
        src = (ROOT / "core" / "backends.py").read_text(encoding="utf-8")
        importing = [
            ln for ln in src.splitlines()
            if "import" in ln and "redis" in ln.lower()
        ]
        assert importing == [], f"استيراد redis في backends.py: {importing}"


# ═══════════ 2) عدة توافق T-108 فوق Redis حقيقي ═══════════


@needs_redis
@pytest.mark.integration
class TestRedisEventBusConformance(EventBusBackendContractMixin):
    """بند القبول: نفس العدة، صفر اختبارات مكررة — فقط make_bus."""

    def make_bus(self):
        from core.backends_redis import RedisEventBusBackend
        return RedisEventBusBackend(
            client=_client(), stream_prefix=f"t109:{uuid.uuid4().hex}:")


# ═══════════ 3) بند القبول: إعادة قراءة مرتبة ═══════════


@needs_redis
@pytest.mark.integration
class TestOrderedReplay:

    def test_history_matches_emission_order(self):
        from core.backends_redis import RedisEventBusBackend
        prefix = f"t109:{uuid.uuid4().hex}:"
        bus = RedisEventBusBackend(client=_client(), stream_prefix=prefix)
        for i in range(20):
            bus.publish(StepProgress(run_id="rX", frame_type="chunk",
                                     payload={"seq": i}))
        replay = bus.history("rX")
        assert [e.payload["seq"] for e in replay] == list(range(20))
        assert all(isinstance(e, StepProgress) for e in replay)

    def test_replay_visible_from_another_process_view(self):
        """backend ثانٍ (يحاكي عملية أخرى) يرى نفس التسلسل من Redis —
        هذا ما يعجز عنه داخل-العملية، وجوهر توزيع R-804."""
        from core.backends_redis import RedisEventBusBackend
        prefix = f"t109:{uuid.uuid4().hex}:"
        writer = RedisEventBusBackend(client=_client(),
                                      stream_prefix=prefix)
        reader = RedisEventBusBackend(client=_client(),
                                      stream_prefix=prefix)
        for i in range(5):
            writer.publish(StepProgress(run_id="rY", frame_type="x",
                                        payload={"seq": i}))
        assert [e.payload["seq"] for e in reader.history("rY")] \
            == list(range(5))

    def test_history_cap_keeps_latest(self):
        """MAXLEN دقيق — نفس دلالة سقف التاريخ داخل-العملية (الأحدث يبقى)."""
        from core.backends_redis import RedisEventBusBackend
        bus = RedisEventBusBackend(
            client=_client(),
            stream_prefix=f"t109:{uuid.uuid4().hex}:",
            history_per_run=3)
        for i in range(6):
            bus.publish(StepProgress(run_id="rZ", frame_type="x",
                                     payload={"i": i}))
        assert [e.payload["i"] for e in bus.history("rZ")] == [3, 4, 5]

    def test_unknown_kind_fails_loud(self):
        from core.backends_redis import _decode_event
        with pytest.raises(ValueError):
            _decode_event({"kind": "Mystery", "data": "{}"})


# ═══════════ 4) بند القبول: استعادة مدخلة worker منهار ═══════════


@needs_redis
@pytest.mark.integration
class TestWorkQueueReclaim:

    def _queue(self):
        from core.backends_redis import RedisWorkQueue
        return RedisWorkQueue(client=_client(),
                              stream=f"t109:wq:{uuid.uuid4().hex}")

    def test_enqueue_claim_ack_lifecycle(self):
        q = self._queue()
        q.enqueue({"run_id": "r1", "kind": "chain"})
        got = q.claim("worker-a")
        assert len(got) == 1
        assert got[0].payload == {"run_id": "r1", "kind": "chain"}
        assert q.pending_count() == 1          # مُستلَمة بلا ack
        assert q.ack(got[0].entry_id) == 1
        assert q.pending_count() == 0

    def test_killed_consumer_entry_is_reclaimed(self):
        """worker-a يستلم ثم «ينهار» (لا ack) ⇒ worker-b يستعيد
        المدخلة نفسها عبر XAUTOCLAIM ويكملها."""
        q = self._queue()
        q.enqueue({"run_id": "r2", "kind": "agent"})
        victim = q.claim("worker-a")
        assert len(victim) == 1                # استلمها ولم يؤكّد أبدًا

        rescued = q.reclaim("worker-b", min_idle_ms=0)
        assert [e.entry_id for e in rescued] == [victim[0].entry_id]
        assert rescued[0].payload == {"run_id": "r2", "kind": "agent"}
        assert q.ack(rescued[0].entry_id) == 1  # المنقذ يكملها
        assert q.pending_count() == 0

    def test_reclaim_respects_min_idle(self):
        """مدخلة نشطة (خمول 0ms < عتبة عالية) لا تُنتزع من صاحبها."""
        q = self._queue()
        q.enqueue({"run_id": "r3", "kind": "direct"})
        q.claim("worker-a")
        assert q.reclaim("worker-b", min_idle_ms=60_000) == []
        assert q.pending_count() == 1          # ما زالت لدى worker-a

    def test_claim_returns_empty_when_no_work(self):
        q = self._queue()
        assert q.claim("worker-a") == []

    def test_group_creation_is_idempotent(self):
        """بناء queue ثانٍ على نفس الـ stream = BUSYGROUP مبتلَع."""
        from core.backends_redis import RedisWorkQueue
        stream = f"t109:wq:{uuid.uuid4().hex}"
        RedisWorkQueue(client=_client(), stream=stream)
        RedisWorkQueue(client=_client(), stream=stream)   # لا استثناء
