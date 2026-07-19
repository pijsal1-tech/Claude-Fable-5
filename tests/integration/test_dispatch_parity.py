# -*- coding: utf-8 -*-
"""T-040/T-041 (R-501): مطابقة الإرسال — المسارات القديمة vs runners.

المسارات القديمة حُذفت من server.py في T-041 — دوال _legacy_*_frames
هنا إعادة إنتاج حرفية لسلوكها المسجّل (مواصفة تنفيذية)، تثبت أن
مسار الإرسال الموحّد الوحيد يُنتج نفس الإطارات للواجهة:
- direct: إطارات chunk متطابقة بايت-بايت مع stream worker المحذوف.
- chain: نفس تسلسل الإطارات ونفس الحقول المستقرة (الزمن/الميزانية/
  هوية الـ run تُطبَّع — غير حتمية بطبيعتها).
- agent (T-041): نفس إطارات AgentLoop + نفس تقطيع الرد النهائي (80)
  الذي كان يفعله ws_handler بعد حلقة الاستطلاع المحذوفة.
- delegate (T-041): نفس أحداث الجسر كإطارات حرفية؛ waiting_approval
  يترك التذكرة حية (نفس دلالة المسار القديم).
"""
from __future__ import annotations

import pathlib
import queue
import threading

import pytest

import server
from actions.command_runner import CommandRunner
from actions.file_manager import FileManager
from chain.agent_loop import AgentLoop
from chain.agent_tools import AgentTools
from chain.bridge import ChainBridge
from chain.delegate import DelegateBridge
from core.execution import ExecutionRegistry
from core.runner import RunRequest
from runners.agent import AgentRunner
from runners.chain import ChainRunner
from runners.delegate import DelegateRunner
from runners.direct import DirectRunner
from tests.fakes.fake_provider import FakeProvider

JOIN_TIMEOUT = 15.0

# نص أطول من قطعة واحدة (FakeProvider يبث كل 8 محارف) — يثبت
# أن التقطيع نفسه متطابق لا مجرد النص الكلي.
DIRECT_REPLY = "امسك الرد المباشر الكامل — قطع متعددة تُبث تباعًا."


# ═════════ العلم والسلم القديم: محذوفان (T-041) ═════════

def test_legacy_dispatch_flag_deleted():
    """بند قبول T-041: العلم اختفى — مسار إرسال واحد لا يُعكس."""
    assert not hasattr(server, "_legacy_dispatch")


def test_runners_map_covers_all_modes():
    """الخريطة الموحّدة تغطي الأوضاع الأربعة — لا وضع خارج العقد."""
    assert set(server.RUNNERS) == {"direct", "chain", "agent", "delegate"}


# ═══════════════════ direct: مطابقة بايت-بايت ═══════════════════

def _legacy_direct_frames(provider, prompt, history, system_prompt):
    """إعادة إنتاج حرفية لمسار الـ stream worker القديم في server.py."""
    frames: list[dict] = []
    chunk_queue: "queue.Queue" = queue.Queue()

    def _stream_worker():
        try:
            for chunk in provider.stream(prompt, history, system_prompt):
                chunk_queue.put(("chunk", chunk))
            chunk_queue.put(("done", None))
        except Exception as e:
            chunk_queue.put(("error", str(e)))

    t = threading.Thread(target=_stream_worker, daemon=True)
    t.start()
    full_response = ""
    while True:
        msg_type, payload = chunk_queue.get(timeout=10)
        if msg_type == "chunk":
            full_response += payload
            frames.append({"type": "chunk", "text": payload})
        elif msg_type == "done":
            break
        elif msg_type == "error":
            frames.append({"type": "error", "text": payload})
            break
    t.join(timeout=5)
    return frames, full_response


def _runner_direct_frames(provider, prompt, history, system_prompt):
    """مسار T-040: DirectRunner + _RunnerWSAdapter."""
    frames: list[dict] = []
    registry = ExecutionRegistry()
    ticket = registry.register("direct")
    sink = server._RunnerWSAdapter(frames.append)
    result = DirectRunner(provider.stream).run(
        RunRequest(mode="direct", message=prompt,
                   system_prompt=system_prompt,
                   context={"history": history}),
        ticket, sink)
    if result.status != "completed":
        frames.append({"type": "error",
                       "text": result.error or "الرد لم يكتمل"})
    return frames, result.text


