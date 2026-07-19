# -*- coding: utf-8 -*-
"""T-044 (R-601): Crash Resume — kill/resume E2E + drift refusal + discard.

الأدلة المطلوبة (acceptance):
- kill-after-step-2-of-5: الاستكمال ينفّذ الخطوات 3–5 **مرة واحدة
  بالضبط** (عدّاد استدعاءات المزود = 3، نتائج 1–2 محفوظة حرفيًّا).
- hash-mismatch: ملف متغيّر/مفقود منذ اللقطة ⇒ رفض بإطار
  ``chain_resume_refused`` + تقرير انجراف — صفر استدعاءات مزود.
- discard: يحذف حالة الـ run بالكامل — ``can_resume`` = False بعدها.
- regression: الـ runs العادية غير المنقطعة لا تظهر في المسح ولا
  تُستأنف.
"""
from __future__ import annotations

import json
import pathlib
import threading
import time

import pytest

from chain.bridge import ChainBridge, _build_project_snapshot
from chain.executor import ChainExecutor
from chain.models import ChainRun, ChainStep, ExecutionPolicy
from chain.resume import DriftReport, check_drift, rebuild_run, scan_resumable
from tests.fakes.fake_provider import FakeProvider

JOIN_TIMEOUT = 10.0

PROJECT_FILE = "a.py"
PROJECT_CONTENT = "print('snapshot me')\n"


# ═══════════════ helpers ═══════════════

class FrameSink:
    """يجمع إطارات WS ويوفر انتظار إطار بنوع معيّن."""

    def __init__(self):
        self.frames: list[dict] = []
        self._lock = threading.Lock()

    def __call__(self, msg: dict):
        with self._lock:
            self.frames.append(msg)

    def wait_for(self, frame_type: str, timeout: float = 5.0) -> dict | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                for f in self.frames:
                    if f.get("type") == frame_type:
                        return f
            time.sleep(0.01)
        return None

    def of_type(self, frame_type: str) -> list[dict]:
        with self._lock:
            return [f for f in self.frames if f.get("type") == frame_type]


def _five_step_run(run_id: str = "run-e2e00001") -> ChainRun:
    """سلسلة خطية 1→2→3→4→5 — كل خطوة على دور executor."""
    steps = [
        ChainStep(id=f"s{i}", name=f"Step {i}", stage="execute",
                  agent_role="executor", prompt_template=f"do step {i}",
                  depends_on=([f"s{i - 1}"] if i > 1 else []))
        for i in range(1, 6)
    ]
    return ChainRun(run_id=run_id, steps=steps, policy=ExecutionPolicy())


def _crashing_provider(crash_at_call: int = 3) -> FakeProvider:
    """مزود ينجح حتى الاستدعاء (crash_at_call - 1) ثم ينهار."""
    counter = {"n": 0}

    def responder(prompt, history, system_prompt):
        counter["n"] += 1
        if counter["n"] >= crash_at_call:
            raise RuntimeError("simulated crash (kill -9)")
        return f"R{counter['n']}"

    return FakeProvider(responder=responder)


def _project_with_file(tmp_path: pathlib.Path) -> pathlib.Path:
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    (project / PROJECT_FILE).write_text(PROJECT_CONTENT, encoding="utf-8")
    return project


def _kill_after_step2(tmp_path: pathlib.Path,
                      mark_running: bool = False) -> tuple[pathlib.Path, pathlib.Path, str]:
    """يشغّل 5 خطوات وينهار عند الخطوة 3 — يرجع (project, runs_dir, run_id).

    ``mark_running=True`` يحاكي kill حقيقيًا (state عالق على running)
    بدل الانهيار المرصود (failed) — كلاهما قابل للاستكمال.
    """
    project = _project_with_file(tmp_path)
    runs_dir = tmp_path / "runs"
    run = _five_step_run()
    run.project_snapshot = _build_project_snapshot(
        str(project), {PROJECT_FILE: PROJECT_CONTENT})
    run_dir = runs_dir / run.run_id

    executor = ChainExecutor(_crashing_provider(crash_at_call=3),
                             run_dir=str(run_dir))
    executor.execute(run)

    assert run.status == "failed"
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    done = [s["id"] for s in state["steps"] if s["status"] == "success"]
    assert done == ["s1", "s2"], "الانهيار المفترض بعد الخطوة 2 بالضبط"

    if mark_running:
        state["status"] = "running"
        (run_dir / "state.json").write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8")

    return project, runs_dir, run.run_id


