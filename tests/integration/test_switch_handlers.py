# -*- coding: utf-8 -*-
"""T-008 (R-102): switch handlers go through ctx — no private pokes.

Covers:
- api_switch_project → ctx.switch_project() (Flask test client E2E)
- switch_model publication: ChainBridge/DelegateBridge resolve
  ctx.active_provider at call time (no `_provider =` pokes needed)
- RequestRouter public `active_provider_name` property replaces the
  private-attribute poke
"""
import json

import pytest

import server
from core.app_context import AppContext, ProjectHandle
from chain.bridge import ChainBridge
from chain.delegate import DelegateBridge
from chain.router import RequestRouter


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


# ── api_switch_project E2E through Flask test client ──────────────

def test_api_switch_project_goes_through_ctx(monkeypatch, tmp_path):
    ctx, proj_a, proj_b = _make_ctx(tmp_path)
    old_handle = ctx.project
    monkeypatch.setattr(server, "ctx", ctx)

    client = server.app.test_client()
    resp = client.post("/api/switch-project",
                       data=json.dumps({"path": str(proj_b)}),
                       content_type="application/json")
    body = resp.get_json()

    assert resp.status_code == 200 and body["ok"] is True
    assert body["project"]["root"] == str(proj_b)
    # the swap happened ON the context, old handle invalidated
    assert str(ctx.project.root) == str(proj_b)
    assert not old_handle.is_valid


def test_api_switch_project_blocked_during_active_run(monkeypatch, tmp_path):
    from core.execution import ExecutionRegistry

    ctx, proj_a, proj_b = _make_ctx(tmp_path)
    monkeypatch.setattr(server, "ctx", ctx)
    # T-015 (R-105): the guard reads execution_registry.list_active() now
    reg = ExecutionRegistry()
    reg.register("chain")
    monkeypatch.setattr(server, "execution_registry", reg)

    client = server.app.test_client()
    resp = client.post("/api/switch-project",
                       data=json.dumps({"path": str(proj_b)}),
                       content_type="application/json")

    assert resp.status_code == 409
    assert str(ctx.project.root) == str(proj_a)  # untouched


# ── switch_model publication (no pokes) ────────────────────────────

class _Prov:
    def __init__(self, name):
        self.name = name


def test_bridges_resolve_provider_from_ctx_after_switch(tmp_path):
    ctx, proj_a, _ = _make_ctx(tmp_path)
    p1, p2 = _Prov("one"), _Prov("two")
    ctx.switch_model(p1)

    bridge = ChainBridge(provider=p1, project_root=str(proj_a), ctx=ctx)
    delegate = DelegateBridge(p1, ctx=ctx)
    assert bridge._provider is p1
    assert delegate._provider is p1

    # ONE publication — no per-object pokes
    ctx.switch_model(p2)

    assert bridge._provider is p2
    assert delegate._provider is p2


def test_router_public_property_replaces_poke():
    router = RequestRouter(orchestrator=None, budget=None,
                           active_provider_name="genspark")
    router.active_provider_name = "deepseek"  # public API, not _attr
    assert router.active_provider_name == "deepseek"
    assert router._active_provider_name == "deepseek"  # owner-internal view


def test_ctx_less_bridges_keep_static_provider(tmp_path):
    """Legacy path: without ctx the constructor arg still wins."""
    p1 = _Prov("solo")
    bridge = ChainBridge(provider=p1, project_root=str(tmp_path))
    delegate = DelegateBridge(p1)
    assert bridge._provider is p1
    assert delegate._provider is p1
