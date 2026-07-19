# -*- coding: utf-8 -*-
"""T-027 (R-301): اختبارات SessionStore — إلحاق O(1)، meta sidecar،
tail-read، والتعافي من السطر الأخير الممزّق + قياس أداء 1k إلحاق.
"""
from __future__ import annotations

import json
import pathlib
import time

import pytest

from sessions.store import (
    CorruptLogError,
    ReplayResult,
    SessionStore,
    SessionMeta,
)


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> SessionStore:
    return SessionStore(tmp_path / "sessions")


# ═════════════════ دورة الحياة والإلحاق ═════════════════

class TestLifecycleAndAppend:

    def test_create_makes_empty_log_and_meta(self, store):
        meta = store.create(project_path="/proj")
        assert store.data_path(meta.id).is_file()
        assert store.data_path(meta.id).stat().st_size == 0
        on_disk = json.loads(store.meta_path(meta.id).read_text("utf-8"))
        assert on_disk["id"] == meta.id
        assert on_disk["project_path"] == "/proj"
        assert on_disk["format"] == 1
        assert on_disk["message_count"] == 0

    def test_round_trip_messages(self, store):
        meta = store.create()
        store.append_message(meta.id, "user", "مرحبا")
        store.append_message(meta.id, "assistant", "أهلًا بك")
        result = store.replay(meta.id)
        assert not result.torn_tail
        assert [r["role"] for r in result.records] == ["user", "assistant"]
        assert result.records[0]["content"] == "مرحبا"
        assert all("ts" in r for r in result.records)

    def test_append_is_pure_append_no_rewrite(self, store):
        """O(1) هيكليًا: الإلحاق لا يغيّر البايتات السابقة أبدًا."""
        meta = store.create()
        store.append_message(meta.id, "user", "أول")
        before = store.data_path(meta.id).read_bytes()
        store.append_message(meta.id, "assistant", "ثانٍ")
        after = store.data_path(meta.id).read_bytes()
        assert after.startswith(before)
        assert after.count(b"\n") == before.count(b"\n") + 1

    def test_arbitrary_record_kinds_accepted(self, store):
        # توسعة R-802: أي كائن JSON — ليس role/content فقط
        meta = store.create()
        store.append_record(meta.id, {"kind": "tool_call", "name": "read"})
        assert store.replay(meta.id).records[0]["kind"] == "tool_call"

    def test_append_to_missing_session_raises(self, store):
        with pytest.raises(FileNotFoundError):
            store.append_message("nope1234", "user", "x")

    def test_delete_removes_both_files(self, store):
        meta = store.create()
        store.append_message(meta.id, "user", "x")
        assert store.delete(meta.id) is True
        assert not store.data_path(meta.id).exists()
        assert not store.meta_path(meta.id).exists()
        assert store.delete(meta.id) is False

    def test_list_ids(self, store):
        ids = {store.create().id for _ in range(3)}
        assert set(store.list_ids()) == ids


# ═════════════════ meta sidecar ═════════════════

class TestMetaSidecar:

    def test_title_set_from_first_user_message_only(self, store):
        meta = store.create()
        store.append_message(meta.id, "assistant", "تمهيد")
        store.append_message(meta.id, "user", "أصلح الخطأ في auth.py")
        store.append_message(meta.id, "user", "رسالة أخرى")
        assert store.read_meta(meta.id).title == "أصلح الخطأ في auth.py"

    def test_long_title_truncated_with_ellipsis(self, store):
        meta = store.create()
        store.append_message(meta.id, "user", "ط" * 100)
        title = store.read_meta(meta.id).title
        assert title == "ط" * 60 + "..."

    def test_meta_not_rewritten_per_message(self, store):
        """جوهر R-301: لا rewrite لكل رسالة — الـ sidecar يُكتب عند
        تغيّر رأسي فقط (هنا: الإنشاء + أول عنوان = كتابتان)."""
        meta = store.create()
        store.append_message(meta.id, "user", "أول")   # عنوان ⇒ كتابة
        mtime_after_title = store.meta_path(meta.id).stat().st_mtime_ns
        for i in range(20):
            store.append_message(meta.id, "assistant", f"رد {i}")
        assert store.meta_path(meta.id).stat().st_mtime_ns == \
            mtime_after_title

    def test_flush_meta_persists_counters(self, store):
        meta = store.create()
        store.append_message(meta.id, "user", "س")
        store.append_message(meta.id, "assistant", "ج")
        store.flush_meta(meta.id)
        on_disk = json.loads(store.meta_path(meta.id).read_text("utf-8"))
        assert on_disk["message_count"] == 2

    def test_set_project_path_written_immediately(self, store):
        meta = store.create()
        store.set_project_path(meta.id, "/new/path")
        on_disk = json.loads(store.meta_path(meta.id).read_text("utf-8"))
        assert on_disk["project_path"] == "/new/path"

    def test_rebuild_meta_from_log(self, store):
        """السجل مصدر الحقيقة — الرأس قابل لإعادة البناء بالكامل."""
        meta = store.create(project_path="/kept")
        store.append_message(meta.id, "user", "العنوان الحقيقي")
        store.append_message(meta.id, "assistant", "رد")
        store.meta_path(meta.id).unlink()          # sidecar ضائع
        fresh = SessionStore(store.sessions_dir)    # كاش بارد
        rebuilt = fresh.read_meta(meta.id)          # يعيد البناء تلقائيًا
        assert rebuilt.message_count == 2
        assert rebuilt.title == "العنوان الحقيقي"
        assert store.meta_path(meta.id).is_file()   # كُتب من جديد

    def test_corrupt_sidecar_rebuilt_from_log(self, store):
        meta = store.create()
        store.append_message(meta.id, "user", "س")
        store.meta_path(meta.id).write_text("{ليس json", encoding="utf-8")
        fresh = SessionStore(store.sessions_dir)
        assert fresh.read_meta(meta.id).message_count == 1


