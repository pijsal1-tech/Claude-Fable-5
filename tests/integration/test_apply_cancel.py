# -*- coding: utf-8 -*-
"""
QA-T10 (جزء TSK-304) — استجابة الإلغاء أثناء apply الطويل (NF-04).
Validates: TSK-304 · TSK-606.

معيار القبول الحرفي: ``cancel`` أثناء دفعة 20 ملفًا يوقفها قبل
اكتمالها — الإجراءات المتبقية لا تُطبَّق. fm بطيء مزيّف (fake slow fm)
يطلق الإلغاء منتصف الدفعة. صفر نداءات AI خارجية.

TSK-606: الدفعة صارت على خيط عامل (runner-apply-batch) — إطار
``cancel_run`` من **نفس الاتصال** يُقرأ الآن أثناء الدفعة ويوقفها
(كان مستحيلًا: النداء المتزامن كان يحتجز خيط حلقة استقبال WS).
"""
import json
import threading

import pytest

import server
from core.app_context import ProjectHandle
from core.execution import ExecutionRegistry
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


def _frames(ws):
    return [json.loads(p) for p in ws.sent]


def _actions(n):
    return [{"action": "create_file", "path": f"f{i}.txt", "content": str(i)}
            for i in range(n)]


def _install_fake_slow_fm(monkeypatch, applied, cancel_at=None,
                          registry=None):
    """بديل _apply_single_action: fm بطيء مزيّف — يسجّل ما طُبّق،
    وعند الخطوة ``cancel_at`` يطلق cancel_run منتصف الدفعة (يحاكي
    وصول طلب الإلغاء من تبويب آخر أثناء عملية I/O طويلة)."""

    def _fake(action, sctx):
        applied.append(action["path"])
        if cancel_at is not None and len(applied) == cancel_at:
            t = registry.list_active()[0]
            registry.cancel(t.run_id, "user cancelled mid-batch")
        return {"ok": True, "message": "تم"}

    monkeypatch.setattr(server, "_apply_single_action", _fake)


class TestAcceptCriterion:
    """معيار القبول الحرفي: cancel أثناء دفعة 20 ملفًا يوقفها قبل اكتمالها."""

    def test_cancel_mid_batch_stops_before_completion(self, fresh_registry,
                                                      monkeypatch, tmp_path):
        (tmp_path / "p").mkdir()
        sctx, ws = _sctx_for(tmp_path / "p")
        applied = []
        _install_fake_slow_fm(monkeypatch, applied, cancel_at=5,
                              registry=fresh_registry)

        server._apply_batch(sctx, _actions(20))

        assert applied == [f"f{i}.txt" for i in range(5)]  # توقف عند 5 من 20
        frames = _frames(ws)
        # إطار error توضيحي للإلغاء + الإنهاء الشريف all_actions_done
        errs = [f for f in frames if f["type"] == "error"]
        assert any("أُلغيت الدفعة" in f["text"] for f in errs)
        assert frames[-1]["type"] == "all_actions_done"
        # التذكرة انتهت بحالة cancelled — لا تذاكر نشطة عالقة
        assert fresh_registry.list_active() == []
        states = [t.state for t in fresh_registry.list_all()]
        assert "cancelled" in states

    def test_no_cancel_full_batch_applies(self, fresh_registry,
                                          monkeypatch, tmp_path):
        (tmp_path / "p").mkdir()
        sctx, ws = _sctx_for(tmp_path / "p")
        applied = []
        _install_fake_slow_fm(monkeypatch, applied)

        server._apply_batch(sctx, _actions(20))

        assert len(applied) == 20  # بلا إلغاء: كل الدفعة تُطبَّق
        frames = _frames(ws)
        assert frames[-1] == {"type": "all_actions_done", "total": 20}
        assert not [f for f in frames if f["type"] == "error"]
        # التذكرة أُنهيت completed — الخانة تحررت
        assert fresh_registry.list_active() == []
        assert [t.state for t in fresh_registry.list_all()] == ["completed"]


