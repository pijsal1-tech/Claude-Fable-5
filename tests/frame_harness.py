# -*- coding: utf-8 -*-
"""Frame-Parity Harness (T-111, R-804): تسجيل ومقارنة تسلسل إطارات WS.

لماذا
-----
بند قبول R-804 الحرفي: «chain run executes on a worker with
byte-identical WS frame sequence vs in-proc». هذا الموديول هو أداة
الإثبات: يسجّل **تسلسل الإطارات الكامل** كما يراه العميل (عبر
``server._RunnerWSAdapter`` — نفس المحوّل الوحيد في الإنتاج) لنفس
تشغيلة السلسلة الثابتة على المسارين، ثم يقارن **بايتات** التسلسلين
بعد تطبيع الحقول غير الحتمية بطبيعتها (أزمنة/ميزانية/هوية run).

الاستخدام (انظر tests/README.md):

    frames_a = record_inproc_chain_frames(tmp, provider_factory, REQ)
    frames_b = record_worker_chain_frames(tmp, provider_factory, REQ,
                                          redis_client)
    assert_frame_parity(frames_a.frames, frames_b.frames)

حساسية الـ harness مُثبتة باختبار طفرة متعمدة (أي تغيير حرف واحد في
أي إطار = فشل) — أداة قياس لا تكشف الخلل ليست أداة قياس.
"""
from __future__ import annotations

import json
import pathlib
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import server
from chain.bridge import ChainBridge
from core.execution import ExecutionRegistry
from core.runner import RunRequest, RunResult
from runners.chain import ChainRunner

JOIN_TIMEOUT = 15.0

#: حقول غير حتمية بين تشغيلتين — نفس قائمة test_dispatch_parity
#: (T-040): أزمنة وميزانية وهوية run عشوائية. كل ما عداها **بايتات**.
NONDETERMINISTIC_KEYS = ("duration_ms", "elapsed_seconds", "budget",
                         "run_id")


@dataclass
class RecordedRun:
    """ناتج تسجيلة واحدة: الإطارات بترتيب الوصول + النتيجة."""
    frames: list[dict] = field(default_factory=list)
    result: RunResult | None = None


# ═══════════════════════════════════════════════════════
#   التطبيع + التسوية البايتية
# ═══════════════════════════════════════════════════════

def normalize_frame(frame: dict) -> dict:
    """يطبّع الحقول غير الحتمية فقط — البقية تبقى حرفيًّا.

    نص العرض الحامل للمدة (``... (123ms)``) يُطبَّع لعلامة نوعه —
    نفس قاعدة test_dispatch_parity (T-040).
    """
    out: dict = {}
    for k, v in frame.items():
        if k in NONDETERMINISTIC_KEYS:
            continue
        if k == "text" and "ms)" in str(v):
            out[k] = "<timed-text>"
        elif k == "text" and "s)" in str(v) and "calls" in str(v):
            out[k] = "<timed-text>"
        else:
            out[k] = v
    return out


def frames_to_bytes(frames: list[dict]) -> list[bytes]:
    """تسلسل إطارات → تسلسل بايتات قانوني (JSON مفروز المفاتيح).

    المقارنة على البايتات هي **التجسيد الحرفي** لبند «byte-identical»:
    أي فرق — نوع إطار، حقل، قيمة، ترتيب — يغيّر البايتات.
    """
    return [json.dumps(normalize_frame(f), ensure_ascii=False,
                       sort_keys=True).encode("utf-8")
            for f in frames]


def assert_frame_parity(frames_a: list[dict], frames_b: list[dict],
                        label_a: str = "in-proc",
                        label_b: str = "worker") -> None:
    """يفشل بـ AssertionError مفصّل عند أول اختلاف بايتي."""
    bytes_a = frames_to_bytes(frames_a)
    bytes_b = frames_to_bytes(frames_b)
    assert len(bytes_a) == len(bytes_b), (
        f"عدد الإطارات مختلف: {label_a}={len(bytes_a)} "
        f"vs {label_b}={len(bytes_b)}\n"
        f"{label_a}: {[f.get('type') for f in frames_a]}\n"
        f"{label_b}: {[f.get('type') for f in frames_b]}")
    for i, (a, b) in enumerate(zip(bytes_a, bytes_b)):
        assert a == b, (
            f"إطار #{i} غير مطابق بايت-بايت:\n"
            f"{label_a}: {a.decode('utf-8')}\n"
            f"{label_b}: {b.decode('utf-8')}")


# ═══════════════════════════════════════════════════════
#   المسجّلان — نفس التشغيلة الثابتة على المسارين
# ═══════════════════════════════════════════════════════

def _make_bridge(base: pathlib.Path, provider: Any) -> ChainBridge:
    project = base / "project"
    project.mkdir(parents=True, exist_ok=True)
    return ChainBridge(provider=provider, project_root=str(project),
                       runs_dir=base / "runs")


def record_inproc_chain_frames(
        base: pathlib.Path,
        provider_factory: Callable[[], Any],
        request_text: str,
        force_strategy: str = "direct") -> RecordedRun:
    """المسار التاريخي حرفيًّا: ChainRunner + _RunnerWSAdapter."""
    rec = RecordedRun()
    bridge = _make_bridge(base / "inproc", provider_factory())
    ticket = ExecutionRegistry().register("chain")
    sink = server._RunnerWSAdapter(rec.frames.append)
    rec.result = ChainRunner(bridge, force_strategy=force_strategy,
                             join_timeout_s=JOIN_TIMEOUT).run(
        RunRequest(mode="chain", message=request_text), ticket, sink)
    return rec


def record_worker_chain_frames(
        base: pathlib.Path,
        provider_factory: Callable[[], Any],
        request_text: str,
        redis_client: Any,
        force_strategy: str = "direct",
        timeout_s: float = 20.0) -> RecordedRun:
    """مسار worker كاملًا عبر Redis حقيقي: نفس ChainRunner لكن داخل
    Worker منفصل (خيط يحاكي عملية مستقلة)، والإطارات تعود للعميل عبر
    ev:<run_id> ثم **نفس** ``_RunnerWSAdapter``.

    العزل بمفاتيح uuid لكل تسجيلة — لا flushdb (عقد T-109).
    """
    from core.backends_redis import RedisEventBusBackend, RedisWorkQueue
    from worker import Worker, WorkerDispatchClient

    tag = uuid.uuid4().hex[:12]
    prefix, qstream = f"ev-{tag}:", f"wq-{tag}:runs"

    def _factory(payload: dict) -> ChainRunner:
        return ChainRunner(
            _make_bridge(base / "worker", provider_factory()),
            force_strategy=force_strategy, join_timeout_s=JOIN_TIMEOUT)

    worker = Worker(
        RedisWorkQueue(client=redis_client, stream=qstream),
        RedisEventBusBackend(client=redis_client, stream_prefix=prefix),
        redis_client, f"parity-{tag}", runner_factory=_factory)
    t = threading.Thread(target=worker.run_once,
                         kwargs={"block_ms": 5000}, daemon=True)
    t.start()

    rec = RecordedRun()
    dispatch = WorkerDispatchClient(
        RedisWorkQueue(client=redis_client, stream=qstream),
        redis_client, stream_prefix=prefix, timeout_s=timeout_s)
    ticket = ExecutionRegistry().register("chain")
    sink = server._RunnerWSAdapter(rec.frames.append)
    rec.result = dispatch.run(
        RunRequest(mode="chain", message=request_text,
                   metadata={"force_strategy": force_strategy}),
        ticket, sink)
    t.join(timeout=timeout_s)
    return rec