def _resume_bridge(project: pathlib.Path, runs_dir: pathlib.Path,
                   provider: FakeProvider) -> ChainBridge:
    """جسر جديد (= إقلاع سيرفر جديد) فوق نفس runs_dir."""
    return ChainBridge(provider=provider, project_root=str(project),
                       runs_dir=runs_dir)


def _join_active(bridge: ChainBridge) -> None:
    thread = bridge._active_thread
    assert thread is not None
    thread.join(timeout=JOIN_TIMEOUT)
    assert not thread.is_alive(), "resume thread لم ينتهِ في المهلة"


# ═══════════════ kill / resume E2E ═══════════════

class TestKillResumeE2E:

    def test_resume_runs_steps_3_to_5_exactly_once(self, tmp_path):
        """القبول الحرفي: kill بعد 2/5 → الاستكمال ينفّذ 3–5 مرة واحدة."""
        project, runs_dir, run_id = _kill_after_step2(tmp_path)

        fixed = FakeProvider(responses=["R3", "R4", "R5"])
        bridge = _resume_bridge(project, runs_dir, fixed)
        sink = FrameSink()

        assert bridge.resume_run(run_id, sink) is True
        _join_active(bridge)

        # exactly-once: 3 استدعاءات فقط في الرِجل المستأنفة (لا 1 ولا 2)
        assert fixed.call_count == 3
        finished = sink.wait_for("chain_finished", timeout=1.0)
        assert finished is not None and finished["status"] == "completed"

        # الحالة النهائية على القرص: نتائج 1–2 الأصلية + 3–5 الجديدة
        state = json.loads(
            (runs_dir / run_id / "state.json").read_text(encoding="utf-8"))
        assert state["status"] == "completed"
        assert state["results"] == {
            "s1": "R1", "s2": "R2", "s3": "R3", "s4": "R4", "s5": "R5"}
        assert all(s["status"] == "success" for s in state["steps"])

    def test_resume_after_literal_kill_status_running(self, tmp_path):
        """state عالق على running (kill -9 منتصف خطوة) يُستأنف كذلك."""
        project, runs_dir, run_id = _kill_after_step2(tmp_path,
                                                      mark_running=True)
        fixed = FakeProvider(responses=["R3", "R4", "R5"])
        bridge = _resume_bridge(project, runs_dir, fixed)
        sink = FrameSink()

        assert bridge.resume_run(run_id, sink) is True
        _join_active(bridge)
        assert fixed.call_count == 3
        state = json.loads(
            (runs_dir / run_id / "state.json").read_text(encoding="utf-8"))
        assert state["status"] == "completed"

    def test_resumed_frame_reports_progress(self, tmp_path):
        project, runs_dir, run_id = _kill_after_step2(tmp_path)
        bridge = _resume_bridge(project, runs_dir,
                                FakeProvider(responses=["R3", "R4", "R5"]))
        sink = FrameSink()
        assert bridge.resume_run(run_id, sink) is True
        _join_active(bridge)

        resumed = sink.of_type("chain_resumed")
        assert len(resumed) == 1
        assert resumed[0]["steps_done"] == 2
        assert resumed[0]["steps_total"] == 5

    def test_resume_finishes_ticket_with_final_state(self, tmp_path):
        """التذكرة تُنهى بحالة الـ run الفعلية — نفس عقد start_chain."""
        from core.execution import ExecutionRegistry
        project, runs_dir, run_id = _kill_after_step2(tmp_path)
        bridge = _resume_bridge(project, runs_dir,
                                FakeProvider(responses=["R3", "R4", "R5"]))
        ticket = ExecutionRegistry().register("chain")
        sink = FrameSink()

        assert bridge.resume_run(run_id, sink, ticket=ticket) is True
        _join_active(bridge)
        assert ticket.state == "completed"

    def test_resume_refused_while_chain_active(self, tmp_path):
        """انشغال الجسر يرفض الاستكمال — نفس حارس start_chain."""
        project, runs_dir, run_id = _kill_after_step2(tmp_path)
        slow = FakeProvider(responses=["R3", "R4", "R5"])
        slow.latency_s = 0.3
        bridge = _resume_bridge(project, runs_dir, slow)
        sink = FrameSink()
        assert bridge.resume_run(run_id, sink) is True

        sink2 = FrameSink()
        assert bridge.resume_run(run_id, sink2) is False
        assert len(sink2.of_type("chain_error")) == 1
        _join_active(bridge)


