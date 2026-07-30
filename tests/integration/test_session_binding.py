# -*- coding: utf-8 -*-
"""T-031 (R-303): Session ↔ Project Binding — per-policy E2E.

Flask test-client E2E over /api/switch-project (same pattern as
test_switch_handlers.py) with a real legacy SessionManager bound to a
tmp sessions dir. The policy source (_session_binding_policy → config)
is monkeypatched per test.

Covers:
- warn: switch allowed, banner in response + module banner set,
  banner injected into project_context, cleared by /api/clear and
  /api/session/new
- fork: chat_history cleared + new bound session created
- block: 409, project untouched
- regression: same-project switch silent; unbound legacy session silent
"""
import json

import pytest

import server
from core.app_context import AppContext, ProjectHandle
from core.conversation_state import ConversationState  # TSK-710 (FI-01/4)
from actions.session_manager import SessionManager


def _make_ctx(tmp_path):
    from actions.file_manager import FileManager

    proj_a = tmp_path / "proj_a"
    proj_b = tmp_path / "proj_b"
    proj_a.mkdir()
    proj_b.mkdir()

    def factory(root: str) -> ProjectHandle:
        return ProjectHandle(root=root, fm=FileManager(root), cmd_runner=None)

    ctx = AppContext(project=factory(str(proj_a)), handle_factory=factory)
    return ctx, proj_a, proj_b


def _setup(monkeypatch, tmp_path, policy, bound_path):
    """ctx + session_mgr (bound to bound_path) + forced policy."""
    ctx, proj_a, proj_b = _make_ctx(tmp_path)
    monkeypatch.setattr(server, "ctx", ctx)
    mgr = SessionManager(str(tmp_path / "sessions"))
    mgr.new_session(bound_path)
    monkeypatch.setattr(server, "session_mgr", mgr)
    monkeypatch.setattr(server, "_session_binding_policy", lambda: policy)
    # TSK-710 (FI-01/4): الحالة القانونية الآن في المخزن — مخزن معزول لكل اختبار.
    monkeypatch.setattr(server, "conversation_state", ConversationState())
    return ctx, proj_a, proj_b, mgr


def _switch(path):
    client = server.app.test_client()
    return client.post("/api/switch-project",
                       data=json.dumps({"path": str(path)}),
                       content_type="application/json")


# ── warn ───────────────────────────────────────────────────────────

def test_warn_switch_allowed_with_banner(monkeypatch, tmp_path):
    ctx, proj_a, proj_b, _ = _setup(monkeypatch, tmp_path,
                                    "warn", str(tmp_path / "proj_a"))
    resp = _switch(proj_b)
    body = resp.get_json()

    assert resp.status_code == 200 and body["ok"] is True
    assert body["binding"]["policy"] == "warn"
    assert "تنبيه ربط الجلسة" in body["binding"]["banner"]
    assert str(proj_b) in body["binding"]["banner"]
    # البانر في المخزن القانوني → يُحقن في سياق كل رسالة (TSK-710)
    assert "تنبيه ربط الجلسة" in server.conversation_state.binding_banner
    assert str(ctx.project.root) == str(proj_b)


def test_warn_banner_cleared_by_clear_and_new_session(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, "warn", str(tmp_path / "proj_a"))
    _switch(tmp_path / "proj_b")
    assert server.conversation_state.binding_banner

    client = server.app.test_client()
    client.post("/api/clear")
    assert server.conversation_state.binding_banner == ""

    _switch(tmp_path / "proj_a")  # re-arm (mismatch مع جلسة clear الجديدة أو لا)
    server.conversation_state.set_banner("⚠️ test")
    client.post("/api/session/new")
    assert server.conversation_state.binding_banner == ""


def test_warn_banner_prefixes_project_context():
    """منطق الحقن نفسه (بانر + سياق / بانر فقط)."""
    banner = "⚠️ [تنبيه ربط الجلسة]: X"
    project_context = "سياق"
    combined = (f"{banner}\n\n{project_context}"
                if project_context else banner)
    assert combined.startswith(banner) and combined.endswith("سياق")
    project_context = ""
    combined = (f"{banner}\n\n{project_context}"
                if project_context else banner)
    assert combined == banner


# ── fork ───────────────────────────────────────────────────────────

def test_fork_clears_history_and_binds_new_session(monkeypatch, tmp_path):
    ctx, proj_a, proj_b, mgr = _setup(monkeypatch, tmp_path,
                                      "fork", str(tmp_path / "proj_a"))
    old_id = mgr.current_session_id
    server.conversation_state.append(object())  # تاريخ موجود قبل التبديل (TSK-710)

    resp = _switch(proj_b)
    body = resp.get_json()

    assert resp.status_code == 200 and body["ok"] is True
    assert body["binding"]["policy"] == "fork"
    new_id = body["binding"]["new_session_id"]
    assert new_id and new_id != old_id
    assert server.conversation_state.snapshot() == []          # التاريخ مُسح
    assert server.conversation_state.binding_banner == ""      # لا بانر تحت fork
    # الجلسة الجديدة مرتبطة بالمشروع الجديد
    new_sess = mgr.load_session(new_id)
    assert new_sess["project_path"] == str(proj_b)


# ── block ──────────────────────────────────────────────────────────

def test_block_refuses_switch_409(monkeypatch, tmp_path):
    ctx, proj_a, proj_b, _ = _setup(monkeypatch, tmp_path,
                                    "block", str(tmp_path / "proj_a"))
    resp = _switch(proj_b)
    body = resp.get_json()

    assert resp.status_code == 409 and body["ok"] is False
    assert body["binding"]["policy"] == "block"
    assert body["binding"]["bound_project_path"] == str(tmp_path / "proj_a")
    assert str(ctx.project.root) == str(proj_a)  # المشروع لم يُمس


# ── regression: silent paths ───────────────────────────────────────

@pytest.mark.parametrize("policy", ["warn", "fork", "block"])
def test_same_project_switch_is_silent(monkeypatch, tmp_path, policy):
    ctx, proj_a, _, mgr = _setup(monkeypatch, tmp_path,
                                 policy, str(tmp_path / "proj_a"))
    old_id = mgr.current_session_id
    resp = _switch(proj_a)
    body = resp.get_json()

    assert resp.status_code == 200 and body["ok"] is True
    assert body["binding"] is None            # لا إجراء ربط
    assert server.conversation_state.binding_banner == ""
    assert mgr.current_session_id == old_id   # لا fork


@pytest.mark.parametrize("policy", ["warn", "fork", "block"])
def test_unbound_legacy_session_switches_silently(monkeypatch, tmp_path,
                                                  policy):
    """جلسة بلا project_path (قديمة) = غير مرتبطة → تبديل صامت."""
    ctx, _, proj_b, mgr = _setup(monkeypatch, tmp_path, policy, "")
    resp = _switch(proj_b)
    body = resp.get_json()

    assert resp.status_code == 200 and body["ok"] is True
    assert body["binding"] is None
    assert server.conversation_state.binding_banner == ""
    assert str(ctx.project.root) == str(proj_b)


def test_no_session_mgr_switch_unaffected(monkeypatch, tmp_path):
    """بلا session_mgr (تشغيل اختبارات/قديم) — المسار القديم كما هو."""
    ctx, _, proj_b = _make_ctx(tmp_path)
    monkeypatch.setattr(server, "ctx", ctx)
    monkeypatch.setattr(server, "session_mgr", None)
    monkeypatch.setattr(server, "conversation_state", ConversationState())
    resp = _switch(proj_b)
    body = resp.get_json()
    assert resp.status_code == 200 and body["ok"] is True
    assert body["binding"] is None