# ═════════════════ tail-read ═════════════════

class TestTailRead:

    def test_tail_returns_last_n_in_order(self, store):
        meta = store.create()
        for i in range(50):
            store.append_message(meta.id, "user", f"رسالة {i}")
        result = store.tail(meta.id, 5)
        assert [r["content"] for r in result.records] == [
            f"رسالة {i}" for i in range(45, 50)]

    def test_tail_larger_than_log_returns_all(self, store):
        meta = store.create()
        store.append_message(meta.id, "user", "وحيدة")
        result = store.tail(meta.id, 100)
        assert len(result.records) == 1

    def test_tail_zero_or_empty(self, store):
        meta = store.create()
        assert store.tail(meta.id, 0).records == []
        assert store.tail(meta.id, 3).records == []

    def test_tail_does_not_read_whole_file(self, store, monkeypatch):
        """نافذة R-304: سجل أكبر بكثير من كتلة القراءة — tail يقرأ
        أقل بكثير من حجم الملف."""
        meta = store.create()
        big = "م" * 1000
        for i in range(300):
            store.append_message(meta.id, "user", f"{i}:{big}")
        file_size = store.data_path(meta.id).stat().st_size

        import sessions.store as mod
        reads: list[int] = []
        orig_read = pathlib.Path.read_bytes   # غير مستخدم في tail أصلًا

        class CountingFile:
            pass

        # نلفّ open الحقيقي ونحصي ما يُقرأ فعليًا
        real_open = open

        def counting_open(*args, **kwargs):
            f = real_open(*args, **kwargs)
            real_read = f.read

            def read(n=-1):
                data = real_read(n)
                reads.append(len(data))
                return data
            f.read = read
            return f

        monkeypatch.setattr("builtins.open", counting_open)
        result = store.tail(meta.id, 3)
        assert len(result.records) == 3
        assert sum(reads) < file_size / 2   # قرأنا نافذة، لا الملف

    def test_tail_skips_torn_line(self, store):
        meta = store.create()
        store.append_message(meta.id, "user", "سليمة")
        with open(store.data_path(meta.id), "a", encoding="utf-8") as f:
            f.write('{"role": "user", "content": "ممز')   # صدمة
        result = store.tail(meta.id, 10)
        assert result.torn_tail is True
        assert [r["content"] for r in result.records] == ["سليمة"]


# ═════════════════ التعافي من التمزّق ═════════════════

