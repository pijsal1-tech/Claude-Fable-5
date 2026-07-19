# -*- coding: utf-8 -*-
"""T-033 (R-305): Truthful Snapshots + RetentionPolicy — tests.

Covers:
- snapshot hashing: real sha256 content hashes for run-touched files;
  the "present-but-empty" artifact is gone (non-empty or absent — never
  empty-but-present)
- policy matrix: max_count / max_age_days / combined / pinned / no-op
- sweep: dry-run default (logs, deletes nothing), live delete,
  idempotence, missing dir, pinned survival on disk
- policy_from_config: defaults, parsing, loud error on bad section
"""
import hashlib
import time

import pytest

from chain.bridge import _build_project_snapshot
from sessions.retention import (
    RetentionPolicy,
    SweepReport,
    plan_sweep,
    policy_from_config,
    sweep,
)


# ═══════════════ Truthful snapshots ═══════════════

def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_snapshot_contains_real_hashes():
    files = {"a.py": "print('a')", "b.md": "# دليل"}
    snap = _build_project_snapshot("/proj/x", files)
    assert snap is not None
    assert snap.project_root == "/proj/x" and snap.project_id == "x"
    assert snap.relevant_file_hashes == {
        "a.py": _sha("print('a')"),
        "b.md": _sha("# دليل"),
    }


def test_snapshot_includes_single_file_path_content():
    snap = _build_project_snapshot("/proj/x", None, "main.py", "x = 1")
    assert snap is not None
    assert snap.relevant_file_hashes == {"main.py": _sha("x = 1")}


def test_snapshot_files_take_precedence_over_file_path():
    files = {"main.py": "from files"}
    snap = _build_project_snapshot("/p", files, "main.py", "from single")
    assert snap.relevant_file_hashes["main.py"] == _sha("from files")


def test_snapshot_never_empty_but_present():
    """قبول R-305: غير فارغة أو غائبة — أبدًا موجودة-وفارغة."""
    assert _build_project_snapshot("/proj/x", None) is None
    assert _build_project_snapshot("/proj/x", {}) is None
    assert _build_project_snapshot("", {"a": "x"}) is None  # بلا جذر = بلا لقطة


def test_snapshot_to_dict_roundtrip():
    snap = _build_project_snapshot("/p", {"f.txt": "hi"})
    d = snap.to_dict()
    assert d["relevant_file_hashes"] == {"f.txt": _sha("hi")}


# ═══════════════ plan_sweep — policy matrix ═══════════════

NOW = 1_700_000_000.0
DAY = 86400.0


def _entries(*ages_days):
    """(name, mtime) — e0 الأحدث."""
    return [(f"run-{i:02d}", NOW - age * DAY)
            for i, age in enumerate(ages_days)]


def test_policy_validation():
    with pytest.raises(ValueError):
        RetentionPolicy(max_count=-1)
    with pytest.raises(ValueError):
        RetentionPolicy(max_age_days=-0.5)


def test_no_limits_no_deletion():
    kept, deleted = plan_sweep(_entries(0, 5, 100), RetentionPolicy(),
                               now=NOW)
    assert deleted == [] and len(kept) == 3


def test_max_count_keeps_newest():
    kept, deleted = plan_sweep(_entries(0, 1, 2, 3, 4),
                               RetentionPolicy(max_count=2), now=NOW)
    assert kept == ["run-00", "run-01"]
    assert deleted == ["run-02", "run-03", "run-04"]


def test_max_count_zero_deletes_all_unpinned():
    kept, deleted = plan_sweep(_entries(0, 1),
                               RetentionPolicy(max_count=0), now=NOW)
    assert kept == [] and len(deleted) == 2


def test_max_age_deletes_old_even_within_count():
    kept, deleted = plan_sweep(
        _entries(0, 1, 40),
        RetentionPolicy(max_count=10, max_age_days=30), now=NOW)
    assert "run-02" in deleted and kept == ["run-00", "run-01"]


def test_combined_survives_both_limits_only():
    # 5 عناصر: أعمار 0,1,2,50,60 — count=3 & age=30
    kept, deleted = plan_sweep(
        _entries(0, 1, 2, 50, 60),
        RetentionPolicy(max_count=3, max_age_days=30), now=NOW)
    assert kept == ["run-00", "run-01", "run-02"]
    assert set(deleted) == {"run-03", "run-04"}


