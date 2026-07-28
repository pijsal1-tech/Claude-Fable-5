# -*- coding: utf-8 -*-
"""QA-T07 — أمن الاستعادة (Zip-Slip) — TSK-105 (NF-15).

Fixtures (مُصنَّعة في tmp_path — صفر نداءات AI خارجية):
- ZIP سليم → يُستعاد.
- ZIP بعضو ``../evil.txt`` → 400 ورفض كامل (لا فك جزئي).
- ZIP بمسار مطلق → 400.
- ZIP بـ symlink → 400.
بعد كل حالة خبيثة: فحص فعلي للقرص — لا ملف واحد يُكتب خارج الجذر
(ولا داخله — الرفض كامل).
"""
import io
import zipfile

import pytest

import server
from actions.file_manager import FileManager


@pytest.fixture()
def restore_env(tmp_path, monkeypatch):
    """مشروع مؤقت + fm مبدّل على server + مجلد نسخ احتياطية."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "keep.txt").write_text("موجود", encoding="utf-8")
    fm = FileManager(str(root))
    monkeypatch.setattr(server, "fm", fm)
    backups_dir = root / ".webdev_backups" / "full"
    backups_dir.mkdir(parents=True)
    outside = tmp_path / "outside_root"
    outside.mkdir()
    return root, backups_dir, outside


def _write_zip(path, members, symlink_members=()):
    """بناء ZIP: members = [(اسم، محتوى)]، symlink_members = [(اسم، هدف)]."""
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in members:
            zf.writestr(name, content)
        for name, target in symlink_members:
            info = zipfile.ZipInfo(name)
            info.external_attr = (0o120777 << 16)  # S_IFLNK | 0777
            zf.writestr(info, target)


def _post_restore(name):
    return server.app.test_client().post(f"/api/restore/{name}")


def _disk_snapshot(root):
    """لقطة ملفات المشروع — باستثناء مجلد النسخ الاحتياطية نفسه."""
    return sorted(
        str(p.relative_to(root)) for p in root.rglob("*")
        if p.is_file() and ".webdev_backups" not in p.parts
    )


class TestSafeZipRestored:
    def test_valid_zip_restores(self, restore_env):
        root, backups_dir, _ = restore_env
        _write_zip(backups_dir / "good.zip",
                   [("a.txt", "A"), ("sub/b.txt", "B")])
        resp = _post_restore("good.zip")
        assert resp.status_code == 200 and resp.get_json()["ok"] is True
        assert (root / "a.txt").read_text(encoding="utf-8") == "A"
        assert (root / "sub" / "b.txt").read_text(encoding="utf-8") == "B"


class TestMaliciousZipsRejected:
    def test_dotdot_member_rejected_completely(self, restore_env):
        """معيار القبول الحرفي: عضو ../evil.txt → 400 ورفض كامل."""
        root, backups_dir, outside = restore_env
        before = _disk_snapshot(root)
        _write_zip(backups_dir / "evil.zip",
                   [("ok.txt", "bait"), ("../evil.txt", "pwned")])
        resp = _post_restore("evil.zip")
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["ok"] is False
        assert any(v["reason"] == "escapes_root" for v in body["violations"])
        # فحص فعلي للقرص: لا شيء خارج الجذر ولا فك جزئي داخله
        assert not (root.parent / "evil.txt").exists()
        assert not (root / "ok.txt").exists(), "رفض كامل — لا فك جزئي"
        assert _disk_snapshot(root) == before

    def test_absolute_path_member_rejected(self, restore_env, tmp_path):
        root, backups_dir, outside = restore_env
        before = _disk_snapshot(root)
        abs_target = str(outside / "abs_evil.txt")
        _write_zip(backups_dir / "abs.zip",
                   [("ok.txt", "bait"), (abs_target, "pwned")])
        resp = _post_restore("abs.zip")
        assert resp.status_code == 400
        body = resp.get_json()
        assert any(v["reason"] in ("absolute_path", "escapes_root")
                   for v in body["violations"])
        assert not (outside / "abs_evil.txt").exists()
        assert _disk_snapshot(root) == before

    def test_symlink_member_rejected(self, restore_env, tmp_path):
        root, backups_dir, outside = restore_env
        before = _disk_snapshot(root)
        _write_zip(backups_dir / "link.zip",
                   [("ok.txt", "bait")],
                   symlink_members=[("sneaky", str(outside))])
        resp = _post_restore("link.zip")
        assert resp.status_code == 400
        body = resp.get_json()
        assert any(v["reason"] == "symlink_member" for v in body["violations"])
        assert not (root / "sneaky").exists()
        assert _disk_snapshot(root) == before

    def test_missing_backup_still_404(self, restore_env):
        """المسار القديم لغير الموجود محفوظ (404 لا 400)."""
        resp = _post_restore("no_such.zip")
        assert resp.status_code == 404
