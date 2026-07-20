# -*- coding: utf-8 -*-
"""T-054 (R-106): checkpoints wired into the gated apply + rollback WS commands.

Acceptance criteria under test:
- apply a 3-file batch via the gate then `rollback_run` restores bytes
- no apply path bypasses the snapshot (structural grep + behavior)
- per-file rollback; conflict frame on external edit
- retention prune bounds checkpoint storage across 50 fixture runs
"""
from __future__ import annotations

import pathlib
import re
import threading

import pytest

import server
from actions.file_manager import FileManager
from actions.response_parser import ResponseParser
from chain.action_applier import ActionApplier
from chain.bridge import ChainBridge
from core.approval import ApprovalGate
from core.checkpoint import CheckpointManager
from core.session_context import SessionContext
from tests.fakes.fake_provider import FakeProvider

JOIN_TIMEOUT = 10.0

# رد AI يكتب 3 ملفات — صيغة ```FILE: التي يفهمها ResponseParser
AI_RESPONSE_3_FILES = (
    "تم:\n"
    "```FILE: one.txt\nNEW ONE\n```\n"
    "```FILE: sub/two.txt\nNEW TWO\n```\n"
    "```FILE: three.txt\nNEW THREE\n```\n"
)


class FrameSink:
    def __init__(self):
        self.frames: list[dict] = []
        self._lock = threading.Lock()

    def __call__(self, msg: dict):
        with self._lock:
            self.frames.append(msg)

    def of_type(self, t: str) -> list[dict]:
        with self._lock:
            return [f for f in self.frames if f.get("type") == t]


def _make_bridge(tmp_path: pathlib.Path):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    # ملفان موجودان مسبقًا بمحتوى أصلي + الثالث (sub/two.txt) سيُنشأ من الصفر
    (project / "one.txt").write_text("ORIG ONE", encoding="utf-8")
    (project / "three.txt").write_text("ORIG THREE", encoding="utf-8")
    fm = FileManager(str(project))
    applier = ActionApplier(parser=ResponseParser(), file_manager=fm,
                            auto_backup=False)
    gate = ApprovalGate(mode="auto",
                        auto_whitelist={"write", "edit", "command"})
    bridge = ChainBridge(
        provider=FakeProvider(responses=[AI_RESPONSE_3_FILES]),
        project_root=str(project),
        runs_dir=tmp_path / "runs",
        action_applier=applier,
        approval_gate=gate,
    )
    return bridge, project


def _run_and_join(bridge: ChainBridge, sink: FrameSink) -> str:
    run_id = bridge.start_chain(sink, "اكتب الملفات",
                                force_strategy="direct")
    assert run_id
    thread = bridge._active_thread
    assert thread is not None
    thread.join(timeout=JOIN_TIMEOUT)
    assert not thread.is_alive(), "chain thread لم ينتهِ في المهلة"
    return run_id


def _sctx_with_bridge(bridge) -> tuple[SessionContext, list[dict]]:
    sent: list[dict] = []
    sctx = SessionContext(send=sent.append)
    sctx.chain_bridge = bridge
    return sctx, sent


# ═══════════════ E2E: apply → rollback_run يستعيد البايتات ═══════════════

def test_gated_apply_then_rollback_run_restores_bytes(tmp_path):
    bridge, project = _make_bridge(tmp_path)
    sink = FrameSink()
    run_id = _run_and_join(bridge, sink)
    assert len(sink.of_type("chain_apply_result")) == 1

    # الكتابة تمت فعلًا
    assert (project / "one.txt").read_text(encoding="utf-8").strip() == "NEW ONE"
    assert (project / "sub" / "two.txt").exists()
    assert (project / "three.txt").read_text(encoding="utf-8").strip() == "NEW THREE"

    # rollback عبر مسار WS الحقيقي
    sctx, sent = _sctx_with_bridge(bridge)
    server._handle_ws_message(None, sctx, {"type": "rollback_run",
                                           "run_id": run_id})
    frames = [f for f in sent if f.get("type") == "rollback_result"]
    assert len(frames) == 1
    assert frames[0]["status"] == "success"

    # بايتات ما-قبل-الكتابة عادت بالضبط — والمُنشأ من الصفر حُذف
    assert (project / "one.txt").read_text(encoding="utf-8") == "ORIG ONE"
    assert (project / "three.txt").read_text(encoding="utf-8") == "ORIG THREE"
    assert not (project / "sub" / "two.txt").exists()


def test_rollback_file_restores_one_leaves_siblings(tmp_path):
    bridge, project = _make_bridge(tmp_path)
    sink = FrameSink()
    run_id = _run_and_join(bridge, sink)

    sctx, sent = _sctx_with_bridge(bridge)
    server._handle_ws_message(None, sctx, {
        "type": "rollback_file", "run_id": run_id,
        "path": str(project / "one.txt")})
    frames = [f for f in sent if f.get("type") == "rollback_result"]
    assert frames[0]["status"] == "success"
    assert (project / "one.txt").read_text(encoding="utf-8") == "ORIG ONE"
    # الأشقاء لم يُمسّوا
    assert (project / "three.txt").read_text(
        encoding="utf-8").strip() == "NEW THREE"
    assert (project / "sub" / "two.txt").exists()


# ═══════════════ إطار التعارض عند تعديل خارجي ═══════════════