# ═══════════════ drift refusal ═══════════════

class TestDriftRefusal:

    def test_changed_file_refuses_with_report(self, tmp_path):
        project, runs_dir, run_id = _kill_after_step2(tmp_path)
        # انجراف: الملف تغيّر منذ اللقطة
        (project / PROJECT_FILE).write_text("print('MUTATED')\n",
                                            encoding="utf-8")
        fixed = FakeProvider(responses=["R3", "R4", "R5"])
        bridge = _resume_bridge(project, runs_dir, fixed)
        sink = FrameSink()

        assert bridge.resume_run(run_id, sink) is False
        refused = sink.of_type("chain_resume_refused")
        assert len(refused) == 1
        report = refused[0]["drift_report"]
        assert report["has_drift"] is True
        assert PROJECT_FILE in report["changed"]
        # صفر تنفيذ ضد ملفات منجرفة
        assert fixed.call_count == 0
        # الحالة لم تُمس — discard لاحق ما زال ممكنًا
        assert ChainExecutor.can_resume(runs_dir / run_id)

    def test_missing_file_refuses_with_report(self, tmp_path):
        project, runs_dir, run_id = _kill_after_step2(tmp_path)
        (project / PROJECT_FILE).unlink()
        bridge = _resume_bridge(project, runs_dir, FakeProvider())
        sink = FrameSink()

        assert bridge.resume_run(run_id, sink) is False
        report = sink.of_type("chain_resume_refused")[0]["drift_report"]
        assert PROJECT_FILE in report["missing"]

    def test_unchanged_files_pass_drift_check(self, tmp_path):
        project = _project_with_file(tmp_path)
        snap = _build_project_snapshot(str(project),
                                       {PROJECT_FILE: PROJECT_CONTENT})
        assert snap is not None
        report = check_drift(snap.to_dict(), str(project))
        assert report.has_drift is False
        assert report.matched == [PROJECT_FILE]

    def test_empty_snapshot_means_no_drift(self, tmp_path):
        # لقطة غائبة (run بلا ملفات) — لا شيء نتحقق منه ⇒ لا رفض
        assert check_drift(None, str(tmp_path)).has_drift is False
        assert check_drift({}, str(tmp_path)).has_drift is False


# ═══════════════ discard ═══════════════

class TestDiscard:

    def test_discard_cleans_state(self, tmp_path):
        project, runs_dir, run_id = _kill_after_step2(tmp_path)
        bridge = _resume_bridge(project, runs_dir, FakeProvider())

        assert ChainExecutor.can_resume(runs_dir / run_id)
        assert bridge.discard_run(run_id) is True
        # الحالة اختفت بالكامل: لا مجلد، لا استكمال، لا ظهور في المسح
        assert not (runs_dir / run_id).exists()
        assert ChainExecutor.can_resume(runs_dir / run_id) is False
        assert scan_resumable(runs_dir) == []

    def test_discard_unknown_run_is_false(self, tmp_path):
        project = _project_with_file(tmp_path)
        bridge = ChainBridge(provider=FakeProvider(),
                             project_root=str(project),
                             runs_dir=tmp_path / "runs")
        assert bridge.discard_run("run-nope1234") is False

    def test_discard_then_resume_refused(self, tmp_path):
        project, runs_dir, run_id = _kill_after_step2(tmp_path)
        bridge = _resume_bridge(project, runs_dir, FakeProvider())
        assert bridge.discard_run(run_id) is True

        sink = FrameSink()
        assert bridge.resume_run(run_id, sink) is False
        assert len(sink.of_type("chain_error")) == 1


# ═══════════════ startup scan ═══════════════

