# -*- coding: utf-8 -*-
"""
QA-T10 (جزء TSK-301) — وحدة سباق pending_path_requests (NF-01).
Validates: TSK-301 (تنظيف pending_path_requests داخل القفل).

معيار القبول الحرفي: اختبار خيطين (store متكرر + pop متكرر) 10k دورة
بلا استثناء. قبل الإصلاح كان _clean_expired_pending_requests يطوف
القاموس خارج القفل → RuntimeError «dictionary changed size during
iteration» تحت الضغط. صفر نداءات AI خارجية.
"""
import threading

import pytest

import server


@pytest.fixture(autouse=True)
def _clean_state():
    """عزل الحالة العالمية قبل/بعد كل اختبار."""
    server.pending_path_requests.clear()
    yield
    server.pending_path_requests.clear()


CYCLES = 10_000


class TestStorePopRace:
    """معيار القبول: خيطا store/pop، 10k دورة، بلا استثناء."""

    def test_concurrent_store_and_pop_10k_cycles(self, monkeypatch):
        # TTL=0 ⇒ كل عنصر منتهي الصلاحية فورًا — التنظيف يطوف ويحذف
        # في كل store: أقصى احتكاك ممكن بين الطوفان والطفرة.
        monkeypatch.setattr(server, "_PENDING_PATH_TTL", 0)
        errors: list[BaseException] = []
        start = threading.Barrier(2)

        def storer():
            start.wait()
            try:
                for i in range(CYCLES):
                    server.store_pending_path_request(
                        f"req-{i % 50}", {"path": f"/p/{i}", "timestamp": 0})
            except BaseException as exc:  # noqa: BLE001 — نلتقط أي شيء
                errors.append(exc)

        def popper():
            start.wait()
            try:
                for i in range(CYCLES):
                    server.pop_pending_path_request(f"req-{i % 50}")
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        t1 = threading.Thread(target=storer)
        t2 = threading.Thread(target=popper)
        t1.start(); t2.start()
        t1.join(timeout=60); t2.join(timeout=60)
        assert not t1.is_alive() and not t2.is_alive(), "deadlock/تعليق"
        assert errors == [], f"استثناءات سباق: {errors!r}"

    def test_concurrent_two_storers(self, monkeypatch):
        """خيطا store متوازيان — التنظيف داخل القفل لا يتصادم مع الإضافة."""
        monkeypatch.setattr(server, "_PENDING_PATH_TTL", 0)
        errors: list[BaseException] = []
        start = threading.Barrier(2)

        def storer(tag):
            start.wait()
            try:
                for i in range(CYCLES // 2):
                    server.store_pending_path_request(
                        f"{tag}-{i % 25}", {"path": "/x", "timestamp": 0})
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=storer, args=(t,))
                   for t in ("a", "b")]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)
        assert all(not t.is_alive() for t in threads)
        assert errors == []


class TestFunctionalBehavior:
    """السلوك الوظيفي محفوظ بعد نقل التنظيف داخل القفل."""

    def test_store_then_pop_roundtrip(self):
        server.store_pending_path_request(
            "r1", {"path": "/proj", "timestamp": 9e12})
        got = server.pop_pending_path_request("r1")
        assert got == {"path": "/proj", "timestamp": 9e12}
        assert server.pop_pending_path_request("r1") is None

    def test_expired_entries_cleaned_on_store(self, monkeypatch):
        """TTL منقضٍ → العنصر القديم يُنظَّف عند أول store تالٍ."""
        server.pending_path_requests["old"] = {"path": "/o", "timestamp": 0}
        monkeypatch.setattr(server, "_PENDING_PATH_TTL", 0)
        server.store_pending_path_request(
            "new", {"path": "/n", "timestamp": 9e12})
        assert "old" not in server.pending_path_requests
        assert "new" in server.pending_path_requests

    def test_fresh_entries_survive_clean(self):
        """عنصر حديث (ضمن TTL) لا يُحذف بالتنظيف."""
        import time
        server.store_pending_path_request(
            "fresh", {"path": "/f", "timestamp": time.time()})
        server.store_pending_path_request(
            "fresh2", {"path": "/f2", "timestamp": time.time()})
        assert "fresh" in server.pending_path_requests


class TestLockDiscipline:
    """grep-asserts: الانضباط البنيوي — التنظيف لا يجري خارج القفل."""

    def test_store_cleans_inside_lock(self):
        """في store: التنظيف بعد with lock (بنيويًا)."""
        import inspect
        src = inspect.getsource(server.store_pending_path_request)
        lock_idx = src.index("with _pending_path_lock:")
        clean_idx = src.index("_clean_expired_pending_requests()")
        assert clean_idx > lock_idx, "التنظيف خارج القفل — انحدار NF-01"

    def test_clean_helper_does_not_acquire_lock(self):
        """الدالة المساعدة لا تمسك القفل بنفسها (Lock غير reentrant —
        امتلاكه داخلها مع المستدعي = deadlock)."""
        import inspect
        src = inspect.getsource(server._clean_expired_pending_requests)
        assert "with _pending_path_lock" not in src