class TestTornWriteRecovery:

    def _tear(self, store, session_id, partial='{"role": "user", "con'):
        with open(store.data_path(session_id), "a", encoding="utf-8") as f:
            f.write(partial)

    def test_replay_skips_torn_tail_and_reports(self, store):
        meta = store.create()
        store.append_message(meta.id, "user", "أ")
        store.append_message(meta.id, "assistant", "ب")
        self._tear(store, meta.id)
        result = store.replay(meta.id)
        assert result.torn_tail is True
        assert [r["content"] for r in result.records] == ["أ", "ب"]

    def test_append_after_tear_truncates_then_appends(self, store):
        """أخطر سيناريو: إلحاق فوق ذيل ممزّق يجب ألا يُنتج سطرًا ملتحمًا."""
        meta = store.create()
        store.append_message(meta.id, "user", "قبل الصدمة")
        self._tear(store, meta.id)
        fresh = SessionStore(store.sessions_dir)   # عملية جديدة بعد الصدمة
        fresh.append_message(meta.id, "assistant", "بعد التعافي")
        result = fresh.replay(meta.id)
        assert result.torn_tail is False
        assert [r["content"] for r in result.records] == \
            ["قبل الصدمة", "بعد التعافي"]

    def test_tear_on_first_line_truncates_to_empty(self, store):
        meta = store.create()
        self._tear(store, meta.id)   # السطر الوحيد ممزّق — لا \n إطلاقًا
        fresh = SessionStore(store.sessions_dir)
        fresh.append_message(meta.id, "user", "أول سليمة")
        result = fresh.replay(meta.id)
        assert [r["content"] for r in result.records] == ["أول سليمة"]

    def test_mid_log_corruption_raises_loudly(self, store):
        """تلف في الوسط ليس نمط صدمة — يفشل بصوت عالٍ، لا إخفاء."""
        meta = store.create()
        store.append_message(meta.id, "user", "أ")
        store.append_message(meta.id, "user", "ب")
        path = store.data_path(meta.id)
        lines = path.read_bytes().split(b"\n")
        lines[0] = b"{corrupt!!"
        path.write_bytes(b"\n".join(lines))
        with pytest.raises(CorruptLogError):
            store.replay(meta.id)

    def test_meta_lag_after_crash_healed_by_rebuild(self, store):
        """بند مخاطر R-301: العدّادات تتأخر بعد صدمة — rebuild يصلحها."""
        meta = store.create()
        store.append_message(meta.id, "user", "س")   # عنوان ⇒ sidecar كُتب
        # رسالتان لم يُكتب عدّادهما (لا flush قبل "الصدمة")
        store.append_message(meta.id, "assistant", "ج1")
        store.append_message(meta.id, "assistant", "ج2")
        fresh = SessionStore(store.sessions_dir)
        assert fresh.read_meta(meta.id).message_count == 1   # متأخر
        assert fresh.rebuild_meta(meta.id).message_count == 3  # الحقيقة


# ═════════════════ قياس الأداء (معيار القبول) ═════════════════

class TestBenchmark:

    def test_1k_appends_p95_under_5ms(self, tmp_path):
        """معيار قبول R-301/T-027: 1k إلحاق p95 < 5ms.

        نقيس بسياسة ``fsync="never"`` — زمن fsync ملك القرص لا الخوارزمية،
        والمطلوب إثباته هو أن *تكلفة الإلحاق ثابتة* لا تنمو مع التاريخ
        (عكس rewrite-per-message القديم الذي يتخطى 5ms حتميًا مع النمو).
        """
        store = SessionStore(tmp_path / "bench", fsync="never")
        meta = store.create()
        durations: list[float] = []
        payload = "رسالة قياس بطول معقول يشبه رسائل المحادثة الفعلية " * 3
        for i in range(1000):
            t0 = time.perf_counter()
            store.append_message(meta.id, "user", f"{i}: {payload}")
            durations.append(time.perf_counter() - t0)
        durations.sort()
        p95 = durations[int(len(durations) * 0.95) - 1]
        assert p95 < 0.005, f"p95={p95 * 1000:.3f}ms >= 5ms"
        # وتأكيد صحة الناتج: 1000 سطر سليم
        assert len(store.replay(meta.id).records) == 1000

    def test_append_cost_does_not_grow_with_history(self, tmp_path):
        """جوهر قتل O(n²): متوسط آخر 100 إلحاق ≤ 3× متوسط أول 100
        رغم أن التاريخ صار 10× أطول (القديم كان يعطي ~10×)."""
        store = SessionStore(tmp_path / "growth", fsync="never")
        meta = store.create()
        durations: list[float] = []
        payload = "ن" * 500
        for i in range(1000):
            t0 = time.perf_counter()
            store.append_message(meta.id, "user", payload)
            durations.append(time.perf_counter() - t0)
        first = sum(durations[:100]) / 100
        last = sum(durations[-100:]) / 100
        assert last <= first * 3, (
            f"الإلحاق ينمو مع التاريخ: أول 100={first * 1e6:.1f}µs "
            f"آخر 100={last * 1e6:.1f}µs")
