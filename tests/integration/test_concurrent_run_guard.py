# -*- coding: utf-8 -*-
"""T-004 (R-101): concurrent chain start is rejected with a `busy` frame.

Exercises the guard helpers in server.py directly (no real WS/socket needed):
- first dispatch acquires the slot
- second dispatch gets a `busy` frame and no guard id
- terminal frames (chain_finished / chain_error) release the slot
- failed start (empty run_id path) releases via explicit release
"""
import pytest

import server
from core.active_run import ActiveRunHolder


class FakeWS:
    """Minimal ws double capturing JSON-encoded frames."""
    def __init__(self):
        self.sent = []

    def send(self, payload: str):
        self.sent.append(payload)


@pytest.fixture(autouse=True)
def fresh_holder(monkeypatch):
    """Isolate each test with its own holder instance."""
    holder = ActiveRunHolder()
    monkeypatch.setattr(server, "active_run_holder", holder)
    return holder


def _send_via(ws):
    import json
    return lambda m: ws.send(json.dumps(m, ensure_ascii=False))


def test_second_start_gets_busy_frame(fresh_holder):
    ws1, ws2 = FakeWS(), FakeWS()

    g1 = server._begin_chain_guard(_send_via(ws1))
    assert g1 is not None
    assert fresh_holder.current() == g1
    assert ws1.sent == []                      # no busy frame for the winner

    g2 = server._begin_chain_guard(_send_via(ws2))
    assert g2 is None                          # rejected
    assert len(ws2.sent) == 1
    import json
    frame = json.loads(ws2.sent[0])
    assert frame["type"] == "busy"
    assert frame["active_run"] == g1


def test_terminal_frame_releases_slot(fresh_holder):
    ws = FakeWS()
    g = server._begin_chain_guard(_send_via(ws))
    sender = server._make_chain_sender(ws, g)

    sender({"type": "chain_step", "text": "working"})
    assert fresh_holder.is_active()            # non-terminal keeps the slot

    sender({"type": "chain_finished", "text": "done"})
    assert not fresh_holder.is_active()        # terminal frees it

    # next run can start immediately
    assert server._begin_chain_guard(_send_via(ws)) is not None


def test_chain_error_also_releases(fresh_holder):
    ws = FakeWS()
    g = server._begin_chain_guard(_send_via(ws))
    server._make_chain_sender(ws, g)({"type": "chain_error", "text": "boom"})
    assert not fresh_holder.is_active()


def test_failed_start_release_path(fresh_holder):
    """Mirrors the `if not run_id: release(guard_id)` branch in server.py."""
    ws = FakeWS()
    g = server._begin_chain_guard(_send_via(ws))
    run_id = ""                                # start_chain refused
    if not run_id:
        server.active_run_holder.release(g)
    assert not fresh_holder.is_active()
