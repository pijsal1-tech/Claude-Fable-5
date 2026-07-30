# -*- coding: utf-8 -*-
"""TSK-718 (FI-05/1) — عقد وحدة snapshot الفهرس: حفظ ذرّي + تحميل متشكك.

معايير القبول (DEVELOPMENT_TASKS §BATCH-P1 / TSK-718):
- roundtrip: حفظ ثم تحميل بنفس الجذر ⇒ نفس القائمة بنفس الترتيب.
- جذر مغاير ⇒ None (مشروع نُقل — يسقط لـ rebuild).
- نسخة مغايرة ⇒ None.
- ملف فاسد/غائب/شكل شاذ ⇒ None — **بلا استثناء**.
- وجهة غير قابلة للكتابة ⇒ save يعيد False — **بلا استثناء**.
- مسارات خبيثة (مطلقة/../Windows drive) ⇒ None.
"""
import json
import pathlib

import pytest

from core.index_snapshot import (SNAPSHOT_VERSION, load_snapshot,
                                 save_snapshot)


@pytest.fixture()
def snap(tmp_path):
    return tmp_path / ".ai_runs" / "project_index.json"


def test_roundtrip_preserves_list_and_order(tmp_path, snap):
    rels = ["a.py", "src/b.py", "src/nested/c.txt", "z last.md"]
    assert save_snapshot(snap, tmp_path, rels) is True
    assert snap.is_file()
    assert load_snapshot(snap, tmp_path) == rels


def test_roundtrip_empty_list(tmp_path, snap):
    assert save_snapshot(snap, tmp_path, []) is True
    assert load_snapshot(snap, tmp_path) == []


def test_root_mismatch_returns_none(tmp_path, snap):
    other = tmp_path / "other_project"
    other.mkdir()
    assert save_snapshot(snap, tmp_path, ["a.py"]) is True
    assert load_snapshot(snap, other) is None


def test_version_mismatch_returns_none(tmp_path, snap):
    assert save_snapshot(snap, tmp_path, ["a.py"]) is True
    data = json.loads(snap.read_text(encoding="utf-8"))
    data["version"] = SNAPSHOT_VERSION + 1
    snap.write_text(json.dumps(data), encoding="utf-8")
    assert load_snapshot(snap, tmp_path) is None


def test_missing_file_returns_none(tmp_path, snap):
    assert load_snapshot(snap, tmp_path) is None


def test_corrupt_json_returns_none(tmp_path, snap):
    snap.parent.mkdir(parents=True)
    snap.write_text("{not json!!", encoding="utf-8")
    assert load_snapshot(snap, tmp_path) is None


@pytest.mark.parametrize("payload", [
    "[]",                                            # ليست dict
    '{"version": 1}',                                # بلا root/files
    '{"version": 1, "root": "X", "files": "nope"}',  # files ليست قائمة
])
def test_malformed_shapes_return_none(tmp_path, snap, payload):
    snap.parent.mkdir(parents=True)
    snap.write_text(payload, encoding="utf-8")
    assert load_snapshot(snap, tmp_path) is None


@pytest.mark.parametrize("bad", [
    "/etc/passwd",            # مطلق posix
    "\\\\server\\share",      # مطلق UNC
    "C:/Windows/system32",    # مطلق Windows drive
    "../outside.py",          # هارب
    "src/../../outside.py",   # هارب متداخل
    "",                       # فارغ
    123,                      # غير نصي
])
def test_hostile_entries_return_none(tmp_path, snap, bad):
    snap.parent.mkdir(parents=True)
    payload = {"version": SNAPSHOT_VERSION,
               "root": pathlib.Path(tmp_path).resolve().as_posix(),
               "files": ["ok.py", bad]}
    snap.write_text(json.dumps(payload, default=str), encoding="utf-8")
    assert load_snapshot(snap, tmp_path) is None


def test_unwritable_destination_returns_false(tmp_path):
    blocker = tmp_path / "blocked"
    blocker.write_text("file not dir", encoding="utf-8")
    # الوجهة تحت *ملف* — mkdir(parents) سيفشل ⇒ False بلا استثناء.
    target = blocker / "sub" / "snap.json"
    assert save_snapshot(target, tmp_path, ["a.py"]) is False


def test_atomic_no_tmp_leftover(tmp_path, snap):
    assert save_snapshot(snap, tmp_path, ["a.py"]) is True
    leftovers = list(snap.parent.glob("*.tmp"))
    assert leftovers == []


def test_save_overwrites_previous(tmp_path, snap):
    assert save_snapshot(snap, tmp_path, ["old.py"]) is True
    assert save_snapshot(snap, tmp_path, ["new.py", "two.py"]) is True
    assert load_snapshot(snap, tmp_path) == ["new.py", "two.py"]
