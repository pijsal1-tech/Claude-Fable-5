# -*- coding: utf-8 -*-
"""TSK-201 golden test (QA-T08): apply_all_actions / execute_plan frame parity.

يلتقط تسلسل الإطارات الصادر عن مسارَي التطبيق (قبل التوحيد كانا كتلتين
متطابقتين نصيًا L1862–1925) ويقارنه بايت-بايت ضد golden محفوظ.
أي انحراف في الإطارات بعد دمجهما في ``_apply_batch`` = فشل فوري.

صفر نداءات AI خارجية — كل شيء stub محلي (حدود QA_MASTER_PLAN).
"""
import json
import pathlib

import pytest

import server

GOLDEN = pathlib.Path(__file__).parent.parent / "goldens" / "apply_batch_frames.json"


class _StubFM:
    """FileManager stub: ينجح دائمًا ويسجّل النداءات."""

    def __init__(self):
        self.calls = []

    def create_full_backup(self):
        self.calls.append("backup")
        return "/tmp/backup.zip"

    def write_file(self, path, content):
        self.calls.append(("write", path))
        return path

    def edit_file(self, path, old, new):
        self.calls.append(("edit", path))


class _StubCmdRunner:
    def run(self, command, need_approval=False):
        return {"success": True, "output": f"ran: {command}", "error": ""}


class _FailingFM(_StubFM):
    """يفشل عند ثاني write — لاختبار مسار break."""

    def write_file(self, path, content):
        if any(c[0] == "write" for c in self.calls if isinstance(c, tuple)):
            raise RuntimeError("disk full")
        return super().write_file(path, content)


class _StubSctx:
    def __init__(self, fm):
        self.fm = fm
        self.cmd_runner = _StubCmdRunner()
        self.backup_done_for_batch = False
        self.frames = []
        self.mode = "build"
        self.chat_history = []

    def send(self, frame):
        self.frames.append(frame)


ACTIONS = [
    {"action": "create_file", "path": "a.txt", "content": "hello"},
    {"action": "run_command", "command": "echo hi"},
    {"action": "edit_file", "path": "a.txt", "old_text": "hello", "new_text": "bye"},
]


def _run(msg_type, actions, fm=None):
    sctx = _StubSctx(fm or _StubFM())
    server._handle_ws_message(None, sctx, {"type": msg_type, "actions": actions})
    return sctx.frames


def _capture_all():
    return {
        "apply_all_actions/ok": _run("apply_all_actions", ACTIONS),
        "execute_plan/ok": _run("execute_plan", ACTIONS),
        "apply_all_actions/fail_step2": _run(
            "apply_all_actions",
            [
                {"action": "create_file", "path": "a.txt", "content": "x"},
                {"action": "create_file", "path": "b.txt", "content": "y"},
                {"action": "run_command", "command": "never"},
            ],
            fm=_FailingFM(),
        ),
        "execute_plan/empty": _run("execute_plan", []),
    }


def test_apply_batch_frames_match_golden():
    """الإطارات الصادرة مطابقة بايت-بايت للـ golden الملتقط قبل TSK-201."""
    captured = _capture_all()
    if not GOLDEN.exists():
        pytest.fail(f"golden missing: {GOLDEN} — capture it from pre-refactor code")
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    got = json.loads(json.dumps(captured, ensure_ascii=False))
    assert got == expected, "frame sequence drifted from golden (TSK-201 parity broken)"


def test_both_paths_identical():
    """apply_all_actions و execute_plan يصدران نفس التسلسل حرفيًا."""
    a = _run("apply_all_actions", ACTIONS)
    b = _run("execute_plan", ACTIONS)
    assert json.dumps(a, ensure_ascii=False, sort_keys=True) == json.dumps(
        b, ensure_ascii=False, sort_keys=True
    )


def test_backup_flag_reset():
    """علم الباك-أب يُصفَّر قبل وبعد الدفعة."""
    sctx = _StubSctx(_StubFM())
    sctx.backup_done_for_batch = True
    server._handle_ws_message(None, sctx, {"type": "apply_all_actions", "actions": ACTIONS})
    assert sctx.backup_done_for_batch is False
    assert "backup" in sctx.fm.calls  # الباك-أب حدث فعلًا رغم العلم الأولي
