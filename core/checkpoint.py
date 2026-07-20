# -*- coding: utf-8 -*-
"""CheckpointManager (T-053, R-106): content-addressed pre-write snapshots.

Why this exists
---------------
Post-write reversibility is the highest product-trust item: once an
agent/chain apply mutates project files, the user needs a guaranteed way
back.  This module provides the standalone manager — WS wiring and the
apply-path hookup land in T-054.

Store layout
------------
::

    <root>/
        objects/
            <sha256-hex>            # content-addressed blobs (dedup: one
                                    # blob per unique content, ever)
        checkpoints.jsonl           # CheckpointLog — JSONL records keyed
                                    # by run_id

``checkpoints.jsonl`` record types::

    {"type": "snapshot", "run_id": str, "path": str,
     "sha256": str | null,    # pre-write content hash; null => the file
                              # did NOT exist (restore deletes it)
     "size": int, "ts": float}

    {"type": "seal", "run_id": str, "path": str,
     "sha256": str | null,    # post-write content hash; null => the run
                              # deleted the file
     "ts": float}

Lifecycle (T-054 wires this around every gate-approved apply)::

    mgr.snapshot(run_id, paths)   # BEFORE writing — captures pre state
    ... apply writes files ...
    mgr.seal(run_id, paths)       # AFTER writing — captures post state

Restore semantics — the external-modification guard
----------------------------------------------------
``restore_run`` / ``restore_file`` verify the **current** on-disk hash of
every target first:

* current == pre-write hash   -> already at snapshot state; no-op success.
* current == sealed post-write hash -> the run's own output is still on
  disk untouched; safe to roll back to the snapshot blob.
* anything else (or no seal record at all) -> the file **changed
  externally** (human edit, another tool, ...); restore **refuses with a
  conflict report** for that file and never overwrites unverifiable work.

``restore_run`` still restores clean siblings when some files are refused;
the report's ``status`` is then ``"partial"``.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> Optional[str]:
    """Hash a file's content; ``None`` when it does not exist."""
    try:
        with open(path, "rb") as fh:
            h = hashlib.sha256()
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
            return h.hexdigest()
    except FileNotFoundError:
        return None


@dataclass(frozen=True)
class SnapshotEntry:
    """One snapshotted file inside a run's checkpoint."""

    run_id: str
    path: str
    sha256: Optional[str]  # None => file was absent at snapshot time
    size: int
    ts: float

    def to_record(self) -> dict:
        return {
            "type": "snapshot",
            "run_id": self.run_id,
            "path": self.path,
            "sha256": self.sha256,
            "size": self.size,
            "ts": self.ts,
        }

    @staticmethod
    def from_record(rec: dict) -> "SnapshotEntry":
        return SnapshotEntry(
            run_id=str(rec["run_id"]),
            path=str(rec["path"]),
            sha256=rec.get("sha256"),
            size=int(rec.get("size", 0)),
            ts=float(rec.get("ts", 0.0)),
        )


@dataclass(frozen=True)
class Conflict:
    """A file that refused restore because its state is unverifiable."""

    path: str
    expected_sha256: Optional[str]  # sealed post-write hash (or None)
    actual_sha256: Optional[str]  # what is on disk now
    reason: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "expected_sha256": self.expected_sha256,
            "actual_sha256": self.actual_sha256,
            "reason": self.reason,
        }


@dataclass
class RestoreReport:
    """Outcome of a restore call.

    ``status`` is one of ``"success"`` (everything restored),
    ``"partial"`` (some files restored, some refused) or ``"refused"``
    (nothing restored).
    """

    run_id: str
    restored: list[str] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.conflicts and self.restored:
            return "partial"
        if self.conflicts:
            return "refused"
        return "success"

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "restored": list(self.restored),
            "conflicts": [c.to_dict() for c in self.conflicts],
        }


