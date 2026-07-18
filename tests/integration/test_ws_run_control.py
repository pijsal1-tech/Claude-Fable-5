# -*- coding: utf-8 -*-
"""T-016 (R-105): WS control surface — `list_runs` / `cancel_run`.

Acceptance criterion (E2E): start a run → list shows it `running` →
cancel_run stops it (cooperatively, at the next checkpoint) → list shows
the terminal `cancelled` state.

Also: cancel_run on unknown/terminal runs → acknowledged=False +
error="not_found"; empty run_id → error="missing_run_id"; frames are
additive (existing frames untouched — regression covered elsewhere).
"""
from __future__ import annotations

import json
import threading
import time

import pytest

import server
from chain.bridge import ChainBridge
from core.execution import ExecutionRegistry
from tests.fakes.fake_provider import FakeProvider

JOIN_TIMEOUT = 10.0


class FakeWS:
    """Minimal ws double capturing JSON-encoded frames."""
    def __init__(self):
        self.sent = []

    def send(self, payload: str):
        self.sent.append(payload)

    def frames(self):
        return [json.loads(p) for p in self.sent]


@pytest.fixture(autouse=True)
def fresh_registry(monkeypatch):
    """Isolate each test with its own registry instance."""
    reg = ExecutionRegistry()
    monkeypatch.setattr(server, "execution_registry", reg)
    return reg


# ═══════════════════════ frame helpers: list_runs ═══════════════════════

def test_list_runs_empty_registry():
    frame = server._list_runs_frame()
    assert frame == {"type": "runs_list", "runs": []}


def test_list_runs_shows_active_run(fresh_registry):
    t = fresh_registry.register("chain")
    frame = server._list_runs_frame()
    assert frame["type"] == "runs_list"
    assert len(frame["runs"]) == 1
    entry = frame["runs"][0]
    assert entry["id"] == t.run_id
    assert entry["mode"] == "chain"
    assert entry["state"] == "running"
    assert entry["started_at"] == pytest.approx(t.created_at)
    assert entry["is_cancelled"] is False
    assert entry["finished_at"] is None


def test_list_runs_includes_terminal_runs(fresh_registry):
    """المنتهية تظهر أيضًا بحالتها النهائية — الواجهة تحتاج التاريخ الصادق."""
    t1 = fresh_registry.register("agent")
    t1.finish("completed")
    t2 = fresh_registry.register("delegate")

    entries = {e["id"]: e for e in server._list_runs_frame()["runs"]}
    assert entries[t1.run_id]["state"] == "completed"
    assert entries[t1.run_id]["finished_at"] is not None
    assert entries[t2.run_id]["state"] == "running"


# ═══════════════════════ frame helpers: cancel_run ═══════════════════════

def test_cancel_run_acknowledged_raises_flag(fresh_registry):
    t = fresh_registry.register("chain")
    frame = server._cancel_run_frame(t.run_id, "user clicked stop")
    assert frame == {
        "type": "cancel_run_result",
        "run_id": t.run_id,
        "acknowledged": True,
    }
    # تعاوني: العلم مرفوع لكن الحالة تبقى running بصدق حتى نقطة التفتيش
    assert t.is_cancelled
    assert t.cancel_reason == "user clicked stop"
    assert t.state == "running"


def test_cancel_run_unknown_id_not_found():
    frame = server._cancel_run_frame("no-such-run")
    assert frame["acknowledged"] is False
    assert frame["error"] == "not_found"


def test_cancel_run_terminal_run_not_found(fresh_registry):
    """إلغاء run منتهٍ = not_found (الحالات النهائية غير قابلة للتغيير)."""
    t = fresh_registry.register("chain")
    t.finish("completed")
    frame = server._cancel_run_frame(t.run_id)
    assert frame["acknowledged"] is False
    assert frame["error"] == "not_found"
    assert t.state == "completed"          # لم يتغير شيء


def test_cancel_run_missing_id():
    frame = server._cancel_run_frame("")
    assert frame["acknowledged"] is False
    assert frame["error"] == "missing_run_id"
    assert "run_id" not in frame


# ═══════════════════════ E2E: start → list → cancel → list ═══════════════

def test_e2e_list_cancel_list(tmp_path, fresh_registry):
    """معيار القبول: run يبدأ، list يعرضه running، cancel_run يوقفه،
    list يعرض الحالة النهائية cancelled."""
    ticket = fresh_registry.register("chain")
    release = threading.Event()

    def slow_responder(prompt, history, sys):
        release.wait(timeout=5)         # الخطوة 1 معلقة حتى نلغي
        return "step response"

    provider = FakeProvider(responder=slow_responder)
    project = tmp_path / "project"
    project.mkdir()
    bridge = ChainBridge(
        provider=provider,
        project_root=str(project),
        runs_dir=tmp_path / "runs",
    )

    frames: list[dict] = []
    run_id = bridge.start_chain(frames.append, "اعمل تحليل وخطة كاملة",
                                force_strategy="pipeline", ticket=ticket)
    assert run_id
    time.sleep(0.2)                      # الخطوة 1 بدأت (معلقة في المزود)

    # (1) list يعرض الـ run نشطًا
    listed = server._list_runs_frame()["runs"]
    assert [(e["id"], e["state"]) for e in listed] == [(ticket.run_id, "running")]

    # (2) cancel_run عبر المعرّف — acknowledged
    cancel_frame = server._cancel_run_frame(ticket.run_id, "stop from list UI")
    assert cancel_frame["acknowledged"] is True
    release.set()                        # الخطوة 1 ترجع → التفتيش قبل التالية

    bridge._active_thread.join(timeout=JOIN_TIMEOUT)
    assert not bridge._active_thread.is_alive()

    # (3) الـ run توقف قبل الخطوة التالية والتذكرة انتهت cancelled
    assert ticket.state == "cancelled"
    assert len(provider.calls) == 1
    assert any(f.get("type") == "chain_cancelled" for f in frames)

    # (4) list يعرض الحالة النهائية
    listed = server._list_runs_frame()["runs"]
    assert listed[0]["state"] == "cancelled"
    assert listed[0]["finished_at"] is not None
    assert fresh_registry.list_active() == []