def test_external_edit_yields_conflict_frame(tmp_path):
    bridge, project = _make_bridge(tmp_path)
    sink = FrameSink()
    run_id = _run_and_join(bridge, sink)

    # إنسان يعدّل بعد الـ run
    (project / "one.txt").write_text("HUMAN EDIT", encoding="utf-8")

    sctx, sent = _sctx_with_bridge(bridge)
    server._handle_ws_message(None, sctx, {"type": "rollback_run",
                                           "run_id": run_id})
    frame = [f for f in sent if f.get("type") == "rollback_result"][0]
    assert frame["status"] == "partial"  # الأشقاء النظيفون استُعيدوا
    conflicted = [c["path"] for c in frame["conflicts"]]
    assert str((project / "one.txt").resolve()) in conflicted
    assert (project / "one.txt").read_text(encoding="utf-8") == "HUMAN EDIT"
    # التقرير مقروء: سبب + hashات
    assert frame["conflicts"][0]["reason"]
    assert frame["conflicts"][0]["actual_sha256"]


def test_unknown_run_and_missing_args_refused(tmp_path):
    bridge, _ = _make_bridge(tmp_path)
    sctx, sent = _sctx_with_bridge(bridge)
    server._handle_ws_message(None, sctx, {"type": "rollback_run",
                                           "run_id": "run-nope"})
    assert sent[-1]["status"] == "refused"
    server._handle_ws_message(None, sctx, {"type": "rollback_run"})
    assert sent[-1]["conflicts"][0]["reason"] == "missing_run_id"
    server._handle_ws_message(None, sctx, {"type": "rollback_file",
                                           "run_id": "run-x"})
    assert sent[-1]["conflicts"][0]["reason"] == "missing_path"


def test_no_bridge_refused():
    sent: list[dict] = []
    sctx = SessionContext(send=sent.append)
    sctx.chain_bridge = None
    server._handle_ws_message(None, sctx, {"type": "rollback_run",
                                           "run_id": "run-1"})
    assert sent[-1]["status"] == "refused"
    assert sent[-1]["conflicts"][0]["reason"] == "no_chain_bridge"


# ═══════════════ structural: لا مسار apply يتجاوز الـ snapshot ═══════════════

def test_no_apply_path_bypasses_snapshot_structural():
    """grep-level: apply_step في _gated_apply يمرر checkpoint= دائمًا."""
    src = pathlib.Path("chain/bridge.py").read_text(encoding="utf-8")
    gated = src[src.index("def _gated_apply"):]
    gated = gated[:gated.index("\n    def ")]  # جسم الدالة فقط
    calls = re.findall(r"apply_step\([^)]*\)", gated, flags=re.S)
    assert calls, "لا يوجد استدعاء apply_step في _gated_apply"
    for call in calls:
        assert "checkpoint=" in call, f"apply بلا checkpoint: {call}"
    # وداخل الـ applier: snapshot يسبق الكتابة والكتابة تسبق الـ seal
    applier_src = pathlib.Path("chain/action_applier.py").read_text(
        encoding="utf-8")
    assert applier_src.index("checkpoint.snapshot") \
        < applier_src.index("self._apply_action(action)")
    assert applier_src.index("self._apply_action(action)") \
        < applier_src.index("checkpoint.seal")


def test_behavioral_snapshot_written_by_gated_apply(tmp_path):
    """سلوكيًا: الـ gated apply أنتج checkpoint قابلًا للاستعادة."""
    bridge, _ = _make_bridge(tmp_path)
    sink = FrameSink()
    run_id = _run_and_join(bridge, sink)
    mgr = bridge.checkpoint_manager
    assert run_id in mgr.run_ids()
    assert len(mgr.entries_for_run(run_id)) == 3


# ═══════════════ retention: التقليم يحد التخزين عبر 50 run ═══════════════

def test_retention_prune_bounds_checkpoint_storage(tmp_path):
    store_root = tmp_path / "ckpt"
    mgr = CheckpointManager(store_root)
    proj = tmp_path / "p"
    proj.mkdir()
    f = proj / "a.txt"
    f.write_text("content--1", encoding="utf-8")  # حالة ما-قبل أول run
    run_ids = []
    for i in range(50):
        rid = f"run-{i:03d}"
        mgr.snapshot(rid, [f])                       # قبل الكتابة
        f.write_text(f"content-{i}", encoding="utf-8")  # "الـ run يكتب"
        mgr.seal(rid, [f])                           # بعد الكتابة
        run_ids.append(rid)
    assert len(mgr.run_ids()) == 50
    blobs_before = len(list((store_root / "objects").iterdir()))
    assert blobs_before >= 50

    # سياسة "احتفظ بآخر 10" — نفس شكل ناتج sweep (أسماء الناجين)
    keep = set(run_ids[-10:])
    pruned = mgr.prune(keep)
    assert pruned == 40
    assert set(mgr.run_ids()) == keep
    blobs_after = len(list((store_root / "objects").iterdir()))
    assert blobs_after < blobs_before

    # الناجون ما زالوا قابلين للاستعادة: أعد الملف لحالة seal الـ run
    # المستهدف (run-049 ختم "content-49") ثم استعد snapshot-ه ("content-48")
    f.write_text("content-49", encoding="utf-8")
    report = mgr.restore_run("run-049")
    assert report.status == "success"
    assert f.read_text(encoding="utf-8") == "content-48"

    # وتعديل خارجي بعد التقليم ما زال يُرفض بصدق
    f.write_text("EXTERNAL", encoding="utf-8")
    report2 = mgr.restore_run("run-048")
    assert report2.status == "refused"


def test_prune_noop_when_all_kept(tmp_path):
    mgr = CheckpointManager(tmp_path / "ckpt")
    proj = tmp_path / "p"
    proj.mkdir()
    f = proj / "a.txt"
    f.write_text("x", encoding="utf-8")
    mgr.snapshot("run-1", [f])
    assert mgr.prune({"run-1"}) == 0
    assert mgr.run_ids() == ["run-1"]