def test_direct_parity_success():
    """نجاح: قوائم الإطارات متطابقة بايت-بايت + النص الكلي متطابق."""
    legacy_frames, legacy_text = _legacy_direct_frames(
        FakeProvider(default_response=DIRECT_REPLY),
        "اشرح الملف", [], "sys")
    runner_frames, runner_text = _runner_direct_frames(
        FakeProvider(default_response=DIRECT_REPLY),
        "اشرح الملف", [], "sys")

    assert runner_frames == legacy_frames
    assert runner_text == legacy_text == DIRECT_REPLY
    # أكثر من قطعة فعلاً — المطابقة على التقطيع لا النص فقط
    assert sum(1 for f in legacy_frames if f["type"] == "chunk") > 1


def test_direct_parity_provider_failure():
    """فشل المزود: كلاهما إطار error واحد بنفس النص، صفر chunks."""
    def failing():
        p = FakeProvider()
        p.fail_always = RuntimeError("provider dead")
        return p

    legacy_frames, _ = _legacy_direct_frames(failing(), "اشرح", [], "")
    runner_frames, _ = _runner_direct_frames(failing(), "اشرح", [], "")

    assert runner_frames == legacy_frames
    assert legacy_frames == [{"type": "error", "text": "provider dead"}]


def test_direct_runner_registers_direct_kind():
    """التذكرة بنوع direct — الوضع الأخير ينضم للسجل (VALID_KINDS)."""
    registry = ExecutionRegistry()
    ticket = registry.register("direct")
    assert ticket.kind == "direct"
    result = DirectRunner(FakeProvider(default_response="x").stream).run(
        RunRequest(mode="direct", message="hi"), ticket,
        server._RunnerWSAdapter(lambda m: None))
    assert result.status == "completed"
    assert ticket.state == "completed"


# ═══════════════════ chain: مطابقة التسلسل والحقول المستقرة ═══════════════════

# حقول غير حتمية بين تشغيلتين: أزمنة/ميزانية + هوية الـ run العشوائية
_NONDETERMINISTIC_KEYS = ("duration_ms", "elapsed_seconds", "budget",
                          "run_id")


def _normalize(frame: dict) -> dict:
    """يطبّع الحقول غير الحتمية — الزمن والميزانية وهوية الـ run."""
    out = {}
    for k, v in frame.items():
        if k in _NONDETERMINISTIC_KEYS:
            continue
        if k == "text" and "ms)" in str(v):
            # نص العرض يحمل المدة — نطبّعه لنوعه فقط
            out[k] = "<timed-text>"
        elif k == "text" and "s)" in str(v) and "calls" in str(v):
            out[k] = "<timed-text>"
        else:
            out[k] = v
    return out


def _make_bridge(tmp_path: pathlib.Path, provider) -> ChainBridge:
    project = tmp_path / "project"
    project.mkdir(parents=True, exist_ok=True)
    return ChainBridge(provider=provider, project_root=str(project),
                       runs_dir=tmp_path / "runs")


def _legacy_chain_frames(tmp_path, provider, request_text):
    """المسار القديم: start_chain مباشرة + join (كما في server.py)."""
    bridge = _make_bridge(tmp_path, provider)
    registry = ExecutionRegistry()
    ticket = registry.register("chain")
    frames: list[dict] = []
    run_id = bridge.start_chain(frames.append, request_text,
                                force_strategy="direct", ticket=ticket)
    assert run_id
    bridge._active_thread.join(timeout=JOIN_TIMEOUT)
    assert not bridge._active_thread.is_alive()
    return frames, ticket


def _runner_chain_frames(tmp_path, provider, request_text):
    """مسار T-040: ChainRunner + _RunnerWSAdapter فوق جسر مطابق."""
    bridge = _make_bridge(tmp_path, provider)
    registry = ExecutionRegistry()
    ticket = registry.register("chain")
    frames: list[dict] = []
    sink = server._RunnerWSAdapter(frames.append)
    result = ChainRunner(bridge, force_strategy="direct",
                         join_timeout_s=JOIN_TIMEOUT).run(
        RunRequest(mode="chain", message=request_text),
        ticket, sink)
    return frames, ticket, result


def test_chain_parity_success(tmp_path):
    """نجاح: نفس تسلسل الإطارات ونفس الحقول المستقرة عبر المسارين."""
    legacy_frames, legacy_ticket = _legacy_chain_frames(
        tmp_path / "legacy", FakeProvider(default_response="chain reply"),
        "نفّذ المهمة")
    runner_frames, runner_ticket, result = _runner_chain_frames(
        tmp_path / "runner", FakeProvider(default_response="chain reply"),
        "نفّذ المهمة")

    assert [_normalize(f) for f in runner_frames] == \
           [_normalize(f) for f in legacy_frames]
    assert legacy_ticket.state == runner_ticket.state == "completed"
    assert result.status == "completed"
    assert result.text == "chain reply"


