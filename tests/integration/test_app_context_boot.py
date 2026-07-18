# -*- coding: utf-8 -*-
"""T-006 (R-102): AppContext is built in main() and reachable in handlers.

Boot smoke without Flask: we simulate main()'s wiring by assigning the
legacy globals, then call server._build_ctx() and assert the one-way
aliasing invariant — ctx fields ARE the legacy globals (identical objects),
so both code paths see the same state during the R-102 migration.
"""
import json

import pytest

import server
from core.app_context import AppContext


class FakeWS:
    def __init__(self):
        self.sent = []

    def send(self, payload: str):
        self.sent.append(payload)


@pytest.fixture
def wired_globals(monkeypatch, tmp_path):
    """Simulate main()'s global wiring with light sentinels."""
    fm = object()
    cmd_runner = object()
    pool = object()
    session_mgr = object()
    budget = object()
    monkeypatch.setattr(server, "fm", fm)
    monkeypatch.setattr(server, "cmd_runner", cmd_runner)
    monkeypatch.setattr(server, "provider_pool", pool)
    monkeypatch.setattr(server, "session_mgr", session_mgr)
    monkeypatch.setattr(server, "account_budget", budget)
    return {
        "fm": fm, "cmd_runner": cmd_runner, "pool": pool,
        "session_mgr": session_mgr, "budget": budget,
        "root": str(tmp_path),
    }


def test_build_ctx_aliases_legacy_globals(wired_globals):
    ctx = server._build_ctx(wired_globals["root"])
    assert isinstance(ctx, AppContext)
    # one-way aliasing: identical objects, not copies
    assert ctx.project.fm is wired_globals["fm"]
    assert ctx.project.cmd_runner is wired_globals["cmd_runner"]
    assert ctx.provider_pool is wired_globals["pool"]
    assert ctx.session_manager is wired_globals["session_mgr"]
    assert ctx.budget is wired_globals["budget"]
    assert ctx.project.root == wired_globals["root"]
    assert ctx.project.is_valid


def test_ctx_active_provider_published(wired_globals):
    ctx = server._build_ctx(wired_globals["root"])
    provider = object()
    old = ctx.switch_model(provider)
    assert old is None
    assert ctx.active_provider is provider


def test_ws_handler_pong_reports_ctx(monkeypatch, wired_globals):
    """Handler receives ctx: pong frame carries ctx reachability flag."""
    ctx = server._build_ctx(wired_globals["root"])
    monkeypatch.setattr(server, "ctx", ctx)

    ws = FakeWS()
    frames = iter([json.dumps({"type": "ping"}), None])
    ws.receive = lambda: next(frames)

    server.ws_handler(ws)

    assert len(ws.sent) == 1
    pong = json.loads(ws.sent[0])
    assert pong["type"] == "pong"
    assert pong["ctx"] is True


def test_ws_handler_pong_ctx_false_when_unbuilt(monkeypatch):
    monkeypatch.setattr(server, "ctx", None)
    ws = FakeWS()
    frames = iter([json.dumps({"type": "ping"}), None])
    ws.receive = lambda: next(frames)

    server.ws_handler(ws)

    pong = json.loads(ws.sent[0])
    assert pong["type"] == "pong"
    assert pong["ctx"] is False
