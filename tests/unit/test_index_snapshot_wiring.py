# -*- coding: utf-8 -*-
"""TSK-719 (FI-05/2) — عقد توصيل snapshot بـ ProjectIndex.

معايير القبول (DEVELOPMENT_TASKS §BATCH-P1 / TSK-719):
- تكافؤ ذهبي: نتائج lookup/files متطابقة بين بناء طازج وتحميل snapshot.
- التحميل الناجح **بلا مشية شجرية** (rebuild_count يبقى 0).
- snapshot قديم يتقارب بعد refresh_if_stale(force=True).
- فاشل/غائب/جذر مغاير ⇒ rebuild كالسابق (لا كسر للسلوك القائم).
- الحفظ بعد rebuild فقط عند تغيّر القائمة (لا churn من sweep).
- خطاف write-through يعمل فوق فهرس مبذور.
"""
import json
import pathlib

import pytest

from context.index import ProjectIndex
from core.index_snapshot import load_snapshot, save_snapshot


def _make_tree(root: pathlib.Path) -> None:
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (root / "src" / "util.py").write_text("y = 2\n", encoding="utf-8")
    (root / "readme.md").write_text("# hi\n", encoding="utf-8")


@pytest.fixture()
def proj(tmp_path):
    _make_tree(tmp_path)
    return tmp_path


@pytest.fixture()
def snap(proj):
    return proj / ".ai_runs" / "project_index.json"


def test_rebuild_saves_snapshot(proj, snap):
    idx = ProjectIndex(proj, snapshot_path=snap)
    assert idx.rebuild_count == 1              # لا snapshot ⇒ rebuild عادي
    rels = load_snapshot(snap, proj)
    assert rels is not None
    assert "src/app.py" in rels and "readme.md" in rels


def test_seed_from_snapshot_no_tree_walk(proj, snap):
    ProjectIndex(proj, snapshot_path=snap)     # يكتب الـ snapshot
    idx2 = ProjectIndex(proj, snapshot_path=snap)
    assert idx2.rebuild_count == 0             # بذر بلا أي rebuild


def test_golden_equivalence_fresh_vs_seeded(proj, snap):
    fresh = ProjectIndex(proj)                 # بلا snapshot — المرجع
    ProjectIndex(proj, snapshot_path=snap)     # يكتب snapshot
    seeded = ProjectIndex(proj, snapshot_path=snap)
    assert seeded.rebuild_count == 0
    assert seeded.files == fresh.files
    assert seeded.lookup("app.py") == fresh.lookup("app.py")
    assert seeded.lookup_name("util.py") == fresh.lookup_name("util.py")
    assert seeded.lookup_ext(".md") == fresh.lookup_ext(".md")


def test_stale_snapshot_converges_on_forced_sweep(proj, snap):
    ProjectIndex(proj, snapshot_path=snap)
    # تعديل خارجي بعد كتابة الـ snapshot — القديم لا يعرفه.
    (proj / "new_file.txt").write_text("later\n", encoding="utf-8")
    idx = ProjectIndex(proj, snapshot_path=snap)
    seeded_names = {p.name for p in idx.files}
    assert "new_file.txt" not in seeded_names  # نافذة staleness موثقة
    assert idx.refresh_if_stale(force=True) is True
    assert "new_file.txt" in {p.name for p in idx.files}   # تقارب
    # والحفظ التقط القائمة الجديدة (تغيّرت ⇒ كُتبت).
    assert "new_file.txt" in (load_snapshot(snap, proj) or [])


def test_corrupt_snapshot_falls_back_to_rebuild(proj, snap):
    snap.parent.mkdir(parents=True)
    snap.write_text("{broken", encoding="utf-8")
    idx = ProjectIndex(proj, snapshot_path=snap)
    assert idx.rebuild_count == 1              # سقوط نظيف لـ rebuild
    assert "app.py" in {p.name for p in idx.files}


def test_foreign_root_snapshot_rejected(proj, snap, tmp_path_factory):
    other = tmp_path_factory.mktemp("other_project")
    (other / "z.py").write_text("z\n", encoding="utf-8")
    save_snapshot(snap, other, ["z.py"])       # snapshot لجذر آخر
    idx = ProjectIndex(proj, snapshot_path=snap)
    assert idx.rebuild_count == 1              # رُفض ⇒ rebuild
    assert "z.py" not in {p.name for p in idx.files}


def test_no_save_churn_when_list_unchanged(proj, snap):
    idx = ProjectIndex(proj, snapshot_path=snap)
    mtime1 = snap.stat().st_mtime_ns
    idx.refresh_if_stale(force=True)           # نفس الشجرة ⇒ لا كتابة
    assert snap.stat().st_mtime_ns == mtime1


def test_write_through_hook_on_seeded_index(proj, snap):
    ProjectIndex(proj, snapshot_path=snap)
    idx = ProjectIndex(proj, snapshot_path=snap)
    assert idx.rebuild_count == 0
    new = proj / "hooked.py"
    new.write_text("h\n", encoding="utf-8")
    idx.notify_write("hooked.py")              # نفس مسار خطاف T-049
    assert idx.lookup_name("hooked.py") == [new.resolve()]


def test_no_snapshot_path_behaves_as_before(proj):
    idx = ProjectIndex(proj)                   # التوقيع القديم يعمل كما هو
    assert idx.rebuild_count == 1
    assert not (proj / ".ai_runs").exists()    # صفر آثار جانبية


def test_server_snapshot_path_inside_ai_runs(proj):
    import server
    p = pathlib.Path(server._index_snapshot_path(str(proj)))
    assert p.parts[-2:] == (".ai_runs", "project_index.json")
    assert pathlib.Path(str(proj)) in p.parents
