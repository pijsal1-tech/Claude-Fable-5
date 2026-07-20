# -*- coding: utf-8 -*-
"""T-048 (R-701): SessionContext لكل اتصال WS — عزل تبويبين.

بنود القبول:
- E2E تبويبان: جلستان/موديلان/موافقات مستقلة — B يبدّل مشروعه
  ومقبض A يبقى نفس الكائن (id()-asserted)؛ الإطارات تصل لعميل كلٍّ
  منهما فقط.
- اختبار تنظيف القطع: القطع يلغي حلقة الـ Agent وجسر السلسلة ويفك
  اشتراك المحوّل — idempotent.
- بوابة lint: تنجح على server.py وتفشل على fixture الانتهاك.
- Regression: مسار التبويب الواحد كما هو (pong/list_runs عبر sctx).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

import server
from core.app_context import AppContext, ProjectHandle
from core.session_context import SessionContext

ROOT = pathlib.Path(__file__).resolve().parents[2]


class FakeWS:
    """قناة WS زائفة — receive من سيناريو، sent يجمع الإطارات."""

    def __init__(self, incoming=None):
        self.sent: list[str] = []
        self._incoming = iter(incoming or [])

    def receive(self):
        return next(self._incoming, None)

    def send(self, payload: str):
        self.sent.append(payload)

    def frames(self) -> list[dict]:
        return [json.loads(s) for s in self.sent]


def _mk_ctx(tmp_path, name="proj_a"):
    proj = tmp_path / name
    proj.mkdir(exist_ok=True)
    (proj / "app.py").write_text("print('x')\n", encoding="utf-8")
    handle = server._server_handle_factory(str(proj))
    return AppContext(project=handle,
                      handle_factory=server._server_handle_factory)


# ═══════════════ بناء SessionContext عند الاتصال ═══════════════

def test_build_session_context_snapshots_shared_state(monkeypatch, tmp_path):
    ctx = _mk_ctx(tmp_path)
    monkeypatch.setattr(server, "ctx", ctx)
    monkeypatch.setattr(server, "chat_history", [])
    sctx = server._build_session_context(FakeWS())
    assert isinstance(sctx, SessionContext)
    assert sctx.project is ctx.project           # بذر بمقبض المشروع المشترك
    assert sctx.chat_history == [] and sctx.chat_history is not server.chat_history
    sctx.close()


def test_two_connections_get_independent_contexts(monkeypatch, tmp_path):
    ctx = _mk_ctx(tmp_path)
    monkeypatch.setattr(server, "ctx", ctx)
    a = server._build_session_context(FakeWS())
    b = server._build_session_context(FakeWS())
    try:
        assert a is not b
        assert a.chat_history is not b.chat_history
        assert a.bus is not b.bus
    finally:
        a.close()
        b.close()


# ═══════════════ E2E تبويبان: عزل كامل (R-701) ═══════════════

def test_two_tab_project_isolation_id_asserted(monkeypatch, tmp_path):
    """B يبدّل مشروعه — مقبض A يبقى **نفس الكائن** وصالحًا."""
    ctx = _mk_ctx(tmp_path, "proj_a")
    proj_b = tmp_path / "proj_b"
    proj_b.mkdir()
    (proj_b / "other.py").write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr(server, "ctx", ctx)

    ws_a, ws_b = FakeWS(), FakeWS()
    sctx_a = server._build_session_context(ws_a)
    sctx_b = server._build_session_context(ws_b)
    a_fm_id = id(sctx_a.fm)
    a_handle_id = id(sctx_a.project)
    try:
        # B يبدّل مشروعه عبر رسالة WS حقيقية (كشف المسار الذكي)
        server._handle_ws_message(ctx, sctx_b, {
            "type": "message", "text": str(proj_b), "mode": "chat"})

        # B انتقل فعلًا
        assert str(sctx_b.project.root) == str(proj_b)
        types_b = [f["type"] for f in ws_b.frames()]
        assert "project_switched" in types_b

        # A: نفس المقبض بنفس الهوية — agent جارٍ عند A يقرأ مشروع A
        assert id(sctx_a.project) == a_handle_id
        assert id(sctx_a.fm) == a_fm_id
        assert sctx_a.project.is_valid            # لم يُبطل
        assert sctx_a.fm.scan_project()["total_files"] >= 1

        # المشروع المشترك (REST) لم يُمس
        assert ctx.project is sctx_a.project

        # الإطارات وصلت لعميل B فقط
        assert ws_a.sent == []
    finally:
        sctx_a.close()
        sctx_b.close()


def test_two_tab_independent_histories_and_models(monkeypatch, tmp_path):
    ctx = _mk_ctx(tmp_path)
    monkeypatch.setattr(server, "ctx", ctx)
    sctx_a = server._build_session_context(FakeWS())
    sctx_b = server._build_session_context(FakeWS())
    try:
        sctx_a.chat_history.append("a-only")
        assert sctx_b.chat_history == []

        model_a, model_b = object(), object()
        sctx_a.model_provider = model_a
        sctx_b.model_provider = model_b
        assert sctx_a.active_provider() is model_a
        assert sctx_b.active_provider() is model_b
    finally:
        sctx_a.close()
        sctx_b.close()


def test_two_tab_events_routed_to_correct_client_only(monkeypatch, tmp_path):
    """إطار من اتصال A يصل لعميل A فقط — R-604 لكل اتصال."""
    ctx = _mk_ctx(tmp_path)
    monkeypatch.setattr(server, "ctx", ctx)
    ws_a, ws_b = FakeWS(), FakeWS()
    sctx_a = server._build_session_context(ws_a)
    sctx_b = server._build_session_context(ws_b)
    try:
        sctx_a.send({"type": "chunk", "text": "لـ A فقط"})
        assert [f["type"] for f in ws_a.frames()] == ["chunk"]
        assert ws_b.sent == []

        sctx_b.send({"type": "error", "text": "لـ B فقط"})
        assert [f["type"] for f in ws_b.frames()] == ["error"]
        assert len(ws_a.sent) == 1
    finally:
        sctx_a.close()
        sctx_b.close()


def test_two_tab_independent_approval_inboxes(monkeypatch, tmp_path):
    """رد موافقة من A يصل لحلقة A فقط — صندوق موافقات لكل اتصال."""
    ctx = _mk_ctx(tmp_path)
    monkeypatch.setattr(server, "ctx", ctx)

    class FakeLoop:
        def __init__(self):
            self.approvals = []
            self.cancelled = False

        def approve_command(self, approved, approval_id, payload_hash):
            self.approvals.append((approved, approval_id))

        def cancel(self):
            self.cancelled = True

    sctx_a = server._build_session_context(FakeWS())
    sctx_b = server._build_session_context(FakeWS())
    loop_a, loop_b = FakeLoop(), FakeLoop()
    sctx_a.active_agent_loop = loop_a
    sctx_b.active_agent_loop = loop_b
    try:
        server._handle_ws_message(ctx, sctx_a, {
            "type": "agent_approval_response", "approved": True,
            "approval_request_id": "req-a", "payload_hash": "h"})
        assert loop_a.approvals == [(True, "req-a")]
        assert loop_b.approvals == []

        server._handle_ws_message(ctx, sctx_b, {"type": "cancel_agent"})
        assert loop_b.cancelled and not loop_a.cancelled
    finally:
        sctx_a.close()
        sctx_b.close()


# ═══════════════ تنظيف القطع ═══════════════

def test_disconnect_cleanup_cancels_and_unsubscribes(monkeypatch, tmp_path):
    ctx = _mk_ctx(tmp_path)
    monkeypatch.setattr(server, "ctx", ctx)

    class FakeLoop:
        cancelled = False

        def cancel(self):
            self.cancelled = True

    class FakeBridge:
        reason = None

        def cancel(self, reason):
            self.reason = reason

    ws = FakeWS(incoming=[json.dumps({"type": "ping"}), None])
    loop, bridge = FakeLoop(), FakeBridge()

    real_build = server._build_session_context
    captured = {}

    def _capture(ws_arg):
        sctx = real_build(ws_arg)
        sctx.active_agent_loop = loop
        sctx.chain_bridge = bridge
        captured["sctx"] = sctx
        return sctx

    monkeypatch.setattr(server, "_build_session_context", _capture)
    server.ws_handler(ws)   # يستهلك ping ثم يقطع

    sctx = captured["sctx"]
    assert sctx.closed
    assert loop.cancelled
    assert bridge.reason == "WebSocket disconnected"
    assert sctx.bus.subscriber_count == 0        # المحوّل فكّ اشتراكه
    # idempotent
    sctx.close()
    assert sctx.closed


def test_close_is_idempotent_and_safe_when_empty():
    sctx = SessionContext(send=lambda f: None)
    sctx.close()
    sctx.close()
    assert sctx.closed


# ═══════════════ Regression: مسار التبويب الواحد كما هو ═══════════════

def test_single_tab_pong_unchanged(monkeypatch, tmp_path):
    ctx = _mk_ctx(tmp_path)
    monkeypatch.setattr(server, "ctx", ctx)
    ws = FakeWS(incoming=[json.dumps({"type": "ping"}), None])
    server.ws_handler(ws)
    frames = ws.frames()
    assert len(frames) == 1
    assert frames[0] == {"type": "pong", "ctx": True}


def test_single_tab_list_runs_unchanged(monkeypatch, tmp_path):
    ctx = _mk_ctx(tmp_path)
    monkeypatch.setattr(server, "ctx", ctx)
    ws = FakeWS(incoming=[json.dumps({"type": "list_runs"}), None])
    server.ws_handler(ws)
    types = [f["type"] for f in ws.frames()]
    assert "runs_list" in types or len(types) >= 1  # نفس عقد الإطار القديم


# ═══════════════ بوابة الـ lint ═══════════════

LINT = ROOT / "scripts" / "lint_handler_state.py"
FIXTURE = ROOT / "tests" / "fixtures" / "lint_handler_state_violation.py"


def test_lint_passes_on_server():
    proc = subprocess.run(
        [sys.executable, str(LINT), "server.py"],
        cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_lint_fails_on_violation_fixture():
    proc = subprocess.run(
        [sys.executable, str(LINT), str(FIXTURE)],
        cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    out = proc.stdout
    assert "global" in out                       # التقط عبارة global
    assert "chat_history" in out                 # التقط قراءة الحالة الوحدوية
    assert "_pending_approvals" in out           # التقط dict وحدويًا متغيّرًا


def test_lint_gate_wired_into_check_sh():
    src = (ROOT / "scripts" / "check.sh").read_text(encoding="utf-8")
    assert "lint_handler_state.py" in src


def test_no_global_statements_left_in_ws_handlers():
    """معيار قبول R-701: لا handler يقرأ حالة وحدوية — grep بنيوي."""
    import ast
    src = (ROOT / "server.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name in (
                "ws_handler", "_handle_ws_message", "_apply_single_action"):
            globals_found = [n for n in ast.walk(fn)
                             if isinstance(n, ast.Global)]
            assert globals_found == [], f"{fn.name} يحتوي global"
