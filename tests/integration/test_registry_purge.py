# -*- coding: utf-8 -*-
"""
QA-T10 (جزء TSK-303) — طَهْر تذاكر terminal من السجل (NF-06).
Validates: TSK-303.

معيار القبول الحرفي: 500 run متتابع → ``len(list_all())`` مسقوف؛
``_list_runs_frame`` سليم. التذاكر النشطة لا تُحذف أبدًا.
صفر نداءات AI خارجية — كل شيء داخل tmp_path/سجل نظيف.
"""
import json

import pytest

import server
from core.app_context import ProjectHandle
from core.execution import ExecutionRegistry, TERMINAL_STATES
from core.session_context import SessionContext


class FakeWS:
    def __init__(self):
        self.sent = []

    def send(self, payload: str):
        self.sent.append(payload)


@pytest.fixture(autouse=True)
def fresh_registry(monkeypatch):
    reg = ExecutionRegistry()
    monkeypatch.setattr(server, "execution_registry", reg)
    return reg


def _sctx_for(root) -> tuple[SessionContext, FakeWS]:
    ws = FakeWS()
    send = lambda m: ws.send(json.dumps(m, ensure_ascii=False))
    sctx = SessionContext(send=send,
                          project=ProjectHandle(root=str(root)))
    return sctx, ws


class TestAcceptCriterion:
    """معيار القبول الحرفي: 500 run متتابع → list_all مسقوف + frame سليم."""

    def test_500_sequential_runs_list_all_capped(self, fresh_registry,
                                                 tmp_path):
        (tmp_path / "p").mkdir()
        sctx, ws = _sctx_for(tmp_path / "p")
        for _ in range(500):
            t = server._begin_run_ticket("chain", sctx.send, sctx=sctx)
            assert t is not None  # الخانة تتحرر كل مرة — لا busy
            fresh_registry.finish(t.run_id, "completed")
        # السقف: keep_last الافتراضي (50) + ما قد يُسجَّل بعد آخر طَهْر
        assert len(fresh_registry.list_all()) <= 51
        assert ws.sent == []  # لا إطارات busy على الإطلاق

    def test_list_runs_frame_valid_after_purge(self, fresh_registry,
                                               tmp_path):
        (tmp_path / "p").mkdir()
        sctx, _ = _sctx_for(tmp_path / "p")
        for _ in range(120):
            t = server._begin_run_ticket("chain", sctx.send, sctx=sctx)
            fresh_registry.finish(t.run_id, "completed")
        frame = server._list_runs_frame()
        assert frame["type"] == "runs_list"
        assert isinstance(frame["runs"], list)
        assert 0 < len(frame["runs"]) <= 51
        for entry in frame["runs"]:
            for key in ("id", "mode", "state", "started_at",
                        "is_cancelled", "cancel_reason", "finished_at"):
                assert key in entry
        # الإطار قابل للتسلسل JSON (عقد الإرسال)
        json.dumps(frame, ensure_ascii=False)


class TestPurgeSemantics:
    """دلالات purge_terminal نفسها (وحدويًّا على السجل)."""

    def _fill_terminal(self, reg, n, status="completed"):
        ids = []
        for i in range(n):
            t = reg.register("chain", f"proj-{i}")  # مشاريع مختلفة — لا busy
            reg.finish(t.run_id, status)
            ids.append(t.run_id)
        return ids

    def test_running_tickets_never_purged(self, fresh_registry):
        active = [fresh_registry.register("chain", f"act-{i}").run_id
                  for i in range(5)]
        self._fill_terminal(fresh_registry, 20)
        deleted = fresh_registry.purge_terminal(keep_last=0)
        assert deleted == 20
        remaining = {t.run_id for t in fresh_registry.list_all()}
        assert set(active) <= remaining  # كل النشطة باقية
        assert len(remaining) == 5

    def test_keep_last_zero_deletes_all_terminal(self, fresh_registry):
        self._fill_terminal(fresh_registry, 7)
        assert fresh_registry.purge_terminal(keep_last=0) == 7
        assert fresh_registry.list_all() == []

    def test_negative_keep_last_raises(self, fresh_registry):
        with pytest.raises(ValueError):
            fresh_registry.purge_terminal(keep_last=-1)

    def test_oldest_first_and_return_count(self, fresh_registry):
        ids = self._fill_terminal(fresh_registry, 10)
        deleted = fresh_registry.purge_terminal(keep_last=3)
        assert deleted == 7
        remaining = [t.run_id for t in fresh_registry.list_all()]
        assert remaining == ids[-3:]  # الأحدث إنشاءً هي الباقية، بترتيبها

    def test_noop_when_under_cap(self, fresh_registry):
        self._fill_terminal(fresh_registry, 3)
        assert fresh_registry.purge_terminal(keep_last=50) == 0
        assert len(fresh_registry.list_all()) == 3

    def test_all_terminal_states_are_purgeable(self, fresh_registry):
        for i, status in enumerate(TERMINAL_STATES):
            t = fresh_registry.register("chain", f"st-{i}")
            fresh_registry.finish(t.run_id, status)
        assert fresh_registry.purge_terminal(keep_last=0) == len(
            TERMINAL_STATES)
        assert fresh_registry.list_all() == []

    def test_active_slot_integrity_after_purge(self, fresh_registry):
        """الطَهْر لا يمس خانة _active_by_project — نفس المشروع يبقى busy."""
        from core.execution import RunBusyError
        t_act = fresh_registry.register("chain", "proj-x")
        self._fill_terminal(fresh_registry, 60)
        fresh_registry.purge_terminal()
        with pytest.raises(RunBusyError):
            fresh_registry.register("chain", "proj-x")  # ما زالت محجوزة
        fresh_registry.finish(t_act.run_id, "completed")
        assert fresh_registry.register("chain", "proj-x") is not None
