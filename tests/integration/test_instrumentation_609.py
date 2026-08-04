# -*- coding: utf-8 -*-
"""TSK-609 (PM-01/02/04 §R6) — instrumentation المدة والتوكنز والسياق.

Validates: TSK-609.

معيار القبول الحرفي: «إطار finished/done يحمل duration_ms
(وtoken_estimate حيث ينطبق) للمسارات الثلاثة؛ goldens القائمة
تُحدَّث بحقل إضافي فقط (لا كسر بنية)».

يتحقق من:
  1. PM-02 (runner-level): حدث run_finished للمسارات الثلاثة
     (direct/agent/delegate) يحمل ``duration_ms`` عددًا صحيحًا ≥ 0 —
     بجانب ``reason`` القائم (حقل إضافي فقط؛ عقود contracts/ تفحص
     بالمفتاح فلا تتأثر).
  2. PM-04: ``ContextEngine.gather`` يوقّت collect لكل مصدر —
     ``bundle.source_timings_ms`` يحمل kind → ms لكل المصادر بما
     فيها الفاشلة (الاستثناء يُبتلع كما كان)؛ والـ facade يكشفها في
     ``MessageContext.source_timings_ms`` (حقل افتراضي — goldens
     T-017 تقارن مفاتيح الـ golden فقط).
  3. PM-01/02 (server-level): إطار done/plan في المسار المباشر
     يحمل ``duration_ms`` + ``token_estimate`` (تقدير chars÷4 —
     نفس CharsPerTokenEstimator المركزي، لا ثوابت جديدة) — e2e
     على FakeProvider بلا أي نداء AI خارجي.
  4. Regression بنيوي: الحقول إضافية فقط — مفاتيح إطار done
     التاريخية (actions/options/summary) باقية.

صفر نداءات AI خارجية — FakeProvider في كل المسارات.
"""
from __future__ import annotations

import json
import pathlib
import tempfile
import time

import pytest

import server
from actions.command_runner import CommandRunner
from actions.file_manager import FileManager
from chain.agent_loop import AgentLoop
from chain.agent_tools import AgentTools
from chain.delegate import DelegateBridge
from context.budget import CharsPerTokenEstimator
from context.engine import ContextEngine, ContextRequest
from context.bundle import ContextItem
from context.facade import gather_message_context
from core.execution import ExecutionRegistry
from core.runner import RunRequest
from runners.agent import AgentRunner
from runners.delegate import DelegateRunner
from runners.direct import DirectRunner
from tests.contracts.runner_contract import CollectingSink
from tests.fakes.fake_provider import FakeProvider


# ═══════════ 1. PM-02: duration_ms في run_finished للمسارات الثلاثة ═══════════

def _run(runner, mode="direct", message="hello"):
    registry = ExecutionRegistry()
    ticket = registry.register(mode, project_id="tsk609-proj")
    sink = CollectingSink()
    result = runner.run(RunRequest(mode=mode, message=message), ticket, sink)
    return result, sink


def _assert_finished_has_duration(sink, expected_reason):
    last = sink.events[-1]
    assert last.type == "run_finished"
    assert last.data["reason"] == expected_reason      # الحقل التاريخي باقٍ
    assert "duration_ms" in last.data, "run_finished بلا duration_ms (PM-02)"
    d = last.data["duration_ms"]
    assert isinstance(d, int) and d >= 0


class TestRunnerFinishedCarriesDuration:
    def test_direct_runner(self):
        provider = FakeProvider(default_response="direct reply")
        result, sink = _run(DirectRunner(provider.stream))
        _assert_finished_has_duration(sink, result.status)
        assert result.status == "completed"

    def test_direct_runner_failed_path_also_timed(self):
        provider = FakeProvider(default_response="x")
        provider.fail_always = RuntimeError("boom")
        result, sink = _run(DirectRunner(provider.stream))
        _assert_finished_has_duration(sink, result.status)
        assert result.status == "failed"

    def test_agent_runner(self):
        provider = FakeProvider(default_response="الرد النهائي للوكيل")
        tmp = tempfile.mkdtemp(prefix="tsk609-agent-")

        def _loop_factory(frame_sink):
            tools = AgentTools(
                file_manager=FileManager(tmp),
                command_runner=CommandRunner(cwd=tmp, auto_approve=True),
                project_root=tmp,
            )
            return AgentLoop(tools=tools,
                             send_fn=lambda p, h, s: provider.send(p, h, s),
                             ws_send_fn=frame_sink,
                             max_iterations=2)

        result, sink = _run(AgentRunner(_loop_factory), mode="agent")
        _assert_finished_has_duration(sink, result.status)

    def test_delegate_runner(self):
        # دورة brief → implement → review(REJECT) — نهاية حاسمة
        # (نفس سيناريو عدة العقود T-041).
        provider = FakeProvider(responses=[
            "<brief>خطة</brief>", "تم التنفيذ",
            "[VERDICT]: REJECT\n[SUMMARY]: مرفوض"])
        result, sink = _run(DelegateRunner(DelegateBridge(provider)),
                            mode="delegate")
        _assert_finished_has_duration(sink, result.status)


# ═══════════ 2. PM-04: توقيت المصادر في ContextEngine.gather ═══════════

class _StubSource:
    def __init__(self, kind, items=None, sleep_s=0.0, fail=False):
        self.kind = kind
        self._items = items or []
        self._sleep = sleep_s
        self._fail = fail

    def collect(self, request, scan):
        if self._sleep:
            time.sleep(self._sleep)
        if self._fail:
            raise RuntimeError("مصدر معطوب")
        return list(self._items)


