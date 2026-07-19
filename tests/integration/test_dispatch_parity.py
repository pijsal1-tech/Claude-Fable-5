# -*- coding: utf-8 -*-
"""T-040 (R-501): مطابقة الإرسال — legacy vs runners خلف LEGACY_DISPATCH.

بنود القبول:
- العلم: الافتراضي legacy (غياب المتغير أو أي قيمة ≠ "0")؛
  LEGACY_DISPATCH=0 يفعّل مسار الـ runners.
- direct: نفس المدخلات ⇒ إطارات chunk متطابقة بايت-بايت بين
  المسار القديم (stream worker) ومسار DirectRunner + _RunnerWSAdapter.
- chain: نفس المدخلات ⇒ نفس تسلسل الإطارات ونفس الحقول المستقرة
  (الحقول الزمنية duration_ms/elapsed تُطبَّع — غير حتمية بطبيعتها).
- regression: flag=1 لا يغيّر شيئًا — المسار القديم يعمل حرفيًا كما كان
  (يغطيه بقاء كامل عدة الاختبارات الحالية خضراء + اختبار العلم هنا).
"""
from __future__ import annotations

import pathlib
import queue
import threading

import pytest

import server
from chain.bridge import ChainBridge
from core.execution import ExecutionRegistry
from core.runner import RunRequest
from runners.chain import ChainRunner
from runners.direct import DirectRunner
from tests.fakes.fake_provider import FakeProvider

JOIN_TIMEOUT = 15.0

# نص أطول من قطعة واحدة (FakeProvider يبث كل 8 محارف) — يثبت
# أن التقطيع نفسه متطابق لا مجرد النص الكلي.
DIRECT_REPLY = "امسك الرد المباشر الكامل — قطع متعددة تُبث تباعًا."


# ═══════════════════ العلم نفسه ═══════════════════

def test_flag_default_is_legacy(monkeypatch):
    monkeypatch.delenv("LEGACY_DISPATCH", raising=False)
    assert server._legacy_dispatch() is True


def test_flag_zero_enables_runners(monkeypatch):
    monkeypatch.setenv("LEGACY_DISPATCH", "0")
    assert server._legacy_dispatch() is False


def test_flag_other_values_stay_legacy(monkeypatch):
    for val in ("1", "true", "yes", ""):
        monkeypatch.setenv("LEGACY_DISPATCH", val)
        assert server._legacy_dispatch() is True, f"قيمة {val!r} يجب أن تبقى legacy"


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
