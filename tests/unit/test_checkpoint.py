# -*- coding: utf-8 -*-
"""T-053 (R-106): CheckpointManager — content-addressed pre-write snapshots.

Acceptance criteria under test:
* 5-file batch snapshot + restore is byte-exact
* per-file restore leaves siblings untouched
* external-modification refusal (with conflict report)
* duplicate content stored once (dedup asserted)
"""

import hashlib
import json
from pathlib import Path

import pytest

from core.checkpoint import (
    CheckpointManager,
    Conflict,
    RestoreReport,
    SnapshotEntry,
)


@pytest.fixture()
def store(tmp_path):
    return CheckpointManager(tmp_path / "ckpt")


@pytest.fixture()
def project(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    return proj


def _mkfiles(project: Path, spec: dict[str, bytes]) -> list[Path]:
    out = []
    for name, content in spec.items():
        p = project / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        out.append(p)
    return out


def _apply(paths_content: dict[Path, bytes]) -> None:
    """Simulate the run writing new content (post-snapshot)."""
    for p, content in paths_content.items():
        p.write_bytes(content)


class TestSnapshot:
    def test_snapshot_records_entries_with_hashes(self, store, project):
        files = _mkfiles(project, {"a.py": b"alpha", "b.py": b"beta"})
        entries = store.snapshot("run-1", files)
        assert len(entries) == 2
        by_path = {Path(e.path).name: e for e in entries}
        assert by_path["a.py"].sha256 == hashlib.sha256(b"alpha").hexdigest()
        assert by_path["b.py"].size == 4

    def test_missing_file_recorded_as_absent(self, store, project):
        ghost = project / "new_file.py"
        entries = store.snapshot("run-1", [ghost])
        assert entries[0].sha256 is None
        assert entries[0].size == 0

    def test_empty_run_id_rejected(self, store, project):
        with pytest.raises(ValueError):
            store.snapshot("", [project / "x"])

    def test_log_is_jsonl_keyed_by_run_id(self, store, project, tmp_path):
        files = _mkfiles(project, {"a.py": b"alpha"})
        store.snapshot("run-7", files)
        log = tmp_path / "ckpt" / CheckpointManager.LOG_NAME
        records = [json.loads(l) for l in log.read_text().splitlines()]
        assert records[0]["run_id"] == "run-7"
        assert records[0]["type"] == "snapshot"


class TestDedup:
    def test_duplicate_content_stored_once(self, store, project, tmp_path):
        # same content in 3 files across 2 runs -> exactly ONE blob
        files = _mkfiles(
            project, {"a.py": b"same", "b.py": b"same", "c.py": b"same"}
        )
        store.snapshot("run-1", files[:2])
        store.snapshot("run-2", files[2:])
        objects = tmp_path / "ckpt" / CheckpointManager.OBJECTS_DIR
        blobs = [p for p in objects.iterdir() if not p.name.endswith(".tmp")]
        assert len(blobs) == 1
        assert blobs[0].read_bytes() == b"same"


class TestRestoreRun:
    def test_5_file_batch_byte_exact(self, store, project):
        originals = {
            "a.py": b"one",
            "b.py": b"two\ntwo",
            "sub/c.py": b"three",
            "d.bin": bytes(range(256)),
            "e.txt": "نص عربي".encode("utf-8"),
        }
        files = _mkfiles(project, originals)
        store.snapshot("run-1", files)
        _apply({p: b"MUTATED-" + p.name.encode() for p in files})
        store.seal("run-1", files)

        report = store.restore_run("run-1")
        assert report.status == "success"
        assert len(report.restored) == 5
        for name, content in originals.items():
            assert (project / name).read_bytes() == content

    def test_created_file_rollback_deletes_it(self, store, project):
        ghost = project / "created.py"
        store.snapshot("run-1", [ghost])
        ghost.write_bytes(b"made by the run")
        store.seal("run-1", [ghost])

        report = store.restore_run("run-1")
        assert report.status == "success"
        assert not ghost.exists()

    def test_unknown_run_refused(self, store):
        report = store.restore_run("no-such-run")
        assert report.status == "refused"
        assert "no checkpoint" in report.conflicts[0].reason

    def test_noop_when_already_at_snapshot_state(self, store, project):
        files = _mkfiles(project, {"a.py": b"alpha"})
        store.snapshot("run-1", files)
        store.seal("run-1", files)  # run wrote nothing new
        report = store.restore_run("run-1")
        assert report.status == "success"
        assert (project / "a.py").read_bytes() == b"alpha"


class TestRestoreFile:
    def test_per_file_restore_leaves_siblings(self, store, project):
        files = _mkfiles(project, {"a.py": b"A0", "b.py": b"B0"})
        store.snapshot("run-1", files)
        _apply({files[0]: b"A1", files[1]: b"B1"})
        store.seal("run-1", files)

        report = store.restore_file("run-1", files[0])
        assert report.status == "success"
        assert files[0].read_bytes() == b"A0"  # restored
        assert files[1].read_bytes() == b"B1"  # sibling untouched

    def test_path_not_in_checkpoint_refused(self, store, project):
        files = _mkfiles(project, {"a.py": b"A0"})
        store.snapshot("run-1", files)
        report = store.restore_file("run-1", project / "other.py")
        assert report.status == "refused"
        assert "not in checkpoint" in report.conflicts[0].reason


class TestConflictRefusal:
    def test_external_edit_refused_with_report(self, store, project):
        files = _mkfiles(project, {"a.py": b"A0"})
        store.snapshot("run-1", files)
        _apply({files[0]: b"A1"})
        store.seal("run-1", files)
        # human edits AFTER the run
        files[0].write_bytes(b"HUMAN EDIT")

        report = store.restore_run("run-1")
        assert report.status == "refused"
        c = report.conflicts[0]
        assert c.path == str(files[0])
        assert c.actual_sha256 == hashlib.sha256(b"HUMAN EDIT").hexdigest()
        assert c.expected_sha256 == hashlib.sha256(b"A1").hexdigest()
        assert "externally" in c.reason
        # and the file is NOT touched
        assert files[0].read_bytes() == b"HUMAN EDIT"

    def test_partial_restore_clean_siblings_still_restored(self, store, project):
        files = _mkfiles(project, {"a.py": b"A0", "b.py": b"B0"})
        store.snapshot("run-1", files)
        _apply({files[0]: b"A1", files[1]: b"B1"})
        store.seal("run-1", files)
        files[1].write_bytes(b"HUMAN EDIT")  # conflict only on b.py

        report = store.restore_run("run-1")
        assert report.status == "partial"
        assert files[0].read_bytes() == b"A0"  # clean sibling restored
        assert files[1].read_bytes() == b"HUMAN EDIT"  # conflicted untouched
        assert [c.path for c in report.conflicts] == [str(files[1])]

    def test_missing_seal_refused(self, store, project):
        # snapshot taken but run never sealed (crash mid-apply):
        # current content is unverifiable -> refuse.
        files = _mkfiles(project, {"a.py": b"A0"})
        store.snapshot("run-1", files)
        _apply({files[0]: b"A1"})  # no seal!

        report = store.restore_run("run-1")
        assert report.status == "refused"
        assert "no seal record" in report.conflicts[0].reason

    def test_absent_snapshot_with_external_content_refused(self, store, project):
        ghost = project / "created.py"
        store.snapshot("run-1", [ghost])
        ghost.write_bytes(b"run output")
        store.seal("run-1", [ghost])
        ghost.write_bytes(b"then a human changed it")

        report = store.restore_run("run-1")
        assert report.status == "refused"
        assert ghost.read_bytes() == b"then a human changed it"


class TestReportShape:
    def test_report_serializes_for_ws(self, store, project):
        files = _mkfiles(project, {"a.py": b"A0"})
        store.snapshot("run-1", files)
        _apply({files[0]: b"A1"})
        store.seal("run-1", files)
        d = store.restore_run("run-1").to_dict()
        assert d["status"] == "success"
        assert d["run_id"] == "run-1"
        assert isinstance(d["restored"], list)
        assert isinstance(d["conflicts"], list)

    def test_run_ids_listed_in_order(self, store, project):
        files = _mkfiles(project, {"a.py": b"A0"})
        store.snapshot("run-1", files)
        store.snapshot("run-2", files)
        store.snapshot("run-1", files)  # repeat must not duplicate
        assert store.run_ids() == ["run-1", "run-2"]

    def test_first_snapshot_wins_within_run(self, store, project):
        files = _mkfiles(project, {"a.py": b"ORIGINAL"})
        store.snapshot("run-1", files)
        _apply({files[0]: b"MID"})
        store.snapshot("run-1", files)  # second snapshot same run
        _apply({files[0]: b"FINAL"})
        store.seal("run-1", files)

        report = store.restore_run("run-1")
        assert report.status == "success"
        assert files[0].read_bytes() == b"ORIGINAL"  # not b"MID"

    def test_torn_log_line_tolerated(self, store, project, tmp_path):
        files = _mkfiles(project, {"a.py": b"A0"})
        store.snapshot("run-1", files)
        log = tmp_path / "ckpt" / CheckpointManager.LOG_NAME
        with open(log, "a") as fh:
            fh.write('{"run_id": "run-9", "pa')  # torn tail
        assert store.run_ids() == ["run-1"]
