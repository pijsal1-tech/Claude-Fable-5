# -*- coding: utf-8 -*-
"""
TSK-608 (RF-02 §R5) — تفعيل ExecutionRegistry.reap_stale إنتاجيًا.
Validates: TSK-608.

معيار القبول الحرفي: محاكاة تذكرة يتيمة (خيط مات بلا finish) → run
جديد لنفس المشروع يُقبل بعد TTL؛ لا reap لتذاكر حية (تنبض).
صفر نداءات AI خارجية — ساعة مزيفة وسجل محقون.
"""
import json

import pytest

import server
from core.app_context import ProjectHandle
from core.backends import (
    DEFAULT_STALE_TTL_SECONDS,
    backends_from_config,
    resolve_stale_ttl,
)
from core.execution import ExecutionRegistry
from core.session_context import SessionContext


class FakeClock:
    """ساعة قابلة للتقديم اليدوي — نفس نمط tests/unit/test_execution.py."""

    def __init__(self, start: float = 1000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _sctx_for(root) -> tuple[SessionContext, list]:
    frames: list = []
    send = lambda m: frames.append(json.loads(json.dumps(m, ensure_ascii=False)))
    sctx = SessionContext(send=send,
                          project=ProjectHandle(root=str(root)))
    return sctx, frames


# ═══════════ 1) درزة الإعداد: resolve_stale_ttl ═══════════


class TestResolveStaleTTL:
    def test_missing_section_gives_default(self):
        assert resolve_stale_ttl(None) == DEFAULT_STALE_TTL_SECONDS
        assert resolve_stale_ttl({}) == DEFAULT_STALE_TTL_SECONDS
        assert resolve_stale_ttl("not-a-dict") == DEFAULT_STALE_TTL_SECONDS

    def test_explicit_null_disables(self):
        assert resolve_stale_ttl({"stale_ttl_seconds": None}) is None

    def test_positive_number_passes_through(self):
        assert resolve_stale_ttl({"stale_ttl_seconds": 30}) == 30.0
        assert resolve_stale_ttl({"stale_ttl_seconds": 0.5}) == 0.5

    @pytest.mark.parametrize("bad", [0, -1, "900", True, [], {}])
    def test_invalid_is_loud(self, bad):
        with pytest.raises(ValueError):
            resolve_stale_ttl({"stale_ttl_seconds": bad})

    def test_factory_forwards_ttl(self):
        pair = backends_from_config("memory", ttl_seconds=42.0)
        assert pair.registry._ttl == 42.0

    def test_server_registry_has_ttl_enabled(self):
        """config.yaml الحي يفعّل TTL على سجل الخادم (لا None بعد TSK-608)."""
        assert server._backends.registry._ttl is not None
        assert server._backends.registry._ttl > 0


# ═══════════ 2) معيار القبول: اليتيمة تُحصد والحية لا ═══════════


class TestAcceptCriterion:
    def _wire(self, monkeypatch, tmp_path, ttl=30.0):
        clock = FakeClock(1000.0)
        reg = ExecutionRegistry(ttl_seconds=ttl, clock=clock)
        monkeypatch.setattr(server, "execution_registry", reg)
        sctx, frames = _sctx_for(tmp_path)
        return reg, clock, sctx, frames

    def test_orphan_ticket_frees_slot_after_ttl(self, monkeypatch, tmp_path):
        """يتيمة (خيط مات بلا finish) → run جديد لنفس المشروع يُقبل بعد TTL."""
        reg, clock, sctx, frames = self._wire(monkeypatch, tmp_path)

        orphan = server._begin_run_ticket("chain", sctx.send, sctx=sctx)
        assert orphan is not None
        # الخيط "مات": لا heartbeat ولا finish. قبل TTL → busy (السلوك القديم)
        clock.advance(20)
        assert server._begin_run_ticket("chain", sctx.send, sctx=sctx) is None
        assert frames[-1]["type"] == "busy"

        # بعد TTL → الحصاد يحرر الخانة والتسجيل الجديد يُقبل
        clock.advance(15)   # صمت كلي 35s > 30s TTL
        replacement = server._begin_run_ticket("chain", sctx.send, sctx=sctx)
        assert replacement is not None
        assert orphan.state == "failed"
        assert orphan.cancel_reason.startswith("stale")
        assert replacement.state == "running"

    def test_live_ticket_is_not_reaped(self, monkeypatch, tmp_path):
        """تذكرة تنبض لا تُحصد مهما طال الزمن — busy يبقى صادقًا."""
        reg, clock, sctx, frames = self._wire(monkeypatch, tmp_path)

        live = server._begin_run_ticket("chain", sctx.send, sctx=sctx)
        assert live is not None
        for _ in range(5):
            clock.advance(20)          # 5 × 20s = 100s إجمالًا > TTL
            assert live.heartbeat() is True
        assert server._begin_run_ticket("chain", sctx.send, sctx=sctx) is None
        assert frames[-1]["type"] == "busy"
        assert live.state == "running"

    def test_reap_is_noop_when_ttl_disabled(self, monkeypatch, tmp_path):
        """null صريح (تعطيل) = سلوك ما قبل TSK-608 حرفيًا: busy للأبد."""
        reg, clock, sctx, frames = self._wire(monkeypatch, tmp_path, ttl=None)

        orphan = server._begin_run_ticket("chain", sctx.send, sctx=sctx)
        assert orphan is not None
        clock.advance(10_000)
        assert server._begin_run_ticket("chain", sctx.send, sctx=sctx) is None
        assert frames[-1]["type"] == "busy"
        assert orphan.state == "running"


# ═══════════ 3) نبض الحياة: المحوّل ومسار الدفعة ═══════════


class TestHeartbeatWiring:
    def test_adapter_emit_heartbeats_ticket(self, monkeypatch, tmp_path):
        """كل حدث عبر _RunnerWSAdapter = نبضة — run حي يبث لا يُحصد."""
        clock = FakeClock(1000.0)
        reg = ExecutionRegistry(ttl_seconds=30.0, clock=clock)
        monkeypatch.setattr(server, "execution_registry", reg)

        ticket = reg.register("direct", "proj-hb")
        sink = server._RunnerWSAdapter(lambda m: None)
        from core.runner import RunEvent

        clock.advance(25)
        sink.emit(RunEvent(type="chunk_evt", run_id=ticket.run_id,
                           seq=0, data={"text": "قطعة"}))
        assert ticket.last_heartbeat == clock.now   # نُبض
        clock.advance(25)                            # 50s منذ الإنشاء لكن 25s منذ النبضة
        assert reg.reap_stale() == []
        assert ticket.state == "running"

    def test_adapter_emit_unknown_run_id_is_safe(self, monkeypatch):
        """حدث بـ run_id مجهول (سجل محقون في اختبار آخر) → لا انفجار."""
        reg = ExecutionRegistry()
        monkeypatch.setattr(server, "execution_registry", reg)
        sink = server._RunnerWSAdapter(lambda m: None)
        from core.runner import RunEvent
        sink.emit(RunEvent(type="x_evt", run_id="missing", seq=0, data={}))

    def test_apply_batch_heartbeats_per_action(self, monkeypatch, tmp_path):
        """_apply_batch ينبض لكل action — دفعة طويلة حية لا تُحصد."""
        clock = FakeClock(1000.0)
        reg = ExecutionRegistry(ttl_seconds=30.0, clock=clock)
        monkeypatch.setattr(server, "execution_registry", reg)
        sctx, frames = _sctx_for(tmp_path)

        beats: list[float] = []

        def _slow_action(action, _sctx):
            beats.append(clock.now)
            clock.advance(20)        # كل action أبطأ من ثلثي الـ TTL
            return {"ok": True, "message": ""}

        monkeypatch.setattr(server, "_apply_single_action", _slow_action)
        actions = [{"type": "create_file", "path": f"f{i}.txt", "content": ""}
                   for i in range(4)]
        server._apply_batch(sctx, actions)   # 4 × 20s = 80s إجمالًا > TTL

        assert len(beats) == 4               # كل الإجراءات نُفذت — لم يُحصد
        done = [f for f in frames if f["type"] == "all_actions_done"]
        assert done and done[0]["total"] == 4
        tickets = reg.list_all()
        assert len(tickets) == 1 and tickets[0].state == "completed"