def test_chain_parity_provider_failure(tmp_path):
    """فشل المزود: نفس إطارات الفشل، وكلا التذكرتين failed."""
    def failing():
        p = FakeProvider()
        p.fail_always = RuntimeError("chain provider dead")
        return p

    legacy_frames, legacy_ticket = _legacy_chain_frames(
        tmp_path / "legacy", failing(), "نفّذ المهمة")
    runner_frames, runner_ticket, result = _runner_chain_frames(
        tmp_path / "runner", failing(), "نفّذ المهمة")

    assert [_normalize(f) for f in runner_frames] == \
           [_normalize(f) for f in legacy_frames]
    assert legacy_ticket.state == runner_ticket.state == "failed"
    assert result.status == "failed"
    assert "chain provider dead" in result.error


# ═══════════════════ agent: مطابقة الإطارات والتقطيع ═══════════════════

AGENT_REPLY = ("الرد النهائي من الوكيل — نص أطول من قطعة واحدة حتى نثبت "
               "أن تقطيع الثمانين محرفًا نفسه متطابق حرفيًا لا النص الكلي فقط.")


def _make_agent_loop(tmp_path: pathlib.Path, provider, frame_sink):
    project = tmp_path / "project"
    project.mkdir(parents=True, exist_ok=True)
    tools = AgentTools(
        file_manager=FileManager(str(project)),
        command_runner=CommandRunner(cwd=str(project), auto_approve=True),
        project_root=str(project),
    )
    return AgentLoop(
        tools=tools,
        send_fn=lambda p, h, s: provider.send(p, h, s),
        ws_send_fn=frame_sink,
        max_iterations=2,
    )


def _legacy_agent_frames(tmp_path, provider):
    """إعادة إنتاج حرفية للمسار المحذوف: AgentLoop في thread + حلقة
    الاستطلاع (تُختزل لـ join لأن لا رسائل واردة هنا) ثم تقطيع الرد 80."""
    frames: list[dict] = []
    registry = ExecutionRegistry()
    ticket = registry.register("agent")
    loop = _make_agent_loop(tmp_path, provider, frames.append)
    result_box: list[str] = []
    t = threading.Thread(
        target=lambda: result_box.append(loop.run(
            "نفّذ المهمة", history=[], project_context="",
            run_id=ticket.run_id, step_id="step-agent-execute",
            ticket=ticket)),
        daemon=True)
    t.start()
    t.join(timeout=JOIN_TIMEOUT)
    assert not t.is_alive()
    full_response = result_box[0]
    chunk_size = 80
    for i in range(0, len(full_response), chunk_size):
        frames.append({"type": "chunk", "text": full_response[i:i + chunk_size]})
    return frames, full_response, ticket


def _runner_agent_frames(tmp_path, provider):
    """مسار T-041: AgentRunner + _RunnerWSAdapter."""
    frames: list[dict] = []
    registry = ExecutionRegistry()
    ticket = registry.register("agent")
    sink = server._RunnerWSAdapter(frames.append)
    runner = AgentRunner(
        lambda frame_sink: _make_agent_loop(tmp_path, provider, frame_sink))
    result = runner.run(
        RunRequest(mode="agent", message="نفّذ المهمة",
                   context={"history": [], "project_context": ""}),
        ticket, sink)
    return frames, result.text, ticket, result


def test_agent_parity_success(tmp_path):
    """نجاح: نفس إطارات الحلقة ونفس تقطيع الرد النهائي (80) حرفيًا."""
    legacy_frames, legacy_text, legacy_ticket = _legacy_agent_frames(
        tmp_path / "legacy", FakeProvider(default_response=AGENT_REPLY))
    runner_frames, runner_text, runner_ticket, result = _runner_agent_frames(
        tmp_path / "runner", FakeProvider(default_response=AGENT_REPLY))

    assert runner_frames == legacy_frames
    assert runner_text == legacy_text == AGENT_REPLY
    assert legacy_ticket.state == runner_ticket.state == "completed"
    assert result.status == "completed"
    # أكثر من قطعة chunk فعلاً — المطابقة على التقطيع لا النص فقط
    assert sum(1 for f in legacy_frames if f["type"] == "chunk") > 1