class CheckpointManager:
    """Content-addressed pre-write snapshots with hash-verified restore.

    Parameters
    ----------
    root:
        Directory for the object store + log.  Created on demand.
    """

    LOG_NAME = "checkpoints.jsonl"
    OBJECTS_DIR = "objects"

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._objects = self._root / self.OBJECTS_DIR
        self._log_path = self._root / self.LOG_NAME

    # ------------------------------------------------------------------
    # snapshot / seal
    # ------------------------------------------------------------------
    def snapshot(self, run_id: str, paths: list[str | Path]) -> list[SnapshotEntry]:
        """Record the pre-write state of ``paths`` under ``run_id``.

        Files that do not exist yet are recorded with ``sha256=None`` so a
        restore *deletes* them (the pre-write state was "absent").
        Duplicate content across files/runs is stored exactly once
        (content-addressed by sha256).
        """
        if not run_id:
            raise ValueError("run_id must be non-empty")
        self._objects.mkdir(parents=True, exist_ok=True)
        entries: list[SnapshotEntry] = []
        now = time.time()
        for raw in paths:
            p = Path(raw).resolve()
            try:
                data: Optional[bytes] = p.read_bytes()
            except FileNotFoundError:
                data = None
            if data is None:
                entry = SnapshotEntry(
                    run_id=run_id, path=str(p), sha256=None, size=0, ts=now
                )
            else:
                digest = _sha256_bytes(data)
                self._store_blob(digest, data)
                entry = SnapshotEntry(
                    run_id=run_id, path=str(p), sha256=digest, size=len(data), ts=now
                )
            entries.append(entry)
        # append to log only after all blobs are safely on disk
        with open(self._log_path, "a", encoding="utf-8") as fh:
            for entry in entries:
                fh.write(json.dumps(entry.to_record(), ensure_ascii=False) + "\n")
        return entries

    def snapshot_absent(self, run_id: str,
                        paths: list[str | Path]) -> list[SnapshotEntry]:
        """Record that ``paths`` did **not** exist before the run's mutation.

        T-059 (R-504/R-106): command side-effects create files that are
        only discovered *after* the command ran — by then the file exists,
        so a regular ``snapshot`` would wrongly capture the post state.
        The caller (who diffed the workspace) asserts the pre-state was
        "absent"; restore then deletes the file.  ``entries_for_run``'s
        first-snapshot-wins rule keeps any real earlier snapshot of the
        same path authoritative.
        """
        if not run_id:
            raise ValueError("run_id must be non-empty")
        now = time.time()
        entries = [
            SnapshotEntry(run_id=run_id, path=str(Path(raw).resolve()),
                          sha256=None, size=0, ts=now)
            for raw in paths
        ]
        with open(self._log_path, "a", encoding="utf-8") as fh:
            for entry in entries:
                fh.write(json.dumps(entry.to_record(),
                                    ensure_ascii=False) + "\n")
        return entries

    def seal(self, run_id: str, paths: list[str | Path]) -> None:
        """Record the post-write state of ``paths`` for ``run_id``.

        Call **after** the apply finished writing.  Restore uses these
        hashes to prove nothing changed externally since the run; also
        stores the post-write content as blobs so T-054 can render
        before/after diffs from the store alone.
        """
        if not run_id:
            raise ValueError("run_id must be non-empty")
        self._objects.mkdir(parents=True, exist_ok=True)
        now = time.time()
        records: list[dict] = []
        for raw in paths:
            p = Path(raw).resolve()
            try:
                data: Optional[bytes] = p.read_bytes()
            except FileNotFoundError:
                data = None
            digest: Optional[str] = None
            if data is not None:
                digest = _sha256_bytes(data)
                self._store_blob(digest, data)
            records.append(
                {
                    "type": "seal",
                    "run_id": run_id,
                    "path": str(p),
                    "sha256": digest,
                    "ts": now,
                }
            )
        with open(self._log_path, "a", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _store_blob(self, digest: str, data: bytes) -> None:
        blob = self._objects / digest
        if not blob.exists():  # dedup: one blob per unique content, ever
            tmp = blob.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, blob)

    # ------------------------------------------------------------------
    # log access
    # ------------------------------------------------------------------
    def entries_for_run(self, run_id: str) -> list[SnapshotEntry]:
        """Snapshot entries for ``run_id``, de-duplicated by path.

        If the same path was snapshotted twice within one run the *first*
        record wins — it is the true pre-write state of that run.
        """
        seen: dict[str, SnapshotEntry] = {}
        for rec in self._iter_log():
            if rec.get("run_id") != run_id or rec.get("type") != "snapshot":
                continue
            entry = SnapshotEntry.from_record(rec)
            if entry.path not in seen:  # first snapshot wins
                seen[entry.path] = entry
        return list(seen.values())

    def seals_for_run(self, run_id: str) -> dict[str, Optional[str]]:
        """Map ``path -> post-write sha256`` for ``run_id`` (last seal wins)."""
        out: dict[str, Optional[str]] = {}
        for rec in self._iter_log():
            if rec.get("run_id") != run_id or rec.get("type") != "seal":
                continue
            out[str(rec["path"])] = rec.get("sha256")
        return out

    def run_ids(self) -> list[str]:
        """Distinct run ids in log order (oldest first)."""
        out: list[str] = []
        for rec in self._iter_log():
            rid = str(rec.get("run_id", ""))
            if rid and rid not in out:
                out.append(rid)
        return out

    def prune(self, keep_run_ids: set[str] | frozenset[str]) -> int:
        """T-054 (R-106): retention hookup — drop runs outside ``keep_run_ids``.

        Rewrites the log keeping only records of surviving runs, then
        garbage-collects blobs no surviving record references.  Returns the
        number of run ids pruned.  Called next to the R-305 retention sweep
        with the sweep's surviving run set, so checkpoint storage stays
        bounded by the same policy as run artifacts.
        """
        records = self._iter_log()
        all_ids = {str(r.get("run_id", "")) for r in records if r.get("run_id")}
        doomed = all_ids - set(keep_run_ids)
        if not doomed:
            return 0
        survivors = [r for r in records if str(r.get("run_id", "")) not in doomed]
        tmp = self._log_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            for rec in survivors:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        os.replace(tmp, self._log_path)
        # blob GC: keep only hashes still referenced by surviving records
        live_hashes = {r.get("sha256") for r in survivors if r.get("sha256")}
        if self._objects.is_dir():
            for blob in self._objects.iterdir():
                if blob.name.endswith(".tmp") or blob.name not in live_hashes:
                    try:
                        blob.unlink()
                    except OSError:
                        pass  # best-effort — سيلتقطه المسح القادم
        return len(doomed)

    def _iter_log(self) -> list[dict]:
        if not self._log_path.exists():
            return []
        records: list[dict] = []
        with open(self._log_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue  # tolerate a torn tail line
                if isinstance(rec, dict):
                    # legacy tolerance: records without "type" are snapshots
                    rec.setdefault("type", "snapshot")
                    records.append(rec)
        return records

    # ------------------------------------------------------------------
    # restore
    # ------------------------------------------------------------------
    def restore_run(self, run_id: str) -> RestoreReport:
        """Restore every file of ``run_id`` to its snapshotted state.

        Each file is hash-verified first; conflicted files are refused and
        reported while clean siblings are still restored (partial success).
        """
        report = RestoreReport(run_id=run_id)
        entries = self.entries_for_run(run_id)
        if not entries:
            report.conflicts.append(
                Conflict(
                    path="",
                    expected_sha256=None,
                    actual_sha256=None,
                    reason=f"no checkpoint recorded for run_id {run_id!r}",
                )
            )
            return report
        seals = self.seals_for_run(run_id)
        for entry in entries:
            self._restore_entry(entry, seals, report)
        return report

    def restore_file(self, run_id: str, path: str | Path) -> RestoreReport:
        """Restore a single file from ``run_id``'s checkpoint."""
        target = str(Path(path).resolve())
        report = RestoreReport(run_id=run_id)
        entry = next(
            (e for e in self.entries_for_run(run_id) if e.path == target), None
        )
        if entry is None:
            report.conflicts.append(
                Conflict(
                    path=target,
                    expected_sha256=None,
                    actual_sha256=None,
                    reason=f"path not in checkpoint for run_id {run_id!r}",
                )
            )
            return report
        self._restore_entry(entry, self.seals_for_run(run_id), report)
        return report

    def _restore_entry(
        self,
        entry: SnapshotEntry,
        seals: dict[str, Optional[str]],
        report: RestoreReport,
    ) -> None:
        target = Path(entry.path)
        current = _sha256_file(target)

        # 1) Already at snapshot state -> no-op success.
        if current == entry.sha256:
            report.restored.append(entry.path)
            return

        # 2) External-modification guard: only proceed when the on-disk
        #    content is provably the run's own sealed output.
        if entry.path not in seals:
            report.conflicts.append(
                Conflict(
                    path=entry.path,
                    expected_sha256=None,
                    actual_sha256=current,
                    reason=(
                        "no seal record for this path; cannot verify the "
                        "on-disk content is the run's own output — refusing"
                    ),
                )
            )
            return
        sealed = seals[entry.path]
        if current != sealed:
            report.conflicts.append(
                Conflict(
                    path=entry.path,
                    expected_sha256=sealed,
                    actual_sha256=current,
                    reason="file changed externally after the run — refusing",
                )
            )
            return

        # 3) Verified: roll back to the snapshot state.
        if entry.sha256 is None:
            # pre-write state was "absent" -> rollback deletes the file.
            try:
                target.unlink()
            except FileNotFoundError:
                pass
            report.restored.append(entry.path)
            return
        blob = self._objects / entry.sha256
        if not blob.exists():
            report.conflicts.append(
                Conflict(
                    path=entry.path,
                    expected_sha256=sealed,
                    actual_sha256=current,
                    reason="checkpoint blob missing from object store",
                )
            )
            return
        data = blob.read_bytes()
        if _sha256_bytes(data) != entry.sha256:
            report.conflicts.append(
                Conflict(
                    path=entry.path,
                    expected_sha256=sealed,
                    actual_sha256=current,
                    reason="object store corruption: blob hash mismatch",
                )
            )
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".ckpt-restore.tmp")
        tmp.write_bytes(data)
        os.replace(tmp, target)
        report.restored.append(entry.path)
