# -*- coding: utf-8 -*-
"""T-004 (R-101) → T-015 (R-105): concurrent run start rejected with `busy`.

Originally exercised ActiveRunHolder + _begin_chain_guard; T-015 deleted the
holder — the guard is now `_begin_run_ticket` backed by ExecutionRegistry.
Same guarantees, now for all three kinds:
- first dispatch gets a ticket
- second dispatch gets a `busy` frame and no ticket
- finishing the ticket frees the slot
- failed start finishes the ticket as `failed` (slot freed)
"""
import json

import pytest

import server
from core.execution import ExecutionRegistry


class FakeWS:
    """Minimal ws double capturing JSON-encoded frames."""
    def __init__(self):
        self.sent = []

    def send(self, payload: str):
        self.sent.append(payload)


@pytest.fixture(autouse=True)
def fresh_registry(monkeypatch):
    """Isolate each test with its own registry instance."""
    reg = ExecutionRegistry()
    monkeypatch.setattr(server, "execution_registry", reg)
    return reg


def _send_via(ws):
    return lambda m: ws.send(json.dumps(m, ensure_ascii=False))


def test_second_start_gets_busy_frame(fresh_registry):
    ws1, ws2 = FakeWS(), FakeWS()

    t1 = server._begin_run_ticket("chain", _send_via(ws1))
    assert t1 is not None
    assert fresh_registry.list_active() == [t1]
    assert ws1.sent == []                      # no busy frame for the winner

    t2 = server._begin_run_ticket("chain", _send_via(ws2))
    assert t2 is None                          # rejected
    assert len(ws2.sent) == 1
    frame = json.loads(ws2.sent[0])
    assert frame["type"] == "busy"
    assert frame["active_run"] == t1.run_id


def test_cross_kind_exclusion(fresh_registry):
    """الاستبعاد يشمل الأنواع الثلاثة — agent لا يبدأ فوق chain نشط."""
    ws1, ws2 = FakeWS(), FakeWS()
    t1 = server._begin_run_ticket("chain", _send_via(ws1))
    assert t1 is not None
    assert server._begin_run_ticket("agent", _send_via(ws2)) is None
    assert json.loads(ws2.sent[0])["type"] == "busy"


def test_finish_frees_slot(fresh_registry):
    ws = FakeWS()
    t = server._begin_run_ticket("chain", _send_via(ws))
    assert fresh_registry.list_active() == [t]

    t.finish("completed")                      # terminal frees it
    assert fresh_registry.list_active() == []

    # next run can start immediately
    assert server._begin_run_ticket("delegate", _send_via(ws)) is not None


def test_failed_start_release_path(fresh_registry):
    """Mirrors the `if not run_id: ticket.finish(\"failed\")` branch."""
    ws = FakeWS()
    t = server._begin_run_ticket("chain", _send_via(ws))
    run_id = ""                                # start_chain refused
    if not run_id:
        t.finish("failed")
    assert fresh_registry.list_active() == []
    assert t.state == "failed"


def test_json_sender_encodes_without_lifecycle(fresh_registry):
    """_json_sender يرسل JSON فقط — لا يمس دورة حياة التذكرة (T-015)."""
    ws = FakeWS()
    t = server._begin_run_ticket("chain", _send_via(ws))
    sender = server._json_sender(ws)
    sender({"type": "chain_finished", "text": "done"})
    # frame sent, but ticket lifecycle untouched (bridge owns finish())
    assert json.loads(ws.sent[-1])["type"] == "chain_finished"
    assert fresh_registry.list_active() == [t]
