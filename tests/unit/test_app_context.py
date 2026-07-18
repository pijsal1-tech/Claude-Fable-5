# -*- coding: utf-8 -*-
"""T-005: AppContext / ProjectHandle unit tests (swap atomicity + invalidation)."""
import threading

import pytest

from core.app_context import (
    AppContext,
    ProjectHandle,
    StaleHandleError,
)


def make_ctx(tmp_path, sub="p1"):
    root = tmp_path / sub
    root.mkdir(exist_ok=True)
    factory = lambda p: ProjectHandle(root=p, fm=f"fm({p})", cmd_runner=f"cmd({p})")
    ctx = AppContext(project=factory(str(root)), handle_factory=factory)
    return ctx, root


def test_switch_project_swaps_handle(tmp_path):
    ctx, _ = make_ctx(tmp_path)
    old = ctx.project
    p2 = tmp_path / "p2"; p2.mkdir()

    new = ctx.switch_project(str(p2))

    assert ctx.project is new
    assert new.root == str(p2)
    assert id(ctx.project) != id(old)          # id()-asserted swap


def test_old_handle_unusable_after_swap(tmp_path):
    ctx, _ = make_ctx(tmp_path)
    old = ctx.project
    p2 = tmp_path / "p2"; p2.mkdir()
    ctx.switch_project(str(p2))

    assert old.is_valid is False
    with pytest.raises(StaleHandleError):
        old.ensure_valid()
    # new handle is valid and usable
    assert ctx.project.ensure_valid() is ctx.project


def test_switch_to_missing_dir_rejected_and_state_untouched(tmp_path):
    ctx, _ = make_ctx(tmp_path)
    before = ctx.project
    with pytest.raises(NotADirectoryError):
        ctx.switch_project(str(tmp_path / "does_not_exist"))
    assert ctx.project is before               # failed switch = no swap
    assert before.is_valid


def test_switch_model_atomic_and_returns_old(tmp_path):
    ctx, _ = make_ctx(tmp_path)
    assert ctx.active_provider is None
    old = ctx.switch_model("provider-A")
    assert old is None
    assert ctx.active_provider == "provider-A"
    old = ctx.switch_model("provider-B")
    assert old == "provider-A"
    assert ctx.active_provider == "provider-B"


def test_concurrent_switches_leave_consistent_state(tmp_path):
    """10 threads switch between two dirs; final handle must be valid and
    exactly one of the two roots; all superseded handles invalidated."""
    ctx, r1 = make_ctx(tmp_path)
    p2 = tmp_path / "p2"; p2.mkdir()
    roots = [str(r1), str(p2)]
    handles = []

    def worker(i):
        h = ctx.switch_project(roots[i % 2])
        handles.append(h)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()

    final = ctx.project
    assert final.is_valid
    assert final.root in roots
    # every handle except the published one must be invalidated
    stale = [h for h in handles if h is not final]
    assert all(not h.is_valid for h in stale)
