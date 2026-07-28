# -*- coding: utf-8 -*-
"""QA-T08 seed — golden lock for _apply_batch (TSK-201 / NF-23.1).

يلتقط الإطارات (frames) الصادرة من مساري apply_all_actions / execute_plan
عبر stubs كاملة (صفر استدعاءات AI خارجية — حدود QA_MASTER_PLAN) ويقارنها
بالـ golden المُلتقط من الكود قبل الدمج:
tests/goldens/apply_batch_frames.json
"""
import json
import threading
from pathlib import Path

import pytest

import server
from core.execution import ExecutionRegistry

GOLDEN = Path(__file__).resolve().parent.parent / "goldens" / "apply_batch_frames.json"


@pytest.fixture(autouse=True)
def fresh_registry(monkeypatch):
    """TSK-304 (NF-04): _apply_batch صار يسجّل ticket لكل دفعة —
    سجل نظيف لكل اختبار كي لا تتسرب التذاكر للسجل العالمي (كانت
    تلوّث test_memory_panel وغيره)."""
    reg = ExecutionRegistry()
    monkeypatch.setattr(server, "execution_registry", reg)
    return reg


class _StubFM:
    """FileManager stub — كل العمليات تنجح."""

    def create_file(self, path, content):
        return True, "تم"

    def edit_file(self, path, old_text, new_text):
        return True, "تم"


class _FailingFM(_StubFM):
    """FileManager يفشل في أي edit_file (لسيناريو فشل الخطوة 2)."""

    def edit_file(self, path, old_text, new_text):
        return False, "فشل مقصود"

    def create_file(self, path, content):
        if path.endswith("b.txt"):
            return False, "فشل مقصود"
        return True, "تم"


class _StubCmdRunner:
    def run(self, command):
        return True, "ok-output"


class _StubSctx:
    """SessionContext stub — يسجّل كل الإطارات المُرسلة."""

    def __init__(self, fm):
        self.frames = []
        self.backup_done_for_batch = False
        self.project = type("P", (), {"file_manager": fm, "root": "/tmp/x"})()
        self.command_runner = _StubCmdRunner()

    def send(self, msg):
        self.frames.append(msg)


ACTIONS = [
    {"action": "create_file", "path": "a.txt", "content": "A", "language": "text"},
    {"action": "run_command", "command": "echo hi"},
    {"action": "edit_file", "path": "a.txt", "old_text": "A", "new_text": "B"},
]


def _run_batch_via_ws(msg_type, actions, fm):
    """يشغّل مسار WS الكامل لنوع الرسالة المعطى ويعيد الإطارات."""
    sctx = _StubSctx(fm)
    orig = server._apply_single_action

    def _stubbed(action, s):
        kind = action.get("action", "")
        if kind == "create_file":
            ok, m = fm.create_file(action.get("path", ""), action.get("content", ""))
        elif kind == "edit_file":
            ok, m = fm.edit_file(action.get("path", ""), action.get("old_text", ""), action.get("new_text", ""))
        elif kind == "run_command":
            ok, m = s.command_runner.run(action.get("command", ""))
        else:
            ok, m = False, "unknown"
        return {"ok": ok, "message": m}

    server._apply_single_action = _stubbed
    try:
        server._handle_ws_message(None, sctx, {"type": msg_type, "actions": actions})
        # TSK-606: النداء صار على خيط عامل (runner-apply-batch) —
        # الـ harness ينتظر اكتماله قبل قراءة الإطارات. قفل السلوك هو
        # ملف الـ golden نفسه (لم يتغير)؛ فقط تزامنية الالتقاط تغيّرت.
        for t in threading.enumerate():
            if t.name == "runner-apply-batch":
                t.join(timeout=10)
                assert not t.is_alive(), "خيط الدفعة لم يكتمل في المهلة"
    finally:
        server._apply_single_action = orig
    return sctx.frames, sctx.backup_done_for_batch


def _capture_all():
    """4 سيناريوهات: نجاح كامل عبر المسارين، فشل خطوة 2، قائمة فارغة."""
    out = {}
    out["apply_all_ok"], _ = _run_batch_via_ws("apply_all_actions", ACTIONS, _StubFM())
    out["execute_plan_ok"], _ = _run_batch_via_ws("execute_plan", ACTIONS, _StubFM())
    fail_actions = [
        {"action": "create_file", "path": "a.txt", "content": "A", "language": "text"},
        {"action": "create_file", "path": "b.txt", "content": "B", "language": "text"},
        {"action": "run_command", "command": "echo never"},
    ]
    out["fail_step2"], _ = _run_batch_via_ws("apply_all_actions", fail_actions, _FailingFM())
    out["empty"], _ = _run_batch_via_ws("apply_all_actions", [], _StubFM())
    return out


class TestApplyBatchGolden:
    def test_frames_match_golden(self):
        """الإطارات بعد الدمج مطابقة بايت-بايت للـ golden قبل الدمج."""
        assert GOLDEN.exists(), "golden مفقود — شغّل الالتقاط قبل الدمج"
        expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
        actual = _capture_all()
        assert actual == expected

    def test_both_paths_identical(self):
        """apply_all_actions و execute_plan يعطيان نفس الإطارات تمامًا."""
        a, _ = _run_batch_via_ws("apply_all_actions", ACTIONS, _StubFM())
        b, _ = _run_batch_via_ws("execute_plan", ACTIONS, _StubFM())
        assert a == b

    def test_backup_flag_reset(self):
        """backup_done_for_batch يُعاد ضبطه False بعد الدفعة (نجاحًا وفشلًا)."""
        _, flag_ok = _run_batch_via_ws("apply_all_actions", ACTIONS, _StubFM())
        assert flag_ok is False
        _, flag_fail = _run_batch_via_ws("execute_plan", ACTIONS, _FailingFM())
        assert flag_fail is False
