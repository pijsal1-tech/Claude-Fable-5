# -*- coding: utf-8 -*-
"""
اختبارات TSK-736b — الجسر المُبوَّب + عملية الوكيل (القرار 8 من تسلسل D-19).

صفر subprocess وصفر شبكة (القرار الواعي 5 في مواصفة TSK-736):
- GovernedFsHandler يُختبَر بنداء مباشر مع workspace مؤقت وبوابات
  ApprovalGate **حقيقية** (deny/auto) — لا mocks على منطق الحوكمة.
- كناري سر: محتوى provider_keys.json/.env لا يظهر أبدًا في أي رد
  أو رسالة خطأ (عقد عدم-الترديد).
- _PipeTransport يُختبَر فوق StringIO؛ AcpAgentProcess يُختبَر فقط في
  حالاته التي لا تتطلب عملية (fail-closed قبل start) — الاختبار
  الوحيد المسموح له subprocess حقيقي هو اختبار تكامل 736c بوكيل
  دمية محلي.
"""
from __future__ import annotations

import io

import pytest

from chain.acp.agent_process import (
    AcpAgentProcess,
    AcpAgentUnavailable,
    _PipeTransport,
)
from chain.acp.connection import AcpProtocolError
from chain.acp.governed_fs import MAX_READ_BYTES, GovernedFsHandler
from chain.acp.protocol import (
    ERR_PATH_FORBIDDEN,
    ERR_PERMISSION_DENIED,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    Request,
)
from core.approval import ApprovalGate

# كناري: لو ظهر في أي رد/خطأ فقد سرّبنا سرًّا للوكيل الخارجي
CANARY = "sk-CANARY-736b-do-not-echo"


