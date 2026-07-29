# -*- coding: utf-8 -*-
"""TSK-618 (ASF-07/NF-28): تضييق except الابتلاعي في فحص symlink.

الخلفية: `except Exception: pass` القديم (path_policy.py:107–108) كان
يضم `raise PermissionError` نفسه داخل الـ try ⇒ الرفض يُبتلع فور رفعه
والفحص ميت بالكامل (NF-28 — أشد من توصيف ASF-07). الإصلاح: فصل القياس
(is_symlink داخل try ضيق يلتقط OSError موسومًا بتحذير) عن القرار
(raise خارجه).

المصفوفة (القبول: خطأ FS → تحذير مسجل والاحتواء النهائي يعمل؛
عدّاد NF-14 لا يرتفع):
- symlink داخلي لملف داخلي → PermissionError (كان يمر — NF-28 A)
- ملف عبر مجلد symlink → PermissionError (كان يمر — NF-28 B)
- allow_symlinks=True → يمر (السلوك الاختياري محفوظ)
- ملف عادي بلا symlinks → يمر (المسار الشائع بلا تغيير)
- خطأ FS أثناء is_symlink → تحذير في السجل + الفحص يتابع +
  الاحتواء/الأسرار النهائيان يعملان (القبول حرفيًا)
- الخطوط الصلبة تبقى: symlink هارب خارج الجذر يُرفض بالاحتواء؛
  ألياس سر داخلي يُرفض بفحص الأسرار
- لا `except Exception: pass` في الملف (حارس بنيوي — NF-14)
"""
from __future__ import annotations

import logging
import os
import pathlib
import re

import pytest

from chain.path_policy import resolve_workspace_path

pytestmark = pytest.mark.skipif(
    os.name == "nt", reason="symlink semantics differ on Windows")

ROOT = pathlib.Path(__file__).resolve().parents[2]
POLICY_SRC = ROOT / "chain" / "path_policy.py"


def _project(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "real.txt").write_text("x", encoding="utf-8")
    return root


# ═══════════════ الفحص يعمل الآن (كان ميتًا — NF-28) ═══════════════

class TestSymlinkDenialAlive:

    def test_in_root_file_symlink_denied(self, tmp_path):
        root = _project(tmp_path)
        os.symlink(root / "real.txt", root / "link.txt")
        with pytest.raises(PermissionError, match="Symlinks"):
            resolve_workspace_path(root, "link.txt", allow_symlinks=False)

    def test_file_under_symlinked_dir_denied(self, tmp_path):
        root = _project(tmp_path)
        sub = root / "sub"
        sub.mkdir()
        (sub / "f.txt").write_text("y", encoding="utf-8")
        os.symlink(sub, root / "dlink")
        with pytest.raises(PermissionError, match="Symlinks"):
            resolve_workspace_path(root, "dlink/f.txt",
                                   allow_symlinks=False)

    def test_allow_symlinks_true_still_permits(self, tmp_path):
        root = _project(tmp_path)
        os.symlink(root / "real.txt", root / "link.txt")
        resolved = resolve_workspace_path(root, "link.txt",
                                          allow_symlinks=True)
        assert resolved.name == "real.txt"

    def test_plain_file_unaffected(self, tmp_path):
        root = _project(tmp_path)
        resolved = resolve_workspace_path(root, "real.txt",
                                          allow_symlinks=False)
        assert resolved == (root / "real.txt").resolve()


# ═══════════════ خطأ FS → تحذير موسوم + الاحتواء يعمل ═══════════════

class TestFsErrorLoggedNotSwallowed:

    def test_oserror_logs_warning_and_containment_still_applies(
            self, tmp_path, monkeypatch, caplog):
        """قبول TSK-618 حرفيًا: خطأ FS → تحذير مسجل والاحتواء النهائي يعمل."""
        root = _project(tmp_path)

        def _boom(self):
            raise OSError("simulated FS failure")

        monkeypatch.setattr(pathlib.Path, "is_symlink", _boom)
        with caplog.at_level(logging.WARNING, logger="chain.path_policy"):
            # المسار الشرعي يمر رغم فشل الفحص (الفحص طبقة إضافية)
            resolved = resolve_workspace_path(root, "real.txt",
                                              allow_symlinks=False)
            assert resolved == (root / "real.txt").resolve()
            # الاحتواء النهائي (الخط الصلب) لا يزال يرفض الهروب
            with pytest.raises(PermissionError, match="outside project"):
                resolve_workspace_path(root, "../outside.txt",
                                       allow_symlinks=False)
        warnings = [r for r in caplog.records
                    if "symlink check failed" in r.getMessage()]
        assert warnings, "لا تحذير مسجل — الابتلاع الصامت عاد"

    def test_no_warning_on_clean_path(self, tmp_path, caplog):
        """سلبي: بلا خطأ FS لا ضجيج في السجل."""
        root = _project(tmp_path)
        with caplog.at_level(logging.WARNING, logger="chain.path_policy"):
            resolve_workspace_path(root, "real.txt", allow_symlinks=False)
        assert not [r for r in caplog.records
                    if "symlink check failed" in r.getMessage()]


# ═══════════════ الخطوط الصلبة القائمة تبقى (حماية انحدار) ═══════════

class TestHardLinesPreserved:

    def test_escaping_symlink_still_denied_by_containment(self, tmp_path):
        root = _project(tmp_path)
        outside = tmp_path / "secret_outside.txt"
        outside.write_text("s", encoding="utf-8")
        os.symlink(outside, root / "esc.txt")
        with pytest.raises(PermissionError):
            resolve_workspace_path(root, "esc.txt", allow_symlinks=False)

    def test_secret_alias_still_denied_by_secrets_check(self, tmp_path):
        root = _project(tmp_path)
        (root / ".env").write_text("k=v", encoding="utf-8")
        os.symlink(root / ".env", root / "alias.txt")
        # حتى مع allow_symlinks=True فحص الأسرار على المحلول يرفض
        with pytest.raises(PermissionError, match="secret"):
            resolve_workspace_path(root, "alias.txt", allow_symlinks=True)


# ═══════════════ حارس بنيوي: لا ابتلاع صامت (NF-14) ═══════════════

class TestNoSilentSwallow:

    def test_no_bare_except_exception_pass_in_policy(self):
        src = POLICY_SRC.read_text(encoding="utf-8")
        # لا يجوز عودة النمط except Exception يليه pass في هذا الملف
        assert not re.search(
            r"except\s+Exception\s*:\s*\n\s*pass", src), (
            "عاد نمط الابتلاع الصامت except Exception: pass — NF-14/NF-28")
