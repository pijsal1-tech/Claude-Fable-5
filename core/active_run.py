# -*- coding: utf-8 -*-
"""ActiveRunHolder (T-003, R-101): single-active-run concurrency guard.

Safe replacement for the dead ``_active_chain_run`` module-level guard in
``server.py`` (assigned at L403/L470 but the check at L82 read a stale
closure — it never actually blocked concurrent runs).

Semantics:
- ``acquire(run_id)`` — returns True and records ``run_id`` as the active
  run iff no run is active; returns False otherwise (including when the
  same ``run_id`` tries to acquire twice).
- ``release(run_id)`` — releases only if ``run_id`` matches the active run
  (a "foreign" release is a no-op returning False, never corrupts state).
- ``current()`` — the active ``run_id`` or ``None``.

All operations are protected by one ``threading.Lock``.

.. note::
   Supersession (R-105): once ``ExecutionRegistry`` + ``RunTicket`` land,
   they replace this holder as the general execution-tracking mechanism
   (see T-015 "Tickets in All Three Modes; Delete Holder"). This class is
   deliberately minimal because it is scheduled for deletion.
"""
from __future__ import annotations

import threading


class ActiveRunHolder:
    """Thread-safe holder of the single currently-active run id."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: str | None = None

    def acquire(self, run_id: str) -> bool:
        """Try to become the active run. False if any run (even the same
        id) is already active."""
        if not run_id:
            raise ValueError("run_id must be a non-empty string")
        with self._lock:
            if self._active is not None:
                return False
            self._active = run_id
            return True

    def release(self, run_id: str) -> bool:
        """Release the active slot iff ``run_id`` owns it.

        Returns True if released; False for a foreign/stale release
        (state is left untouched).
        """
        with self._lock:
            if self._active != run_id:
                return False
            self._active = None
            return True

    def current(self) -> str | None:
        """The active run id, or None when idle."""
        with self._lock:
            return self._active

    def is_active(self) -> bool:
        return self.current() is not None