@pytest.fixture
def workspace(tmp_path):
    """workspace مؤقت فيه ملف عادي + ملفا سر (denylist) بكناري."""
    (tmp_path / "notes.txt").write_text("مرحبا يا وكيل", encoding="utf-8")
    (tmp_path / "provider_keys.json").write_text(
        '{"openai": "' + CANARY + '"}', encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=" + CANARY, encoding="utf-8")
    outside = tmp_path.parent / "outside-736b.txt"
    outside.write_text(CANARY, encoding="utf-8")
    return tmp_path


def _req(method: str, params: dict) -> Request:
    return Request(id=1, method=method, params=params)


def deny_gate() -> ApprovalGate:
    return ApprovalGate(mode="deny")


def auto_gate(*kinds: str) -> ApprovalGate:
    return ApprovalGate(mode="auto", auto_whitelist=frozenset(kinds))


# ═══ fs/read_text_file ═══

class TestRead:
    def test_normal_read_returns_content(self, workspace):
        h = GovernedFsHandler(workspace)
        result = h(_req("fs/read_text_file", {"path": "notes.txt"}))
        assert result == {"content": "مرحبا يا وكيل"}

    @pytest.mark.parametrize("secret", ["provider_keys.json", ".env"])
    def test_secret_read_denied_no_canary(self, workspace, secret):
        h = GovernedFsHandler(workspace)
        with pytest.raises(AcpProtocolError) as ei:
            h(_req("fs/read_text_file", {"path": secret}))
        assert ei.value.code == ERR_PATH_FORBIDDEN
        assert CANARY not in ei.value.message
        # رسالة عامة موحّدة — لا تؤكد وجود الملف ولا سبب الحجب
        assert ei.value.message == "مسار محظور"

    def test_escape_path_denied_uniform_message(self, workspace):
        h = GovernedFsHandler(workspace)
        with pytest.raises(AcpProtocolError) as ei:
            h(_req("fs/read_text_file", {"path": "../outside-736b.txt"}))
        assert ei.value.code == ERR_PATH_FORBIDDEN
        assert ei.value.message == "مسار محظور"
        assert CANARY not in ei.value.message

    def test_absolute_escape_denied(self, workspace):
        h = GovernedFsHandler(workspace)
        with pytest.raises(AcpProtocolError) as ei:
            h(_req("fs/read_text_file", {"path": "/etc/passwd"}))
        assert ei.value.code == ERR_PATH_FORBIDDEN

    @pytest.mark.parametrize("bad", [None, 7, "", "   ", ["x"]])
    def test_bad_path_param_invalid_params(self, workspace, bad):
        h = GovernedFsHandler(workspace)
        with pytest.raises(AcpProtocolError) as ei:
            h(_req("fs/read_text_file", {"path": bad}))
        assert ei.value.code == INVALID_PARAMS

    def test_missing_file_generic_error(self, workspace):
        h = GovernedFsHandler(workspace)
        with pytest.raises(AcpProtocolError) as ei:
            h(_req("fs/read_text_file", {"path": "لا-وجود.txt"}))
        assert ei.value.code == ERR_PATH_FORBIDDEN
        # الرسالة لا تحمل المسار المحلول (عقد عدم-الترديد)
        assert str(workspace) not in ei.value.message

    def test_oversized_file_rejected(self, workspace):
        big = workspace / "big.bin"
        big.write_bytes(b"x" * (MAX_READ_BYTES + 1))
        h = GovernedFsHandler(workspace)
        with pytest.raises(AcpProtocolError) as ei:
            h(_req("fs/read_text_file", {"path": "big.bin"}))
        assert ei.value.code == ERR_PATH_FORBIDDEN


# ═══ fs/write_text_file (خلف ApprovalGate) ═══

class TestWrite:
    def test_no_gate_means_no_write(self, workspace):
        h = GovernedFsHandler(workspace, approval_gate=None)
        with pytest.raises(AcpProtocolError) as ei:
            h(_req("fs/write_text_file",
                   {"path": "out.txt", "content": "x"}))
        assert ei.value.code == ERR_PERMISSION_DENIED
        assert not (workspace / "out.txt").exists()

    def test_deny_gate_rejects_and_reports_reason(self, workspace):
        h = GovernedFsHandler(workspace, approval_gate=deny_gate())
        with pytest.raises(AcpProtocolError) as ei:
            h(_req("fs/write_text_file",
                   {"path": "out.txt", "content": "x"}))
        assert ei.value.code == ERR_PERMISSION_DENIED
        assert "deny_mode" in ei.value.message
        assert not (workspace / "out.txt").exists()

    def test_auto_gate_with_acp_write_lands_on_disk(self, workspace):
        h = GovernedFsHandler(workspace,
                              approval_gate=auto_gate("acp_write"))
        result = h(_req("fs/write_text_file",
                        {"path": "sub/dir/out.txt", "content": "محتوى ٧٣٦"}))
        assert result == {"written": True}
        assert (workspace / "sub" / "dir" / "out.txt").read_text(
            encoding="utf-8") == "محتوى ٧٣٦"

    def test_kind_is_acp_write_not_generic_write(self, workspace):
        # بوابة auto بقائمة {"write"} فقط: لو كان kind هو "write"
        # العام لمرّت الكتابة — يجب أن تُرفض لأن kind هو acp_write.
        h = GovernedFsHandler(workspace, approval_gate=auto_gate("write"))
        with pytest.raises(AcpProtocolError) as ei:
            h(_req("fs/write_text_file",
                   {"path": "out.txt", "content": "x"}))
        assert ei.value.code == ERR_PERMISSION_DENIED
        assert "non_whitelisted_kind" in ei.value.message
        assert not (workspace / "out.txt").exists()

    def test_secret_write_denied_before_gate(self, workspace):
        # حتى مع بوابة موافِقة: مسار سر يُرفض قبل الوصول للبوابة
        h = GovernedFsHandler(workspace,
                              approval_gate=auto_gate("acp_write"))
        with pytest.raises(AcpProtocolError) as ei:
            h(_req("fs/write_text_file",
                   {"path": ".env", "content": "TOKEN=hacked"}))
        assert ei.value.code == ERR_PATH_FORBIDDEN
        # الملف الأصلي لم يُمَس
        assert CANARY in (workspace / ".env").read_text(encoding="utf-8")

    def test_escape_write_denied(self, workspace):
        h = GovernedFsHandler(workspace,
                              approval_gate=auto_gate("acp_write"))
        with pytest.raises(AcpProtocolError) as ei:
            h(_req("fs/write_text_file",
                   {"path": "../outside-736b.txt", "content": "غزو"}))
        assert ei.value.code == ERR_PATH_FORBIDDEN
        assert (workspace.parent / "outside-736b.txt").read_text(
            encoding="utf-8") == CANARY

    @pytest.mark.parametrize("bad", [None, 5, ["x"], {"a": 1}])
    def test_non_str_content_invalid_params(self, workspace, bad):
        h = GovernedFsHandler(workspace,
                              approval_gate=auto_gate("acp_write"))
        with pytest.raises(AcpProtocolError) as ei:
            h(_req("fs/write_text_file", {"path": "out.txt",
                                          "content": bad}))
        assert ei.value.code == INVALID_PARAMS


# ═══ session/request_permission ═══

class TestRequestPermission:
    def test_no_gate_denied_never_raises(self, workspace):
        h = GovernedFsHandler(workspace, approval_gate=None)
        result = h(_req("session/request_permission", {"title": "افعل شيئًا"}))
        assert result == {"outcome": "denied", "reason": "no_gate"}

    def test_deny_gate_denied(self, workspace):
        h = GovernedFsHandler(workspace, approval_gate=deny_gate())
        result = h(_req("session/request_permission", {}))
        assert result["outcome"] == "denied"
        assert result["reason"] == "deny_mode"

    def test_auto_gate_with_acp_permission_approved(self, workspace):
        h = GovernedFsHandler(workspace,
                              approval_gate=auto_gate("acp_permission"))
        result = h(_req("session/request_permission",
                        {"title": "تشغيل أداة"}))
        assert result["outcome"] == "approved"
        assert result["reason"] == "auto_whitelist"

    def test_kind_is_acp_permission_specific(self, workspace):
        # قائمة auto لا تشمل acp_permission ⇒ يُرفض (لا قناة تفاعلية)
        h = GovernedFsHandler(workspace, approval_gate=auto_gate("read"))
        result = h(_req("session/request_permission", {}))
        assert result["outcome"] == "denied"
        assert result["reason"] == "non_whitelisted_kind"


# ═══ dispatch ═══

class TestDispatch:
    def test_unknown_method_method_not_found(self, workspace):
        h = GovernedFsHandler(workspace)
        with pytest.raises(AcpProtocolError) as ei:
            h(_req("fs/delete_file", {"path": "notes.txt"}))
        assert ei.value.code == METHOD_NOT_FOUND


# ═══ _PipeTransport (فوق StringIO — صفر subprocess) ═══

class TestPipeTransport:
    def test_read_line_strips_newline(self):
        t = _PipeTransport(io.StringIO(), io.StringIO("hello\r\n"))
        assert t.read_line() == "hello"

    def test_eof_returns_none(self):
        t = _PipeTransport(io.StringIO(), io.StringIO(""))
        assert t.read_line() is None

    def test_closed_stdout_returns_none(self):
        out = io.StringIO("x\n")
        out.close()
        t = _PipeTransport(io.StringIO(), out)
        assert t.read_line() is None

    def test_write_line_appends_newline_and_flushes(self):
        stdin = io.StringIO()
        t = _PipeTransport(stdin, io.StringIO())
        t.write_line('{"jsonrpc":"2.0"}')
        assert stdin.getvalue() == '{"jsonrpc":"2.0"}\n'

    def test_write_to_closed_pipe_raises(self):
        stdin = io.StringIO()
        stdin.close()
        t = _PipeTransport(stdin, io.StringIO())
        with pytest.raises((OSError, ValueError)):
            t.write_line("x")


# ═══ AcpAgentProcess — الحالات بلا عملية (fail-closed قبل start) ═══

class TestAgentProcessFailClosed:
    def test_not_started_not_alive(self):
        p = AcpAgentProcess(command="never-run")
        assert p.alive is False

    def test_stop_before_start_is_noop(self):
        p = AcpAgentProcess(command="never-run")
        p.stop()  # لا يرفع
        assert p.alive is False

    def test_new_session_before_start_raises_unavailable(self):
        p = AcpAgentProcess(command="never-run")
        with pytest.raises(AcpAgentUnavailable):
            p.new_session()

    def test_prompt_before_start_raises_unavailable(self):
        p = AcpAgentProcess(command="never-run")
        with pytest.raises(AcpAgentUnavailable):
            p.prompt("s1", "مرحبا")