class TestTicketLifecycle:
    """تخييط الدفعة تحت ticket: busy، والإنهاء الشريف نجاحًا وفشلًا."""

    def test_busy_when_project_slot_taken(self, fresh_registry,
                                          monkeypatch, tmp_path):
        (tmp_path / "p").mkdir()
        sctx, ws = _sctx_for(tmp_path / "p")
        # احجز خانة المشروع بـ run آخر
        fresh_registry.register("chain", sctx.project.project_id)
        applied = []
        _install_fake_slow_fm(monkeypatch, applied)

        server._apply_batch(sctx, _actions(3))

        assert applied == []  # لا شيء طُبّق
        frames = _frames(ws)
        assert len(frames) == 1 and frames[0]["type"] == "busy"

    def test_failed_step_finishes_ticket_failed(self, fresh_registry,
                                                monkeypatch, tmp_path):
        (tmp_path / "p").mkdir()
        sctx, ws = _sctx_for(tmp_path / "p")

        def _failing(action, s):
            return {"ok": False, "message": "فشل مقصود"}

        monkeypatch.setattr(server, "_apply_single_action", _failing)
        server._apply_batch(sctx, _actions(3))

        assert fresh_registry.list_active() == []
        assert [t.state for t in fresh_registry.list_all()] == ["failed"]
        assert _frames(ws)[-1]["type"] == "all_actions_done"

    def test_slot_free_for_next_batch_after_cancel(self, fresh_registry,
                                                   monkeypatch, tmp_path):
        (tmp_path / "p").mkdir()
        sctx, ws = _sctx_for(tmp_path / "p")
        applied = []
        _install_fake_slow_fm(monkeypatch, applied, cancel_at=2,
                              registry=fresh_registry)
        server._apply_batch(sctx, _actions(10))
        assert len(applied) == 2

        # دفعة تالية على نفس المشروع تشتغل عادي (الخانة تحررت)
        applied2 = []
        _install_fake_slow_fm(monkeypatch, applied2)
        server._apply_batch(sctx, _actions(3))
        assert len(applied2) == 3

    def test_cancel_before_first_action_applies_nothing(self, fresh_registry,
                                                        monkeypatch,
                                                        tmp_path):
        (tmp_path / "p").mkdir()
        sctx, ws = _sctx_for(tmp_path / "p")
        applied = []

        real_begin = server._begin_run_ticket

        def _begin_and_cancel(kind, send_fn, sctx=None):
            t = real_begin(kind, send_fn, sctx=sctx)
            if t is not None:
                t.cancel("cancelled before start")
            return t

        monkeypatch.setattr(server, "_begin_run_ticket", _begin_and_cancel)
        _install_fake_slow_fm(monkeypatch, applied)

        server._apply_batch(sctx, _actions(5))

        assert applied == []  # صفر إجراءات طُبّقت
        frames = _frames(ws)
        assert any(f["type"] == "error" and "أُلغيت الدفعة" in f["text"]
                   for f in frames)
        assert frames[-1]["type"] == "all_actions_done"
        assert fresh_registry.list_active() == []


