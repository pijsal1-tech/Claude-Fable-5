# -*- coding: utf-8 -*-
"""TSK-729a/b — تصليب درز Redis (FI-04 مُكيَّفة بقرار D-11/IR-1).

729a — توافق فوق fakeredis: عدة T-108 (EventBusBackendContractMixin)
ودورة قائمة العمل كاملة تعملان في **كل بوابة محلية** بلا خدمة Redis —
قبل هذا كانت اختبارات التوافق (needs_redis) تُتخطى محليًا دائمًا.
fakeredis اختياري (import-or-skip): غيابه لا يكسر البوابة.

729b — حارس عدم التسرّب: الإقلاع الافتراضي (dispatch: in-proc) لا
يلمس redis إطلاقًا — فحص بنيوي على server.py + فحص تشغيلي على
sys.modules.

ملاحظة نطاق (D-11): هذا **ليس** تفعيلًا لمعمارية worker (تتعارض مع
IR-1) — تصليب عقد الدرز القائم فقط.
"""
from __future__ import annotations

import pathlib
import sys
import uuid

import pytest

from core.events import StepProgress
from tests.unit.test_backends import EventBusBackendContractMixin

ROOT = pathlib.Path(__file__).resolve().parents[2]

fakeredis = pytest.importorskip(
    "fakeredis", reason="fakeredis غير مثبت — تثبَّت عبر requirements-dev")


def _fake_client():
    """عميل مزيف مطابق لعقد redis_client_from_env (decode_responses)."""
    return fakeredis.FakeRedis(decode_responses=True)


# ═══════════ 729a-1: عدة توافق T-108 فوق fakeredis ═══════════


class TestFakeRedisEventBusConformance(EventBusBackendContractMixin):
    """نفس العدة حرفيًا — فقط make_bus فوق العميل المزيف.

    تُثبت أن عقد الناقل (pub/sub، العزل، FIFO لكل run، التاريخ)
    محروس محليًا في كل بوابة، لا في CI فقط.
    """

    def make_bus(self):
        from core.backends_redis import RedisEventBusBackend
        return RedisEventBusBackend(
            client=_fake_client(),
            stream_prefix=f"t729:{uuid.uuid4().hex}:")


# ═══════════ 729a-2: إعادة القراءة المرتبة والسقف ═══════════


class TestFakeRedisOrderedReplay:

    def test_history_matches_emission_order(self):
        from core.backends_redis import RedisEventBusBackend
        bus = RedisEventBusBackend(
            client=_fake_client(), stream_prefix=f"t729:{uuid.uuid4().hex}:")
        for i in range(20):
            bus.publish(StepProgress(run_id="rX", frame_type="chunk",
                                     payload={"seq": i}))
        replay = bus.history("rX")
        assert [e.payload["seq"] for e in replay] == list(range(20))

    def test_replay_visible_from_second_backend_same_client(self):
        """backend ثانٍ فوق نفس العميل يرى نفس التسلسل — جوهر عبور
        العمليات في R-804 (هنا العميل المشترك يحاكي الخادم المشترك)."""
        from core.backends_redis import RedisEventBusBackend
        client = _fake_client()
        prefix = f"t729:{uuid.uuid4().hex}:"
        writer = RedisEventBusBackend(client=client, stream_prefix=prefix)
        reader = RedisEventBusBackend(client=client, stream_prefix=prefix)
        for i in range(5):
            writer.publish(StepProgress(run_id="rY", frame_type="x",
                                        payload={"seq": i}))
        assert [e.payload["seq"] for e in reader.history("rY")] \
            == list(range(5))

    def test_history_cap_keeps_latest(self):
        from core.backends_redis import RedisEventBusBackend
        bus = RedisEventBusBackend(
            client=_fake_client(),
            stream_prefix=f"t729:{uuid.uuid4().hex}:",
            history_per_run=3)
        for i in range(6):
            bus.publish(StepProgress(run_id="rZ", frame_type="x",
                                     payload={"i": i}))
        assert [e.payload["i"] for e in bus.history("rZ")] == [3, 4, 5]


# ═══════════ 729a-3: دورة قائمة العمل كاملة ═══════════


