# -*- coding: utf-8 -*-
"""TSK-725b (P2-3 / D-10) — إنفاذ Workspace Trust + endpoint /api/trust.

يتحقق آليًا من (معايير القبول — DEVELOPMENT_TASKS §TSK-725/725b):
  1. ApprovalGate.interactive_override: غير موثوق ⇒ interactive إجباري
     رغم mode=auto (whitelist لا تمرّر تلقائيًا)؛ موثوق ⇒ auto كما هو؛
     فشل الـ override نفسه ⇒ إجباري (fail-closed)؛ deny يبقى deny.
  2. server._force_command_approval: غير موثوق ⇒ True رغم false صريحة؛
     موثوق ⇒ عقد config التاريخي (D-1) كما هو.
  3. server._workspace_trusted: fm=None ⇒ False (إقلاع مبكر/اختبارات).
  4. /api/trust: GET fail-closed بلا مسارات في الحمولة؛ POST قرار
     صريح bool فقط (400 لغيره)؛ الدورة GET→POST→GET متسقة.

--- السيناريو اليدوي الموثَّق (بند Documentation — Accept الرسمي) ---
  1. شغّل الخادم على مجلد جديد (بلا .ai_runs/trust.json) مع
     auto_execute:true وforce_command_approval:false في config.
  2. اطلب أمر شل من الوكيل — تظهر بطاقة موافقة رغم auto (غير موثوق).
  3. POST /api/trust {trusted:true} (أو زر الشريط بعد 725c) ثم أعد
     الطلب — يمر تلقائيًا (موثوق + auto).
  4. بدّل لمجلد آخر غير موثوق — يعود الإلزام فورًا (الفحص ديناميكي).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import server  # noqa: E402
from core.approval import ApprovalGate, ApprovalRequest, ProposedAction  # noqa: E402
from core import workspace_trust as wt  # noqa: E402


def _req():
    return ApprovalRequest(
        actions=[ProposedAction(kind="command", target="echo hi")],
        source="test")


class TestGateInteractiveOverride:
    def test_untrusted_forces_interactive_despite_auto(self):
        """auto + whitelist مطابقة، لكن override=True ⇒ لا تمرير تلقائي
        — يسقط للتفاعل، وبلا قناة ⇒ رفض بمهلة/قناة غائبة لا موافقة."""
        gate = ApprovalGate(mode="auto", auto_whitelist={"command"},
                            timeout_seconds=0.05,
                            interactive_override=lambda: True)
        v = gate.request(_req())
        assert v.approved is False
        assert v.reason != "auto_whitelist"

    def test_trusted_auto_passes_whitelist(self):
        gate = ApprovalGate(mode="auto", auto_whitelist={"command"},
                            interactive_override=lambda: False)
        v = gate.request(_req())
        assert v.approved is True
        assert v.reason == "auto_whitelist"

    def test_no_override_backward_compatible(self):
        gate = ApprovalGate(mode="auto", auto_whitelist={"command"})
        v = gate.request(_req())
        assert v.approved is True and v.reason == "auto_whitelist"

    def test_override_exception_fails_closed(self):
        def boom():
            raise RuntimeError("trust check exploded")
        gate = ApprovalGate(mode="auto", auto_whitelist={"command"},
                            timeout_seconds=0.05,
                            interactive_override=boom)
        v = gate.request(_req())
        assert v.approved is False

    def test_deny_mode_stays_deny_even_if_trusted(self):
        gate = ApprovalGate(mode="deny",
                            interactive_override=lambda: False)
        v = gate.request(_req())
        assert v.approved is False and v.reason == "deny_mode"


class TestForceCommandApprovalTrust:
    def test_untrusted_overrides_explicit_false(self, monkeypatch):
        monkeypatch.setattr(server, "_workspace_trusted", lambda: False)
        monkeypatch.setattr(server, "_load_config",
                            lambda: {"force_command_approval": False})
        assert server._force_command_approval() is True

    def test_trusted_respects_explicit_false(self, monkeypatch):
        monkeypatch.setattr(server, "_workspace_trusted", lambda: True)
        monkeypatch.setattr(server, "_load_config",
                            lambda: {"force_command_approval": False})
        assert server._force_command_approval() is False

    def test_trusted_absent_key_still_failclosed_true(self, monkeypatch):
        """الثقة لا ترخّي عقد D-1: غياب المفتاح ⇒ True حتى موثوقًا."""
        monkeypatch.setattr(server, "_workspace_trusted", lambda: True)
        monkeypatch.setattr(server, "_load_config", lambda: {})
        assert server._force_command_approval() is True

    def test_workspace_trusted_fm_none_false(self, monkeypatch):
        monkeypatch.setattr(server, "fm", None)
        assert server._workspace_trusted() is False

    def test_workspace_trusted_reads_fm_root(self, monkeypatch, tmp_path):
        class _FM:
            root = tmp_path
        monkeypatch.setattr(server, "fm", _FM())
        assert server._workspace_trusted() is False  # لا سجل ⇒ غير موثوق
        wt.set_trust(tmp_path, True)
        assert server._workspace_trusted() is True


class TestTrustEndpoint:
    @pytest.fixture
    def client(self, monkeypatch, tmp_path):
        class _FM:
            root = tmp_path
        monkeypatch.setattr(server, "fm", _FM())
        return server.app.test_client(), tmp_path

    def test_get_failclosed_and_no_paths(self, client):
        c, root = client
        resp = c.get("/api/trust")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["trust"]["trusted"] is False
        # عقد التطهير: لا مسار الجذر في الحمولة
        assert str(root) not in json.dumps(data, ensure_ascii=False)

    def test_post_then_get_cycle(self, client):
        c, root = client
        resp = c.post("/api/trust", json={"trusted": True})
        assert resp.status_code == 200
        assert resp.get_json()["trust"]["trusted"] is True
        data = c.get("/api/trust").get_json()
        assert data["trust"]["trusted"] is True
        assert data["trust"]["decided_by"] == "user"
        # على القرص فعلًا (يبقى عبر إعادة التشغيل)
        assert wt.is_trusted(root) is True
        # سحب الثقة
        c.post("/api/trust", json={"trusted": False})
        assert c.get("/api/trust").get_json()["trust"]["trusted"] is False

    @pytest.mark.parametrize("body", [
        {}, {"trusted": 1}, {"trusted": "true"}, {"trusted": None},
    ])
    def test_post_non_bool_rejected_400(self, client, body):
        c, _ = client
        resp = c.post("/api/trust", json=body)
        assert resp.status_code == 400

    def test_no_fm_503(self, monkeypatch):
        monkeypatch.setattr(server, "fm", None)
        c = server.app.test_client()
        assert c.get("/api/trust").status_code == 503
