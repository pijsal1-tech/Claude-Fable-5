# -*- coding: utf-8 -*-
"""TSK-707 (FI-01/1): اختبارات ConversationState — المخزن القانوني الموحد.

تغطي: سلوك العمليات المسماة، عزل النسخ (snapshot/replace_all لا تسرب
مراجع)، البانر، والسلامة تحت خيوط متزامنة (عقد REST-thread/WS-thread).
"""
import threading

from core.conversation_state import ConversationState
from providers.base import Message


def _msg(role: str, content: str) -> Message:
    return Message(role=role, content=content)


class TestHistoryOperations:
    def test_starts_empty(self):
        cs = ConversationState()
        assert cs.snapshot() == []
        assert len(cs) == 0

    def test_append_and_snapshot(self):
        cs = ConversationState()
        m1 = _msg("user", "أهلًا")
        m2 = _msg("assistant", "مرحبًا")
        cs.append(m1)
        cs.append(m2)
        snap = cs.snapshot()
        assert snap == [m1, m2]
        assert len(cs) == 2

    def test_replace_all_swaps_history(self):
        cs = ConversationState()
        cs.append(_msg("user", "قديم"))
        new = [_msg("user", "س"), _msg("assistant", "ج")]
        cs.replace_all(new)
        assert cs.snapshot() == new
        assert len(cs) == 2

    def test_clear_empties_history(self):
        cs = ConversationState()
        cs.append(_msg("user", "x"))
        cs.clear()
        assert cs.snapshot() == []
        assert len(cs) == 0


class TestCopyIsolation:
    """عقد العزل: لا تسريب مرجع داخلي في أي اتجاه (T-048 يعتمد عليه)."""

    def test_snapshot_mutation_does_not_affect_store(self):
        cs = ConversationState()
        cs.append(_msg("user", "ثابت"))
        snap = cs.snapshot()
        snap.append(_msg("user", "دخيل"))
        snap.clear()
        assert len(cs) == 1
        assert cs.snapshot()[0].content == "ثابت"

    def test_replace_all_copies_input_list(self):
        cs = ConversationState()
        src = [_msg("user", "أ")]
        cs.replace_all(src)
        src.append(_msg("user", "دخيل"))
        assert len(cs) == 1

    def test_snapshots_are_independent(self):
        cs = ConversationState()
        cs.append(_msg("user", "1"))
        s1 = cs.snapshot()
        s2 = cs.snapshot()
        assert s1 == s2
        assert s1 is not s2


class TestBindingBanner:
    def test_default_empty(self):
        assert ConversationState().binding_banner == ""

    def test_set_and_read(self):
        cs = ConversationState()
        cs.set_banner("⚠️ تنبيه ربط")
        assert cs.binding_banner == "⚠️ تنبيه ربط"

    def test_clear_banner(self):
        cs = ConversationState()
        cs.set_banner("نص")
        cs.clear_banner()
        assert cs.binding_banner == ""

    def test_banner_independent_of_history(self):
        cs = ConversationState()
        cs.set_banner("بانر")
        cs.clear()  # مسح التاريخ لا يمس البانر (الدلالة في المواقع المستدعية)
        assert cs.binding_banner == "بانر"
        assert len(cs) == 0


class TestThreadSafety:
    """عقد القفل: كتابات متزامنة من خيطين (REST + WS) لا تفقد رسائل."""

    def test_concurrent_appends_lose_nothing(self):
        cs = ConversationState()
        n_threads, per_thread = 4, 50

        def writer(tid: int) -> None:
            for i in range(per_thread):
                cs.append(_msg("user", f"{tid}:{i}"))

        threads = [threading.Thread(target=writer, args=(t,))
                   for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(cs) == n_threads * per_thread

    def test_concurrent_snapshot_during_writes_is_safe(self):
        cs = ConversationState()
        stop = threading.Event()
        errors: list[BaseException] = []

        def writer() -> None:
            i = 0
            while not stop.is_set():
                cs.append(_msg("user", str(i)))
                i += 1

        def reader() -> None:
            try:
                for _ in range(200):
                    snap = cs.snapshot()
                    # النسخة متسقة: قابلة للمسح دون أثر على المخزن
                    snap.clear()
            except BaseException as exc:  # pragma: no cover
                errors.append(exc)

        w = threading.Thread(target=writer)
        r = threading.Thread(target=reader)
        w.start(); r.start()
        r.join(); stop.set(); w.join()
        assert errors == []
        assert len(cs) > 0