def test_agent_parity_cancellation(tmp_path):
    """إلغاء التذكرة قبل أول iteration ⇒ كلا المسارين cancelled."""
    def run_cancelled(builder):
        registry = ExecutionRegistry()
        ticket = registry.register("agent")
        ticket.cancel("مطابقة إلغاء")
        return builder(ticket)

    # المسار القديم: الحلقة نفسها ترصد الإلغاء وتُنهي التذكرة cancelled
    def legacy(ticket):
        loop = _make_agent_loop(tmp_path / "legacy",
                                FakeProvider(default_response=AGENT_REPLY),
                                lambda f: None)
        loop.run("نفّذ", ticket=ticket)
        return ticket.state

    # مسار الـ runner: نقطة تفتيش الإلغاء قبل بناء الحلقة أصلًا
    def runner(ticket):
        r = AgentRunner(lambda fs: _make_agent_loop(
            tmp_path / "runner",
            FakeProvider(default_response=AGENT_REPLY), fs))
        result = r.run(RunRequest(mode="agent", message="نفّذ"),
                       ticket, server._RunnerWSAdapter(lambda m: None))
        assert result.status == "cancelled"
        return ticket.state

    assert run_cancelled(legacy) == run_cancelled(runner) == "cancelled"


# ═══════════════════ delegate: مطابقة أحداث الجسر ═══════════════════

DELEGATE_SCRIPT = ["<brief>خطة العمل</brief>", "تم التنفيذ بنجاح",
                   "[VERDICT]: APPROVE\n[SUMMARY]: ممتاز"]


def _legacy_delegate_frames(provider, request_text):
    """المسار المحذوف: run_delegation مباشرة + إطارات {"type": et, **ed}."""
    bridge = DelegateBridge(provider)
    registry = ExecutionRegistry()
    ticket = registry.register("delegate")
    frames: list[dict] = []
    run = bridge.run_delegation(
        request_text, {"a.py": "x = 1"},
        on_event=lambda et, ed: frames.append({"type": et, **ed}),
        ticket=ticket)
    return frames, run, ticket, bridge


def _runner_delegate_frames(provider, request_text):
    """مسار T-041: DelegateRunner + _RunnerWSAdapter فوق جسر مطابق."""
    bridge = DelegateBridge(provider)
    registry = ExecutionRegistry()
    ticket = registry.register("delegate")
    frames: list[dict] = []
    sink = server._RunnerWSAdapter(frames.append)
    result = DelegateRunner(bridge).run(
        RunRequest(mode="delegate", message=request_text,
                   context={"files": {"a.py": "x = 1"}}),
        ticket, sink)
    return frames, result, ticket, bridge


def test_delegate_parity_waiting_approval(tmp_path):
    """دورة كاملة حتى waiting_approval: نفس الأحداث، وكلا التذكرتين
    تبقيان حيتين (المستخدم لم يحسم) ثم land يُنهيهما completed."""
    legacy_frames, legacy_run, legacy_ticket, legacy_bridge = \
        _legacy_delegate_frames(FakeProvider(responses=list(DELEGATE_SCRIPT)),
                                "نفّذ مهمة")
    runner_frames, result, runner_ticket, runner_bridge = \
        _runner_delegate_frames(FakeProvider(responses=list(DELEGATE_SCRIPT)),
                                "نفّذ مهمة")

    assert [_normalize(f) for f in runner_frames] == \
           [_normalize(f) for f in legacy_frames]
    assert legacy_run.status == "waiting_approval"
    assert result.status == "completed"          # تسليم — الأحداث أُغلقت
    # نفس الدلالة: التذكرة حية حتى يحسم المستخدم
    assert legacy_ticket.state == runner_ticket.state == "running"
    assert legacy_bridge.land() is runner_bridge.land() is True
    assert legacy_ticket.state == runner_ticket.state == "completed"


def test_delegate_parity_provider_failure(tmp_path):
    """فشل المزود في Brief: نفس أحداث delegate_error وكلا التذكرتين failed."""
    def failing():
        p = FakeProvider()
        p.fail_always = RuntimeError("delegate provider dead")
        return p

    legacy_frames, legacy_run, legacy_ticket, _ = \
        _legacy_delegate_frames(failing(), "نفّذ مهمة")
    runner_frames, result, runner_ticket, _ = \
        _runner_delegate_frames(failing(), "نفّذ مهمة")

    assert [_normalize(f) for f in runner_frames] == \
           [_normalize(f) for f in legacy_frames]
    assert legacy_run.status == "failed"
    assert result.status == "failed"
    assert "delegate provider dead" in result.error
    assert legacy_ticket.state == runner_ticket.state == "failed"