class TestGatherTimesEachSource:
    def test_all_sources_timed_by_kind(self, tmp_path):
        eng = ContextEngine([_StubSource("mention"), _StubSource("keyword")])
        bundle = eng.gather(ContextRequest(message="x",
                                           project_root=tmp_path))
        assert set(bundle.source_timings_ms) == {"mention", "keyword"}
        assert all(isinstance(v, int) and v >= 0
                   for v in bundle.source_timings_ms.values())

    def test_slow_source_measured(self, tmp_path):
        eng = ContextEngine([_StubSource("slow", sleep_s=0.05)])
        bundle = eng.gather(ContextRequest(message="x",
                                           project_root=tmp_path))
        assert bundle.source_timings_ms["slow"] >= 40  # ≥ 40ms من 50ms نوم

    def test_failing_source_still_timed_and_swallowed(self, tmp_path):
        """نفس تسامح legacy: الاستثناء يُبتلع — والمصدر الفاشل يُرصد."""
        item = ContextItem(source_kind="ok", path="a.py", content="x")
        eng = ContextEngine([_StubSource("broken", fail=True),
                             _StubSource("ok", items=[item])])
        bundle = eng.gather(ContextRequest(message="x",
                                           project_root=tmp_path))
        assert "broken" in bundle.source_timings_ms
        assert bundle.paths() == ["a.py"]  # الجمع لم يسقط

    def test_facade_exposes_timings_default_field(self, tmp_path):
        """MessageContext.source_timings_ms — للمصادر السبعة القياسية
        الخمسة الافتراضية (mention/keyword/symbol/semantic/structure)."""
        (tmp_path / "app.py").write_text("print('x')\n", encoding="utf-8")
        mc = gather_message_context(tmp_path, "اشرح app.py")
        assert isinstance(mc.source_timings_ms, dict)
        assert "mention" in mc.source_timings_ms
        assert "structure" in mc.source_timings_ms
        assert all(isinstance(v, int) for v in mc.source_timings_ms.values())

    def test_field_is_default_compatible(self):
        """بناء MessageContext بلا الحقل الجديد يبقى صالحًا —
        (goldens/مستهلكون قدامى لا يتأثرون)."""
        from context.facade import MessageContext
        mc = MessageContext(mentioned_files=[], user_text_with_files="x",
                            project_context="")
        assert mc.source_timings_ms == {}


# ═══════════ 3. PM-01/02: حقول إطار done في المسار المباشر (e2e) ═══════════

class FakeWS:
    def __init__(self):
        self.sent = []

    def send(self, payload: str):
        self.sent.append(payload)

    def frames(self):
        return [json.loads(p) for p in self.sent]


def _mk_sctx(tmp_path, provider):
    from core.session_context import SessionContext
    proj = tmp_path / "proj"
    proj.mkdir(exist_ok=True)
    (proj / "app.py").write_text("print('x')\n", encoding="utf-8")
    handle = server._server_handle_factory(str(proj))
    ws = FakeWS()
    sctx = SessionContext(
        send=lambda m: ws.send(json.dumps(m, ensure_ascii=False)),
        project=handle,
        model_provider=provider,
    )
    return sctx, ws


def _wait_for_frame(ws, ftype, timeout_s=10.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        for f in ws.frames():
            if f.get("type") == ftype:
                return f
        time.sleep(0.02)
    raise AssertionError(f"لم يصل إطار {ftype} خلال {timeout_s}s — "
                         f"الأنواع الواصلة: {[f.get('type') for f in ws.frames()]}")


REPLY = "هذا شرح تجريبي للمشروع بلا أي إجراءات."


class TestDoneFrameCarriesMetrics:
    @pytest.fixture(autouse=True)
    def fresh_registry(self, monkeypatch):
        monkeypatch.setattr(server, "execution_registry",
                            ExecutionRegistry())

    def test_chat_done_frame_has_duration_and_tokens(self, monkeypatch,
                                                     tmp_path):
        """chat → المسار المباشر → إطار done يحمل الحقلين الجديدين
        بجانب المفاتيح التاريخية (إضافة فقط — لا كسر بنية)."""
        sctx, ws = _mk_sctx(tmp_path, FakeProvider(default_response=REPLY))
        server._dispatch_chat_message(None, sctx, "اشرح المشروع",
                                      "chat", {})
        done = _wait_for_frame(ws, "done")
        # الحقول الجديدة (TSK-609)
        assert isinstance(done["duration_ms"], int)
        assert done["duration_ms"] >= 0
        assert done["token_estimate"] == \
            CharsPerTokenEstimator().estimate(REPLY)
        assert done["token_estimate"] >= 1
        # المفاتيح التاريخية باقية (TSK-101: chat → actions فارغة دائمًا)
        assert done["actions"] == []
        assert "options" in done and "summary" in done

    def test_server_source_has_no_new_token_constants(self):
        """PM-01: التقدير عبر CharsPerTokenEstimator المركزي حصريًا —
        لا ثابت تقريب جديد. المستهلك الفعلي انتقل إلى
        core/chat_dispatch.py (TSK-612/ADR-002)؛ استيراد server.py
        القديم كان ميتًا وأُزيل في TSK-CEV-120 (CEV-F-011, D-18) —
        الحارس يفحص الوحدة المالكة للمنطق لا الغلاف."""
        dispatch_src = (pathlib.Path(server.__file__).parent
                        / "core" / "chat_dispatch.py").read_text(
                            encoding="utf-8")
        assert "CharsPerTokenEstimator" in dispatch_src
        src = pathlib.Path(server.__file__).read_text(encoding="utf-8")
        assert "len(full_response) // 4" not in src
        assert "len(full_response) // 4" not in dispatch_src