class TestSameConnectionCancel:
    """TSK-606 — معيار القبول الحرفي: ``cancel_run`` من **نفس الاتصال**
    أثناء دفعة 20-action يوقفها قبل اكتمالها.

    قبل TSK-606 كان هذا مستحيلًا بنيويًا: `_handle_ws_message` كانت
    تنفّذ `_apply_batch` متزامنةً على خيط حلقة استقبال WS — فلا يُقرأ
    إطار `cancel_run` التالي إلا بعد اكتمال الدفعة كلها. الآن الدفعة
    على خيط `runner-apply-batch` والحلقة حرة لمعالجة الإلغاء.
    """

    @staticmethod
    def _join_batch_thread():
        for t in threading.enumerate():
            if t.name == "runner-apply-batch":
                t.join(timeout=10)
                assert not t.is_alive(), "خيط الدفعة لم يكتمل في المهلة"

    def test_cancel_run_frame_mid_batch_same_connection(self, fresh_registry,
                                                        monkeypatch,
                                                        tmp_path):
        """يحاكي حلقة WS واحدة: إطار الدفعة ثم إطار cancel_run — كلاهما
        عبر _handle_ws_message على نفس sctx (نفس الاتصال حرفيًا)."""
        (tmp_path / "p").mkdir()
        sctx, ws = _sctx_for(tmp_path / "p")

        step_gate = threading.Event()   # يُرفع عند بلوغ الخطوة 5
        resume_gate = threading.Event()  # يُخفَض حتى يُعالَج cancel_run
        applied = []

        def _slow(action, s):
            applied.append(action["path"])
            if len(applied) == 5:
                step_gate.set()          # الدفعة عند الخطوة 5 —
                resume_gate.wait(10)     # تتجمد حتى يمر الإلغاء
            return {"ok": True, "message": "تم"}

        monkeypatch.setattr(server, "_apply_single_action", _slow)

        # إطار 1 من الاتصال: الدفعة (يعود فورًا — الخيط العامل انطلق)
        server._handle_ws_message(None, sctx, {
            "type": "apply_all_actions", "actions": _actions(20)})
        assert step_gate.wait(10), "الدفعة لم تبلغ الخطوة 5"

        # إطار 2 من **نفس الاتصال**: cancel_run أثناء الدفعة —
        # حلقة الاستقبال حرة الآن فتعالجه فورًا (كان يستحيل قبل TSK-606)
        run_id = fresh_registry.list_active()[0].run_id
        server._handle_ws_message(None, sctx, {
            "type": "cancel_run", "run_id": run_id,
            "reason": "user cancelled from same tab"})

        resume_gate.set()  # الدفعة تستأنف — نقطة التفتيش ترى العلم
        self._join_batch_thread()

        # توقفت عند 5 من 20 — الإجراءات المتبقية لم تُطبَّق
        assert applied == [f"f{i}.txt" for i in range(5)]
        frames = _frames(ws)
        # إقرار الإلغاء وصل لنفس الاتصال أثناء الدفعة
        acks = [f for f in frames if f["type"] == "cancel_run_result"]
        assert len(acks) == 1 and acks[0]["acknowledged"] is True
        assert acks[0]["run_id"] == run_id
        # نفس عقد إطارات الإلغاء المقفول (TSK-304): error ثم all_actions_done
        assert any(f["type"] == "error" and "أُلغيت الدفعة" in f["text"]
                   for f in frames)
        assert frames[-1]["type"] == "all_actions_done"
        # التذكرة انتهت cancelled — الخانة تحررت
        assert fresh_registry.list_active() == []
        assert "cancelled" in [t.state for t in fresh_registry.list_all()]

    def test_batch_frame_returns_before_batch_completes(self, fresh_registry,
                                                        monkeypatch,
                                                        tmp_path):
        """حلقة الاستقبال حرة: _handle_ws_message يعود قبل اكتمال الدفعة
        (قياس التحرر البنيوي لا التوقيت)."""
        (tmp_path / "p").mkdir()
        sctx, ws = _sctx_for(tmp_path / "p")
        release = threading.Event()
        applied = []

        def _blocked(action, s):
            applied.append(action["path"])
            release.wait(10)
            return {"ok": True, "message": "تم"}

        monkeypatch.setattr(server, "_apply_single_action", _blocked)
        server._handle_ws_message(None, sctx, {
            "type": "apply_all_actions", "actions": _actions(3)})
        # عدنا والدفعة ما زالت جارية (أول action محتجز على البوابة)
        assert fresh_registry.list_active() != []
        release.set()
        self._join_batch_thread()
        assert len(applied) == 3
        assert _frames(ws)[-1] == {"type": "all_actions_done", "total": 3}
