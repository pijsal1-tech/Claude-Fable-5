# -*- coding: utf-8 -*-
"""T-003: ActiveRunHolder unit tests (acquire/release/double-acquire/foreign-release)."""
import threading

import pytest

from core.active_run import ActiveRunHolder


def test_acquire_and_release():
    h = ActiveRunHolder()
    assert h.current() is None
    assert h.acquire("run-1") is True
    assert h.current() == "run-1"
    assert h.is_active() is True
    assert h.release("run-1") is True
    assert h.current() is None
    assert h.is_active() is False


def test_double_acquire_rejected():
    h = ActiveRunHolder()
    assert h.acquire("run-1") is True
    assert h.acquire("run-2") is False       # different run blocked
    assert h.acquire("run-1") is False       # same id cannot re-acquire
    assert h.current() == "run-1"


def test_foreign_release_is_noop():
    h = ActiveRunHolder()
    assert h.acquire("run-1") is True
    assert h.release("run-2") is False       # foreign release rejected
    assert h.current() == "run-1"            # state untouched
    assert h.release(None) is False          # nonsense release rejected
    assert h.release("run-1") is True


def test_release_when_idle_is_noop():
    h = ActiveRunHolder()
    assert h.release("run-1") is False
    assert h.current() is None


def test_empty_run_id_rejected():
    h = ActiveRunHolder()
    with pytest.raises(ValueError):
        h.acquire("")


def test_thread_safety_only_one_winner():
    """20 threads race to acquire; exactly one must win."""
    h = ActiveRunHolder()
    results = []
    barrier = threading.Barrier(20)

    def worker(i):
        barrier.wait()
        results.append(h.acquire(f"run-{i}"))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count(True) == 1
    assert h.current() is not None