class TestFakeRedisWorkQueue:

    def _queue(self, client=None):
        from core.backends_redis import RedisWorkQueue
        return RedisWorkQueue(client=client or _fake_client(),
                              stream=f"t729:wq:{uuid.uuid4().hex}")

    def test_enqueue_claim_ack_lifecycle(self):
        q = self._queue()
        q.enqueue({"run_id": "r1", "kind": "chain"})
        got = q.claim("worker-a")
        assert len(got) == 1
        assert got[0].payload == {"run_id": "r1", "kind": "chain"}
        assert q.pending_count() == 1
        assert q.ack(got[0].entry_id) == 1
        assert q.pending_count() == 0

    def test_killed_consumer_entry_is_reclaimed(self):
        q = self._queue()
        q.enqueue({"run_id": "r2", "kind": "agent"})
        victim = q.claim("worker-a")           # استلم ولم يؤكّد (انهيار)
        rescued = q.reclaim("worker-b", min_idle_ms=0)
        assert [e.entry_id for e in rescued] == [victim[0].entry_id]
        assert q.ack(rescued[0].entry_id) == 1
        assert q.pending_count() == 0

    def test_reclaim_respects_min_idle(self):
        q = self._queue()
        q.enqueue({"run_id": "r3", "kind": "direct"})
        q.claim("worker-a")
        assert q.reclaim("worker-b", min_idle_ms=60_000) == []
        assert q.pending_count() == 1

    def test_claim_returns_empty_when_no_work(self):
        assert self._queue().claim("worker-a") == []

    def test_group_creation_is_idempotent(self):
        from core.backends_redis import RedisWorkQueue
        client = _fake_client()
        stream = f"t729:wq:{uuid.uuid4().hex}"
        RedisWorkQueue(client=client, stream=stream)
        RedisWorkQueue(client=client, stream=stream)   # لا استثناء


# ═══════════ 729b: حارس عدم التسرّب للإقلاع الافتراضي ═══════════


class TestDefaultBootNoRedisLeak:
    """dispatch: in-proc (الافتراضي) ⇒ صفر لمس لredis — محروس آليًا."""

    SERVER_SRC = (ROOT / "server.py").read_text(encoding="utf-8")

    def test_no_top_level_backends_redis_import_in_server(self):
        """كل ذكر backends_redis في server.py داخل دوال (مسافة بادئة)
        — لا استيراد علوي يجعل redis شرط إقلاع."""
        offenders = [
            ln for ln in self.SERVER_SRC.splitlines()
            if ln.startswith(("import core.backends_redis",
                              "from core.backends_redis"))
        ]
        assert offenders == [], f"استيراد علوي: {offenders}"

    def test_backends_redis_mentions_are_worker_gated(self):
        """كل استيراد backends_redis في server.py يقع بعد فحص
        _dispatch_mode == "worker" داخل نفس الدالة (فحص جواري:
        الأسطر الخمسة السابقة تحوي الحارس)."""
        lines = self.SERVER_SRC.splitlines()
        for i, ln in enumerate(lines):
            if "backends_redis" in ln and "import" in ln:
                window = "\n".join(lines[max(0, i - 5):i])
                assert '_dispatch_mode == "worker"' in window, (
                    f"سطر {i+1}: استيراد backends_redis غير محروس "
                    f"بفرع worker")

    def test_importing_server_does_not_import_redis(self):
        """فحص تشغيلي: استيراد server (config الافتراضي in-proc)
        لا يضع **redis** في sys.modules.

        ملاحظة عقدية: core.backends_redis نفسه قد يُحمَّل (worker.py
        يستورده علويًا لدرزة T-110) — وهذا آمن بالبناء لأن T-109 يضمن
        صفر ``import redis`` علوي فيه (محروس في
        tests/integration/test_redis_backends.py). معيار التسرّب
        الفعلي = تحميل مكتبة redis ذاتها.

        الفحص في subprocess معزول: fakeredis (المستورد أعلى هذا
        الملف) يستورد redis بنفسه فيلوث sys.modules هنا."""
        import subprocess
        code = (
            "import sys; import server; "
            "sys.exit(1 if 'redis' in sys.modules else 0)"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, (
            "مكتبة redis حُمّلت رغم dispatch الافتراضي in-proc: "
            f"{proc.stderr[-300:]}")

    def test_default_dispatch_is_in_proc(self):
        from worker import DEFAULT_DISPATCH
        assert DEFAULT_DISPATCH == "in-proc"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
