# -*- coding: utf-8 -*-
"""
QA-T10 (جزء TSK-302) — سياسة خانة الـ run: project_id فعلي (NF-02).
Validates: TSK-302.

معيار القبول الحرفي: تبويبان على مشروعين مختلفين يشغّلان معًا؛
نفس المشروع → busy. عند غياب مقبض المشروع → الخانة العالمية ""
(قرار موثّق — السلوك التاريخي). صفر نداءات AI خارجية.
"""
import json

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


class TestTwoProjectsRunTogether:
    """معيار القبول: مشروعان مختلفان يشغّلان معًا."""

    def test_parallel_runs_on_different_projects(self, tmp_path):
        (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
        s1, ws1 = _sctx_for(tmp_path / "a")
        s2, ws2 = _sctx_for(tmp_path / "b")

        t1 = server._begin_run_ticket("chain", s1.send, sctx=s1)
        t2 = server._begin_run_ticket("chain", s2.send, sctx=s2)
        assert t1 is not None and t2 is not None  # كلاهما حصل على تذكرة
        assert ws1.sent == [] and ws2.sent == []  # لا إطارات busy
        assert t1.project_id != t2.project_id

    def test_same_project_second_run_busy(self, tmp_path):
        (tmp_path / "a").mkdir()
        s1, ws1 = _sctx_for(tmp_path / "a")
        s2, ws2 = _sctx_for(tmp_path / "a")  # تبويب ثانٍ على نفس المشروع

        t1 = server._begin_run_ticket("chain", s1.send, sctx=s1)
        assert t1 is not None
        t2 = server._begin_run_ticket("agent", s2.send, sctx=s2)
        assert t2 is None                          # مرفوض
        frame = json.loads(ws2.sent[0])
        assert frame["type"] == "busy"
        assert frame["active_run"] == t1.run_id

    def test_slot_freed_after_finish(self, tmp_path):
        (tmp_path / "a").mkdir()
        s1, _ = _sctx_for(tmp_path / "a")
        t1 = server._begin_run_ticket("chain", s1.send, sctx=s1)
        t1.finish("completed")
        t2 = server._begin_run_ticket("chain", s1.send, sctx=s1)
        assert t2 is not None                      # الخانة تحررت

    def test_path_spelling_normalized_same_slot(self, tmp_path):
        """نفس المجلد بمسار بشكل مختلف (a/../a) → نفس الخانة → busy."""
        (tmp_path / "a").mkdir()
        s1, _ = _sctx_for(tmp_path / "a")
        s2, ws2 = _sctx_for(tmp_path / "a" / ".." / "a")
        t1 = server._begin_run_ticket("chain", s1.send, sctx=s1)
        assert t1 is not None
        t2 = server._begin_run_ticket("chain", s2.send, sctx=s2)
        assert t2 is None
        assert json.loads(ws2.sent[0])["type"] == "busy"


class TestGlobalSlotFallback:
    """القرار الموثّق عند الغياب: الخانة العالمية "" (السلوك التاريخي)."""

    def test_no_sctx_uses_global_slot(self):
        ws1, ws2 = FakeWS(), FakeWS()
        send1 = lambda m: ws1.send(json.dumps(m, ensure_ascii=False))
        send2 = lambda m: ws2.send(json.dumps(m, ensure_ascii=False))
        t1 = server._begin_run_ticket("chain", send1)
        assert t1 is not None and t1.project_id == ""
        t2 = server._begin_run_ticket("agent", send2)
        assert t2 is None                          # نفس الخانة العالمية
        assert json.loads(ws2.sent[0])["type"] == "busy"

    def test_sctx_without_project_uses_global_slot(self):
        ws = FakeWS()
        sctx = SessionContext(
            send=lambda m: ws.send(json.dumps(m, ensure_ascii=False)))
        t = server._begin_run_ticket("direct", sctx.send, sctx=sctx)
        assert t is not None and t.project_id == ""

    def test_global_and_project_slots_independent(self, tmp_path):
        """run عالمي + run مشروع — خانتان مستقلتان (كلاهما يعمل)."""
        (tmp_path / "a").mkdir()
        s1, _ = _sctx_for(tmp_path / "a")
        ws = FakeWS()
        t_global = server._begin_run_ticket(
            "chain", lambda m: ws.send(json.dumps(m)))
        t_proj = server._begin_run_ticket("chain", s1.send, sctx=s1)
        assert t_global is not None and t_proj is not None


class TestCallSitesWired:
    """grep-assert: كل نداءات _begin_run_ticket في server.py تمرر sctx."""

    def test_all_call_sites_pass_sctx(self):
        # TSK-612 (ADR-002): 4 مواضع نداء انتقلت إلى core/chat_dispatch.py
        # (تصل _begin_run_ticket عبر deps) — نفس الضمان على الملفين.
        pathlib = __import__("pathlib")
        server_path = pathlib.Path(server.__file__)
        src = server_path.read_text(encoding="utf-8") + "\n" + (
            server_path.parent / "core" / "chat_dispatch.py"
        ).read_text(encoding="utf-8")
        calls = [ln for ln in src.splitlines()
                 if "_begin_run_ticket(" in ln
                 and "def _begin_run_ticket" not in ln]
        assert len(calls) >= 7
        # كل نداء يمرر sctx (في نفس السطر أو السطور التالية القريبة)
        lines = src.splitlines()
        for i, ln in enumerate(lines):
            if "_begin_run_ticket(" in ln and "def " not in ln:
                window = "\n".join(lines[i:i + 4])
                assert "sctx=sctx" in window, \
                    f"نداء بلا sctx قرب السطر {i + 1}: {ln.strip()}"