class TestStartupScan:

    def test_scan_finds_interrupted_run(self, tmp_path):
        project, runs_dir, run_id = _kill_after_step2(tmp_path)
        found = scan_resumable(runs_dir)
        assert len(found) == 1
        assert found[0]["run_id"] == run_id
        assert found[0]["status"] == "failed"
        assert found[0]["steps_done"] == 2
        assert found[0]["steps_total"] == 5

    def test_scan_ignores_completed_runs(self, tmp_path):
        """regression: الـ runs العادية المكتملة لا تظهر ولا تُستأنف."""
        project = _project_with_file(tmp_path)
        runs_dir = tmp_path / "runs"
        run = _five_step_run("run-normal01")
        executor = ChainExecutor(
            FakeProvider(responses=["R1", "R2", "R3", "R4", "R5"]),
            run_dir=str(runs_dir / run.run_id))
        executor.execute(run)
        assert run.status == "completed"

        assert scan_resumable(runs_dir) == []
        assert ChainExecutor.can_resume(runs_dir / run.run_id) is False

    def test_scan_ignores_junk(self, tmp_path):
        runs_dir = tmp_path / "runs"
        (runs_dir / "empty-dir").mkdir(parents=True)
        (runs_dir / "stray.txt").write_text("junk", encoding="utf-8")
        bad = runs_dir / "run-corrupt1"
        bad.mkdir()
        (bad / "state.json").write_text("{not json", encoding="utf-8")
        assert scan_resumable(runs_dir) == []

    def test_scan_missing_dir_is_empty(self, tmp_path):
        assert scan_resumable(tmp_path / "does-not-exist") == []

    def test_bridge_list_resumable_delegates(self, tmp_path):
        project, runs_dir, run_id = _kill_after_step2(tmp_path)
        bridge = _resume_bridge(project, runs_dir, FakeProvider())
        assert [r["run_id"] for r in bridge.list_resumable()] == [run_id]


# ═══════════════ rebuild_run (state round-trip) ═══════════════

class TestRebuildRun:

    def test_success_steps_survive_with_results(self, tmp_path):
        _, runs_dir, run_id = _kill_after_step2(tmp_path)
        state = ChainExecutor.load_state(runs_dir / run_id)
        assert state is not None
        run = rebuild_run(state)

        s1, s2 = run.get_step("s1"), run.get_step("s2")
        assert s1 is not None and s1.status == "success" and s1.result == "R1"
        assert s2 is not None and s2.status == "success" and s2.result == "R2"
        assert run.results["s1"] == "R1" and run.results["s2"] == "R2"

    def test_non_success_steps_reset_to_pending(self, tmp_path):
        _, runs_dir, run_id = _kill_after_step2(tmp_path)
        state = ChainExecutor.load_state(runs_dir / run_id)
        assert state is not None
        run = rebuild_run(state)

        for sid in ("s3", "s4", "s5"):
            step = run.get_step(sid)
            assert step is not None
            assert step.status == "pending"
            assert step.error_message == ""

        # get_ready_steps يرشّح s3 فقط (تبعياته ناجحة) — أساس exactly-once
        assert [s.id for s in run.get_ready_steps()] == ["s3"]

    def test_prompt_template_round_trips(self, tmp_path):
        """بدون prompt_template في الـ state الاستكمال يبني برومبتات فارغة."""
        _, runs_dir, run_id = _kill_after_step2(tmp_path)
        state = ChainExecutor.load_state(runs_dir / run_id)
        assert state is not None
        run = rebuild_run(state)
        s3 = run.get_step("s3")
        assert s3 is not None and s3.prompt_template == "do step 3"

    def test_run_rebuilt_pending_with_fresh_budget(self, tmp_path):
        _, runs_dir, run_id = _kill_after_step2(tmp_path)
        state = ChainExecutor.load_state(runs_dir / run_id)
        assert state is not None
        run = rebuild_run(state)
        assert run.status == "pending"          # المنفّذ ينقلها running
        assert run.budget.attempted_calls == 0  # ميزانية جديدة للرِجل الجديدة
        assert run.policy.max_provider_calls == \
            state["policy"]["max_provider_calls"]

    def test_snapshots_round_trip(self, tmp_path):
        _, runs_dir, run_id = _kill_after_step2(tmp_path)
        state = ChainExecutor.load_state(runs_dir / run_id)
        assert state is not None
        run = rebuild_run(state)
        assert run.project_snapshot is not None
        assert PROJECT_FILE in run.project_snapshot.relevant_file_hashes


# ═══════════════ DriftReport shape ═══════════════

def test_drift_report_to_dict_shape():
    r = DriftReport(matched=["a"], changed=["b"], missing=["c"])
    assert r.to_dict() == {
        "matched": ["a"], "changed": ["b"], "missing": ["c"],
        "has_drift": True,
    }
    assert DriftReport().has_drift is False
