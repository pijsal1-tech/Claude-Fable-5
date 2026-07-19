# -*- coding: utf-8 -*-
"""T-028 (R-301/R-305): اختبارات ترحيل الجلسات JSON→JSONL.

معايير القبول: round-trip بلا فقدان؛ إعادة التشغيل no-op (idempotent)؛
الجلسات القديمة قابلة للتحميل بعد الترحيل عبر SessionStore.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from scripts.migrate_sessions import migrate_dir
from sessions.store import SessionStore

LEGACY_MESSAGES = [
    {"role": "user", "content": "أصلح الخطأ في auth.py",
     "timestamp": "2026-07-14T04:27:01.243854"},
    {"role": "assistant", "content": "تم — راجع السطر 17",
     "timestamp": "2026-07-14T04:27:05.100000"},
    {"role": "user", "content": "ممتاز، كمل ✅",
     "timestamp": "2026-07-14T04:28:00.000001"},
]


def _write_legacy(dir_path: pathlib.Path, session_id: str,
                  messages=None, **overrides) -> pathlib.Path:
    doc = {
        "id": session_id,
        "project_path": "D:\\projects\\my_ai_editor",
        "created_at": "2026-07-14T04:27:01.243854",
        "updated_at": "2026-07-14T04:28:00.000001",
        "messages": LEGACY_MESSAGES if messages is None else messages,
        "title": "أصلح الخطأ في auth.py",
    }
    doc.update(overrides)
    path = dir_path / f"{session_id}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return path


@pytest.fixture()
def sess_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    d = tmp_path / "sessions"
    d.mkdir()
    return d


# ═════════════════ round-trip بلا فقدان ═════════════════

class TestFidelity:

    def test_messages_round_trip_value_exact(self, sess_dir):
        _write_legacy(sess_dir, "abc12345")
        report = migrate_dir(sess_dir)
        assert report.migrated == ["abc12345"]
        replayed = SessionStore(sess_dir).replay("abc12345")
        assert not replayed.torn_tail
        assert len(replayed.records) == len(LEGACY_MESSAGES)
        for rec, msg in zip(replayed.records, LEGACY_MESSAGES):
            assert rec["role"] == msg["role"]
            assert rec["content"] == msg["content"]
            assert rec["ts"] == msg["timestamp"]   # حرفيًا — لا فقدان

    def test_meta_header_carried_verbatim(self, sess_dir):
        _write_legacy(sess_dir, "abc12345")
        migrate_dir(sess_dir)
        meta = SessionStore(sess_dir).read_meta("abc12345")
        assert meta.id == "abc12345"
        assert meta.title == "أصلح الخطأ في auth.py"
        assert meta.project_path == "D:\\projects\\my_ai_editor"
        assert meta.created_at == "2026-07-14T04:27:01.243854"
        assert meta.updated_at == "2026-07-14T04:28:00.000001"
        assert meta.message_count == 3

    def test_empty_session_migrates_to_empty_log(self, sess_dir):
        # 14 من الجلسات الحقيقية الـ 43 فارغة — يجب ألا تضيع رؤوسها
        _write_legacy(sess_dir, "empty001", messages=[])
        report = migrate_dir(sess_dir)
        assert report.migrated == ["empty001"]
        store = SessionStore(sess_dir)
        assert store.replay("empty001").records == []
        assert store.read_meta("empty001").message_count == 0

    def test_post_migration_store_fully_usable(self, sess_dir):
        """regression: الجلسة المُرحَّلة قابلة للاستخدام الكامل —
        إلحاق جديد فوق التاريخ القديم بلا التحام ولا فقدان."""
        _write_legacy(sess_dir, "abc12345")
        migrate_dir(sess_dir)
        store = SessionStore(sess_dir)
        store.append_message("abc12345", "assistant", "رد ما بعد الترحيل")
        records = store.replay("abc12345").records
        assert len(records) == 4
        assert records[-1]["content"] == "رد ما بعد الترحيل"
        assert store.tail("abc12345", 2).records[0]["content"] == "ممتاز، كمل ✅"

    def test_migrates_many_sessions_in_one_run(self, sess_dir):
        for i in range(5):
            _write_legacy(sess_dir, f"many000{i}")
        report = migrate_dir(sess_dir)
        assert len(report.migrated) == 5
        assert sorted(SessionStore(sess_dir).list_ids()) == \
            [f"many000{i}" for i in range(5)]


# ═════════════════ idempotency ═════════════════

class TestIdempotency:

    def test_second_run_is_noop(self, sess_dir):
        _write_legacy(sess_dir, "abc12345")
        migrate_dir(sess_dir)
        store = SessionStore(sess_dir)
        data_mtime = store.data_path("abc12345").stat().st_mtime_ns
        meta_mtime = store.meta_path("abc12345").stat().st_mtime_ns

        report2 = migrate_dir(sess_dir)
        assert report2.is_noop
        assert report2.skipped_existing == ["abc12345"]
        assert store.data_path("abc12345").stat().st_mtime_ns == data_mtime
        assert store.meta_path("abc12345").stat().st_mtime_ns == meta_mtime

    def test_rerun_does_not_duplicate_messages(self, sess_dir):
        _write_legacy(sess_dir, "abc12345")
        migrate_dir(sess_dir)
        migrate_dir(sess_dir)
        migrate_dir(sess_dir)
        assert len(SessionStore(sess_dir).replay("abc12345").records) == 3

    def test_new_appends_survive_rerun(self, sess_dir):
        """أخطر سيناريو idempotency: رسائل أُلحقت بعد الترحيل يجب ألا
        تُمحى بإعادة تشغيل السكربت فوق الملف القديم الباقي."""
        _write_legacy(sess_dir, "abc12345")
        migrate_dir(sess_dir)
        store = SessionStore(sess_dir)
        store.append_message("abc12345", "user", "جديدة بعد الترحيل")
        migrate_dir(sess_dir)   # الملف القديم ما زال موجودًا
        records = SessionStore(sess_dir).replay("abc12345").records
        assert len(records) == 4
        assert records[-1]["content"] == "جديدة بعد الترحيل"


# ═════════════════ الأعطاب والحذف الاختياري ═════════════════

class TestRobustness:

    def test_corrupt_legacy_skipped_reported_others_migrate(self, sess_dir):
        (sess_dir / "broken01.json").write_text("{ليس json",
                                                encoding="utf-8")
        _write_legacy(sess_dir, "good0001")
        report = migrate_dir(sess_dir)
        assert report.migrated == ["good0001"]
        assert [name for name, _ in report.skipped_bad] == ["broken01.json"]

    def test_meta_sidecars_not_treated_as_legacy(self, sess_dir):
        _write_legacy(sess_dir, "abc12345")
        migrate_dir(sess_dir)
        report2 = migrate_dir(sess_dir)   # يوجد الآن session_*.meta.json
        assert report2.skipped_bad == []  # الـ sidecar ليس ملفًا قديمًا

    def test_legacy_kept_by_default(self, sess_dir):
        legacy = _write_legacy(sess_dir, "abc12345")
        migrate_dir(sess_dir)
        assert legacy.exists()   # لا حذف بلا طلب صريح

    def test_remove_legacy_flag_deletes_after_verify(self, sess_dir):
        legacy = _write_legacy(sess_dir, "abc12345")
        report = migrate_dir(sess_dir, remove_legacy=True)
        assert not legacy.exists()
        assert report.removed_legacy == ["abc12345"]
        # البيانات سليمة بعد الحذف
        assert len(SessionStore(sess_dir).replay("abc12345").records) == 3

    def test_remove_legacy_keeps_corrupt_file(self, sess_dir):
        bad = sess_dir / "broken01.json"
        bad.write_text("{ليس json", encoding="utf-8")
        migrate_dir(sess_dir, remove_legacy=True)
        assert bad.exists()   # التالف لا يُحذف أبدًا — دليل جنائي


# ═════════════════ الجلسات الحقيقية في المستودع ═════════════════

class TestRealRepoSessions:

    def test_real_43_sessions_migrate_lossless(self, tmp_path):
        """الاختبار على نسخة من بيانات المستودع الفعلية — بلا لمسها."""
        repo_sessions = pathlib.Path(__file__).resolve().parents[2] / "sessions"
        legacy_files = [p for p in repo_sessions.glob("*.json")
                        if not p.name.endswith(".meta.json")]
        if not legacy_files:
            pytest.skip("لا جلسات legacy في المستودع (رُحّلت وحُذفت)")
        work = tmp_path / "sessions"
        work.mkdir()
        for f in legacy_files:
            (work / f.name).write_bytes(f.read_bytes())

        report = migrate_dir(work)
        assert report.skipped_bad == []
        assert len(report.migrated) == len(legacy_files)

        store = SessionStore(work)
        for f in legacy_files:
            doc = json.loads(f.read_text(encoding="utf-8"))
            replayed = store.replay(doc["id"])
            assert len(replayed.records) == len(doc["messages"])
            for rec, msg in zip(replayed.records, doc["messages"]):
                assert rec["role"] == msg["role"]
                assert rec["content"] == msg["content"]
                assert rec["ts"] == msg["timestamp"]