def test_pinned_survives_count_and_age():
    kept, deleted = plan_sweep(
        _entries(0, 1, 2, 100),
        RetentionPolicy(max_count=1, max_age_days=30,
                        pinned=frozenset({"run-03", "run-02"})), now=NOW)
    assert "run-03" in kept and "run-02" in kept   # مثبت فوق العمر والعدد
    assert kept == ["run-00", "run-02", "run-03"]
    assert deleted == ["run-01"]


def test_pinned_does_not_consume_count_budget():
    # count=2 والمثبت لا يستهلك — أحدث اثنين غير مثبتين يبقيان أيضًا
    kept, _ = plan_sweep(
        _entries(0, 1, 2),
        RetentionPolicy(max_count=2, pinned=frozenset({"run-00"})),
        now=NOW)
    assert kept == ["run-00", "run-01", "run-02"]


# ═══════════════ sweep — on-disk GC ═══════════════

def _make_runs(root, *ages_days):
    root.mkdir(parents=True, exist_ok=True)
    names = []
    for i, age in enumerate(ages_days):
        d = root / f"run-{i:02d}"
        d.mkdir()
        (d / "state.json").write_text("{}", encoding="utf-8")
        mtime = NOW - age * DAY
        import os
        os.utime(d, (mtime, mtime))
        names.append(d.name)
    return names


def test_sweep_dry_run_logs_but_deletes_nothing(tmp_path):
    runs = tmp_path / ".ai_runs"
    _make_runs(runs, 0, 1, 2)
    logs = []
    report = sweep(runs, RetentionPolicy(max_count=1, dry_run=True),
                   now=NOW, log=logs.append)
    assert report.dry_run is True
    assert set(report.would_delete) == {"run-01", "run-02"}
    # لا حذف فعلي
    assert sorted(p.name for p in runs.iterdir()) == [
        "run-00", "run-01", "run-02"]
    assert len(logs) == 2 and all("dry-run" in ln for ln in logs)


def test_sweep_live_deletes_and_pinned_survives(tmp_path):
    runs = tmp_path / ".ai_runs"
    _make_runs(runs, 0, 1, 2, 3)
    report = sweep(runs, RetentionPolicy(
        max_count=1, pinned=frozenset({"run-03"}), dry_run=False), now=NOW)
    assert report.dry_run is False
    remaining = sorted(p.name for p in runs.iterdir())
    assert remaining == ["run-00", "run-03"]     # الأحدث + المثبت
    assert set(report.deleted) == {"run-01", "run-02"}


def test_sweep_idempotent(tmp_path):
    runs = tmp_path / ".ai_runs"
    _make_runs(runs, 0, 1, 2)
    policy = RetentionPolicy(max_count=2, dry_run=False)
    r1 = sweep(runs, policy, now=NOW)
    r2 = sweep(runs, policy, now=NOW)
    assert r1.deleted == ["run-02"]
    assert r2.deleted == []                      # الثاني لا يجد ما يحذفه
    assert sorted(r2.kept) == ["run-00", "run-01"]


def test_sweep_missing_dir_is_noop(tmp_path):
    report = sweep(tmp_path / "nope", RetentionPolicy(max_count=1))
    assert report.kept == [] and report.deleted == []


def test_sweep_default_policy_is_full_noop(tmp_path):
    """رجعية: بلا config = سلوك ما-قبل-T-033 — صفر حذف."""
    runs = tmp_path / ".ai_runs"
    _make_runs(runs, 0, 500)
    report = sweep(runs, RetentionPolicy(), now=NOW)
    assert report.deleted == [] and len(report.kept) == 2


# ═══════════════ policy_from_config ═══════════════

def test_config_missing_section_gives_safe_default():
    p = policy_from_config(None)
    assert p == RetentionPolicy()
    assert p.dry_run is True and p.max_count is None


def test_config_parses_all_fields():
    p = policy_from_config({
        "max_count": 5, "max_age_days": 30,
        "pinned": ["run-aa", "run-bb"], "dry_run": False,
    })
    assert p.max_count == 5 and p.max_age_days == 30.0
    assert p.pinned == frozenset({"run-aa", "run-bb"})
    assert p.dry_run is False


def test_config_null_limits_stay_disabled():
    p = policy_from_config({"max_count": None, "max_age_days": None})
    assert p.max_count is None and p.max_age_days is None


def test_config_bad_section_raises_loudly():
    with pytest.raises(ValueError):
        policy_from_config("not-a-dict")  # type: ignore[arg-type]
