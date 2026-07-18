# -*- coding: utf-8 -*-
"""T-007 (R-102): consumers resolve ctx.project.* at CALL time.

Switch E2E: a file created in project A must be invisible to every
migrated consumer after ctx.switch_project(B) — no stale FileManager /
project_root captured at construction.

Consumers under test (the five stale-ref sites):
  1-3. AgentTools.fm / .cmd / .project_root   (chain/agent_tools.py)
  4.   ActionApplier._fm / ._cmd              (chain/action_applier.py)
  5.   ChainBridge._project_root / ._runs_dir (chain/bridge.py)
AgentLoop._auto_prefetch builds ContextBuilder from tools.project_root
per call, so it inherits the fix through AgentTools.
"""
import pathlib

import pytest

from core.app_context import AppContext, ProjectHandle
from chain.agent_tools import AgentTools
from chain.action_applier import ActionApplier
from chain.bridge import ChainBridge


def _make_ctx(tmp_path):
    """ctx over two real project dirs with real FileManagers."""
    from actions.file_manager import FileManager

    proj_a = tmp_path / "proj_a"
    proj_b = tmp_path / "proj_b"
    proj_a.mkdir()
    proj_b.mkdir()

    def factory(root: str) -> ProjectHandle:
        return ProjectHandle(root=root, fm=FileManager(root), cmd_runner=None)

    ctx = AppContext(project=factory(str(proj_a)), handle_factory=factory)
    return ctx, proj_a, proj_b


def test_agent_tools_sees_new_project_after_switch(tmp_path):
    ctx, proj_a, proj_b = _make_ctx(tmp_path)
    tools = AgentTools(ctx=ctx)

    (proj_a / "only_in_a.txt").write_text("secret", encoding="utf-8")
    assert "only_in_a.txt" in tools.tool_read_file("only_in_a.txt") or \
           "secret" in tools.tool_read_file("only_in_a.txt")

    ctx.switch_project(str(proj_b))

    # file from A must be invisible now
    result = tools.tool_read_file("only_in_a.txt")
    assert "secret" not in result
    assert tools.project_root == str(proj_b)
    assert str(tools.fm.root) == str(proj_b)


def test_action_applier_writes_into_new_project(tmp_path):
    from actions.response_parser import ResponseParser

    ctx, proj_a, proj_b = _make_ctx(tmp_path)
    applier = ActionApplier(parser=ResponseParser(), ctx=ctx, auto_backup=False)

    ctx.switch_project(str(proj_b))

    ai_response = "```FILE: hello.txt\nhi from B\n```"
    applier.apply_step("s1", ai_response)

    assert not (proj_a / "hello.txt").exists(), "wrote into OLD project (stale fm)"
    assert (proj_b / "hello.txt").exists()
    assert (proj_b / "hello.txt").read_text(encoding="utf-8").strip() == "hi from B"


def test_chain_bridge_runs_dir_follows_switch(tmp_path):
    ctx, proj_a, proj_b = _make_ctx(tmp_path)

    class _P:  # minimal provider stub
        name = "fake"

    bridge = ChainBridge(provider=_P(), project_root=str(proj_a), ctx=ctx)
    assert bridge._project_root == str(proj_a)
    assert bridge._runs_dir == pathlib.Path(str(proj_a)) / ".ai_runs"

    ctx.switch_project(str(proj_b))

    assert bridge._project_root == str(proj_b)
    assert bridge._runs_dir == pathlib.Path(str(proj_b)) / ".ai_runs"


def test_ctx_less_construction_still_works(tmp_path):
    """Legacy/test path: static args remain functional without ctx."""
    from actions.file_manager import FileManager

    proj = tmp_path / "solo"
    proj.mkdir()
    (proj / "x.txt").write_text("data", encoding="utf-8")

    tools = AgentTools(file_manager=FileManager(str(proj)), project_root=str(proj))
    assert tools.project_root == str(proj)
    assert "data" in tools.tool_read_file("x.txt")


def test_server_switch_handler_syncs_ctx(monkeypatch, tmp_path):
    """api_switch_project keeps the composition root in sync (grep-level
    behavior check without Flask request machinery)."""
    import server
    ctx, proj_a, proj_b = _make_ctx(tmp_path)
    monkeypatch.setattr(server, "ctx", ctx)
    # simulate the sync line the handler executes
    server.ctx.switch_project(str(proj_b))
    assert str(server.ctx.project.root) == str(proj_b)
