# -*- coding: utf-8 -*-
"""T-103 (R-802): اختبارات الطبقة الحلقية — حلقة لكل run، ثبات عبر
إعادة تحميل المخزن، وتدهور فشل الملخِّص إلى لا-حلقة بلا استثناء.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from context.memory_layers import (          # noqa: E402
    EPISODE_FORMAT,
    EPISODE_KIND,
    MAX_DECISION_CHARS,
    MAX_DECISIONS,
    EpisodeRecord,
    EpisodicLayer,
    RunDigest,
    heuristic_key_decisions,
)
from sessions.store import SessionStore      # noqa: E402


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> SessionStore:
    return SessionStore(tmp_path / "sessions")


@pytest.fixture()
def session_id(store: SessionStore) -> str:
    return store.create().id


def _digest(run_id: str = "run-1", **over) -> RunDigest:
    base = dict(
        run_id=run_id,
        goal="أنشئ صفحة تسجيل دخول",
        outcome="completed",
        files_touched=("static/login.html", "static/login.css"),
        step_results=(("plan", "الخطة: نموذج + تحقق\nتفاصيل أخرى"),
                      ("execute", "كتبت login.html بنجاح")),
        started_at="2026-07-20T10:00:00",
        completed_at="2026-07-20T10:05:00",
    )
    base.update(over)
    return RunDigest(**base)   # type: ignore[arg-type]


# ═════════════════ sidecar المخزن (T-103 hookup) ═════════════════

class TestStoreEpisodeSidecar:

    def test_append_creates_sidecar_not_touching_main_log(self, store,
                                                          session_id):
        store.append_message(session_id, "user", "مرحبا")
        main_before = store.data_path(session_id).read_bytes()
        meta_before = store.meta_path(session_id).read_text("utf-8")
        store.append_episode(session_id, {"kind": "episode", "run_id": "r"})
        assert store.episodes_path(session_id).is_file()
        # سجل الرسائل والـ meta لم يتغيرا — الحلقات مشتقة لا رسائل
        assert store.data_path(session_id).read_bytes() == main_before
        assert store.meta_path(session_id).read_text("utf-8") == meta_before
        assert store.read_meta(session_id).message_count == 1

    def test_replay_episodes_missing_sidecar_is_empty_not_error(
            self, store, session_id):
        result = store.replay_episodes(session_id)
        assert result.records == [] and result.torn_tail is False

    def test_replay_episodes_unknown_session_raises(self, store):
        with pytest.raises(FileNotFoundError):
            store.replay_episodes("nope")

    def test_append_episode_unknown_session_raises(self, store):
        with pytest.raises(FileNotFoundError):
            store.append_episode("nope", {"kind": "episode"})

    def test_torn_episode_tail_recovered_on_next_append(self, store,
                                                        session_id):
        store.append_episode(session_id, {"kind": "episode", "run_id": "a"})
        path = store.episodes_path(session_id)
        # صدمة: نصف سطر بلا \n
        with open(path, "ab") as f:
            f.write(b'{"kind": "epis')
        fresh = SessionStore(store.sessions_dir)
        fresh.append_episode(session_id, {"kind": "episode", "run_id": "b"})
        result = fresh.replay_episodes(session_id)
        assert result.torn_tail is False
        assert [r["run_id"] for r in result.records] == ["a", "b"]

    def test_delete_removes_episode_sidecar_too(self, store, session_id):
        store.append_episode(session_id, {"kind": "episode"})
        assert store.delete(session_id) is True
        assert not store.episodes_path(session_id).exists()


# ═════════════════ حلقة لكل run (بند القبول) ═════════════════

class TestPerRunEpisodes:

    def test_multi_run_fixture_one_episode_per_run_with_fields(
            self, store, session_id):
        """بند القبول: عدة runs ⇒ حلقة واحدة لكل run بحقول صحيحة."""
        layer = EpisodicLayer(store, session_id)
        for i in range(3):
            ep = layer.summarize_and_record(_digest(
                run_id=f"run-{i}",
                outcome="completed" if i < 2 else "failed"))
            assert ep is not None
        episodes = layer.episodes()
        assert [e.run_id for e in episodes] == ["run-0", "run-1", "run-2"]
        for e in episodes:
            assert e.goal == "أنشئ صفحة تسجيل دخول"
            assert e.files_touched == ("static/login.html",
                                       "static/login.css")
            assert e.started_at and e.completed_at and e.ts
            assert e.key_decisions   # الملخِّص الافتراضي أنتج نقاطًا
        assert episodes[2].outcome == "failed"
        assert len(layer.episodes_for_run("run-1")) == 1
        assert layer.episodes_for_run("run-1")[0].run_id == "run-1"

    def test_on_disk_record_matches_schema(self, store, session_id):
        layer = EpisodicLayer(store, session_id)
        layer.summarize_and_record(_digest())
        raw = store.episodes_path(session_id).read_text("utf-8").strip()
        rec = json.loads(raw)
        assert rec["kind"] == EPISODE_KIND
        assert rec["format"] == EPISODE_FORMAT
        assert set(rec) == {"kind", "format", "run_id", "goal", "outcome",
                            "files_touched", "key_decisions",
                            "started_at", "completed_at", "ts"}

    def test_custom_summarizer_is_used(self, store, session_id):
        layer = EpisodicLayer(store, session_id)
        ep = layer.summarize_and_record(
            _digest(), summarizer=lambda d: [f"قرار مخصص لـ {d.run_id}"])
        assert ep is not None
        assert ep.key_decisions == ("قرار مخصص لـ run-1",)


# ═════════════════ الثبات (بند القبول: reload) ═════════════════

class TestReloadDurability:

    def test_episodes_survive_store_reload(self, store, session_id):
        EpisodicLayer(store, session_id).summarize_and_record(_digest())
        # عملية جديدة تمامًا: مخزن جديد فوق نفس المجلد
        fresh_store = SessionStore(store.sessions_dir)
        fresh_layer = EpisodicLayer(fresh_store, session_id)
        episodes = fresh_layer.episodes()
        assert len(episodes) == 1
        assert episodes[0].run_id == "run-1"
        assert episodes[0].key_decisions

    def test_unknown_kind_and_future_format_skipped(self, store,
                                                    session_id):
        """توافق T-029: أنواع/إصدارات مستقبلية تُتخطى لا تُفجّر."""
        layer = EpisodicLayer(store, session_id)
        store.append_episode(session_id, {"kind": "checkpoint", "x": 1})
        layer.summarize_and_record(_digest(run_id="ok"))
        store.append_episode(session_id, {
            "kind": EPISODE_KIND, "format": EPISODE_FORMAT + 1,
            "run_id": "future"})
        episodes = layer.episodes()
        assert [e.run_id for e in episodes] == ["ok"]


# ═════════════════ التدهور (بند القبول: فشل الملخِّص) ═════════════════

class TestFailureDegradation:

    def test_summarizer_crash_degrades_to_no_episode(self, store,
                                                     session_id):
        layer = EpisodicLayer(store, session_id)

        def boom(digest):
            raise RuntimeError("provider down")

        ep = layer.summarize_and_record(_digest(), summarizer=boom)
        assert ep is None
        assert layer.last_error is not None
        assert "provider down" in layer.last_error
        assert layer.episodes() == []          # لا حلقة زائفة
        # الجلسة نفسها سليمة تمامًا — الـ run لم يتأثر
        assert store.exists(session_id)

    def test_write_failure_degrades_to_no_episode(self, store, session_id,
                                                  monkeypatch):
        layer = EpisodicLayer(store, session_id)

        def fail_append(sid, rec):
            raise OSError("disk full")

        monkeypatch.setattr(store, "append_episode", fail_append)
        ep = layer.summarize_and_record(_digest())
        assert ep is None
        assert "disk full" in (layer.last_error or "")

    def test_success_after_failure_clears_last_error(self, store,
                                                     session_id):
        layer = EpisodicLayer(store, session_id)
        layer.summarize_and_record(
            _digest(), summarizer=lambda d: 1 / 0)   # type: ignore
        assert layer.last_error is not None
        ep = layer.summarize_and_record(_digest(run_id="run-2"))
        assert ep is not None and layer.last_error is None
        assert [e.run_id for e in layer.episodes()] == ["run-2"]


# ═════════════════ الملخِّص الافتراضي ═════════════════

class TestHeuristicSummarizer:

    def test_first_nonempty_line_per_step_tagged(self):
        decisions = heuristic_key_decisions(_digest())
        assert decisions == ["[plan] الخطة: نموذج + تحقق",
                             "[execute] كتبت login.html بنجاح"]

    def test_caps_decisions_and_length(self):
        results = tuple((f"s{i}", "x" * 500) for i in range(10))
        decisions = heuristic_key_decisions(_digest(step_results=results))
        assert len(decisions) == MAX_DECISIONS
        assert all(len(d) <= MAX_DECISION_CHARS for d in decisions)
        assert decisions[0].endswith("…")

    def test_empty_results_yield_no_decisions(self):
        assert heuristic_key_decisions(
            _digest(step_results=(("s1", "   \n  "),))) == []
