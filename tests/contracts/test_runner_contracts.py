# -*- coding: utf-8 -*-
"""T-039 (R-501): تطبيق عدة عقود الـ Runner على EchoRunner المرجعي.

runner جديد؟ أضف صنفًا هنا يرث RunnerContractMixin ويعرّف make_runner —
تحصل على العدة كاملة (أحداث/نجاح/فشل/إلغاء/موافقة/تطابق التذكرة).
T-040+ سيضيف Direct/Chain/Agent/Delegate runners لنفس العدة.
"""
from __future__ import annotations

from core.runner import EventStream, Runner, RunResult
from tests.contracts.runner_contract import CollectingSink, RunnerContractMixin
from tests.fakes.echo_runner import EchoRunner

import pytest


class TestEchoRunnerContract(RunnerContractMixin):
    """EchoRunner يجتاز العدة كاملة — المرجع لكل runner قادم."""

    def make_runner(self, *, fail_with=None, cancel_after_start=None):
        return EchoRunner(fail_with=fail_with,
                          cancel_after_start=cancel_after_start)


# ═══════════════ عقود إضافية خاصة بالبنية التحتية ═══════════════

class TestRunnerProtocolShape:
    """الـ Protocol نفسه: runtime_checkable + EchoRunner يطابقه بنيويًا."""

    def test_echo_runner_satisfies_protocol(self):
        assert isinstance(EchoRunner(), Runner)

    def test_arbitrary_object_does_not_satisfy(self):
        class NotARunner:
            pass
        assert not isinstance(NotARunner(), Runner)

    def test_run_result_rejects_unknown_status(self):
        with pytest.raises(ValueError):
            RunResult(status="exploded")


class TestEventStreamGuarantees:
    """EventStream يفرض البروتوكول — لا أحداث شبحية ولا تكرار."""

    def _stream(self):
        sink = CollectingSink()
        return EventStream("run-1", sink), sink

    def test_emit_before_started_raises(self):
        stream, _ = self._stream()
        with pytest.raises(RuntimeError):
            stream.emit("run_output", text="x")

    def test_double_started_raises(self):
        stream, _ = self._stream()
        stream.started()
        with pytest.raises(RuntimeError):
            stream.started()

    def test_emit_after_finished_raises(self):
        stream, _ = self._stream()
        stream.started()
        stream.finished(reason="completed")
        with pytest.raises(RuntimeError):
            stream.emit("run_output", text="ghost")

    def test_double_finished_raises(self):
        stream, _ = self._stream()
        stream.started()
        stream.finished(reason="completed")
        with pytest.raises(RuntimeError):
            stream.finished(reason="completed")

    def test_lifecycle_events_only_via_dedicated_methods(self):
        stream, _ = self._stream()
        stream.started()
        with pytest.raises(RuntimeError):
            stream.emit("run_started")
        with pytest.raises(RuntimeError):
            stream.emit("run_finished")

    def test_seq_stamped_incrementally_with_run_id(self):
        stream, sink = self._stream()
        stream.started(mode="echo")
        stream.emit("run_output", text="a")
        stream.emit("run_output", text="b")
        stream.finished(reason="completed")
        assert [e.seq for e in sink.events] == [0, 1, 2, 3]
        assert {e.run_id for e in sink.events} == {"run-1"}
        assert sink.events[0].data == {"mode": "echo"}
        assert sink.events[-1].data == {"reason": "completed"}
