# -*- coding: utf-8 -*-
"""AppContext + ProjectHandle (T-005, R-102): the composition root.

Wiring diagram (target state after T-006..T-008)::

    main()
      └─ AppContext (single instance, owns the object graph)
           ├─ project: ProjectHandle          ← swapped atomically on switch
           │    ├─ root: str                  (absolute project path)
           │    ├─ fm: FileManager
           │    ├─ cmd_runner: CommandRunner
           │    ├─ safe_reader: (slot, R-204)
           │    └─ index: (slot, R-702)
           ├─ provider_pool / active_provider
           ├─ session_manager
           ├─ config: dict
           └─ registry: (slot, R-105 ExecutionRegistry)

    Consumers (ChainBridge, AgentTools, DelegateBridge, ...) receive
    ``ctx: AppContext`` and resolve ``ctx.project.fm`` **at call time** —
    never caching the handle or its members. That is what kills the
    stale-reference class of bugs: after ``switch_project()`` the old
    handle is invalidated and any accidental cached use raises loudly.

Rules:
- ``switch_project(path)`` builds the new handle **first**, then swaps the
  reference under a lock (atomic publication), then invalidates the old
  handle so stale holders fail fast instead of writing to the wrong tree.
- Nothing here imports Flask or touches module globals.
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from typing import Any, Callable


class StaleHandleError(RuntimeError):
    """Raised when code uses a ProjectHandle that was swapped out."""


@dataclass
class ProjectHandle:
    """Everything scoped to one open project. Swapped as a unit."""
    root: str
    fm: Any = None                 # FileManager
    cmd_runner: Any = None         # CommandRunner
    safe_reader: Any = None        # slot — filled by R-204 (T-025/T-026)
    index: Any = None              # slot — filled by R-702
    _valid: bool = field(default=True, repr=False)

    @property
    def project_id(self) -> str:
        """TSK-302 (NF-02): هوية المشروع لخانة الـ run في
        ExecutionRegistry — المسار المطلق المُطبّع للجذر (هوية
        مستقرة: نفس المجلد = نفس الخانة مهما اختلف شكل كتابة المسار)."""
        return os.path.normpath(os.path.abspath(self.root))

    def invalidate(self) -> None:
        self._valid = False

    @property
    def is_valid(self) -> bool:
        return self._valid

    def ensure_valid(self) -> "ProjectHandle":
        """Fail fast if this handle was superseded by a project switch."""
        if not self._valid:
            raise StaleHandleError(
                f"ProjectHandle for {self.root!r} was invalidated by a "
                "project switch; resolve ctx.project at call time instead "
                "of caching the handle."
            )
        return self


# Factory signature: (root_path) -> ProjectHandle
HandleFactory = Callable[[str], ProjectHandle]


def default_handle_factory(root: str) -> ProjectHandle:
    """Build a ProjectHandle with real FileManager/CommandRunner.

    Imported lazily so unit tests can use AppContext without the heavy
    modules, and so this module never becomes an import cycle hub.
    """
    from actions.file_manager import FileManager
    from actions.command_runner import CommandRunner
    return ProjectHandle(
        root=root,
        fm=FileManager(root),
        cmd_runner=CommandRunner(cwd=root),
    )


@dataclass
class AppContext:
    """Composition root. One instance per process (built in main())."""
    project: ProjectHandle
    provider_pool: Any = None
    session_manager: Any = None
    budget: Any = None
    registry: Any = None           # slot — R-105 ExecutionRegistry
    config: dict = field(default_factory=dict)
    handle_factory: HandleFactory = default_handle_factory
    _provider: Any = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # ── provider ─────────────────────────────────────────
    @property
    def active_provider(self) -> Any:
        with self._lock:
            return self._provider

    def switch_model(self, provider: Any) -> Any:
        """Atomically publish a new active provider. Returns the old one.

        Consumers must read ``ctx.active_provider`` at call time — this
        replaces the private-attribute pokes flagged by R-102 (T-008 will
        migrate the three offenders).
        """
        with self._lock:
            old, self._provider = self._provider, provider
            return old

    # ── project ──────────────────────────────────────────
    def switch_project(self, path: str) -> ProjectHandle:
        """Build a new ProjectHandle for ``path`` and swap it in atomically.

        Order matters: construct fully **outside** the lock (slow I/O),
        publish under the lock, then invalidate the old handle so any
        stale cached reference raises ``StaleHandleError``.
        """
        abs_path = os.path.abspath(path)
        if not os.path.isdir(abs_path):
            raise NotADirectoryError(abs_path)

        new_handle = self.handle_factory(abs_path)
        with self._lock:
            old_handle, self.project = self.project, new_handle
        if old_handle is not None:
            old_handle.invalidate()
        return new_handle
