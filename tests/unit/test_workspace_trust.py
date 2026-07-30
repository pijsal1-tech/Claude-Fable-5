# -*- coding: utf-8 -*-
"""TSK-725a (P2-3 / D-10) — وحدة تخزين Workspace Trust.

يتحقق آليًا من (معايير القبول — DEVELOPMENT_TASKS §TSK-725/725a):
  1. **fail-closed**: ملف معدوم / JSON معطوب / قيمة غير bool / جذر
     غير موجود ⇒ is_trusted=False **بلا استثناء أبدًا**.
  2. دورة القرار: set_trust(True) ⇒ موثوق؛ set_trust(False) ⇒ غير
     موثوق؛ السجل {version, trusted, decided_at, decided_by} كامل.
  3. الذرية (NF-19): tmp+os.replace — لا يبقى ملف tmp بعد النجاح؛
     فشل الكتابة (جذر للقراءة فقط) ⇒ False بلا رفع.
  4. الموقع: <root>/.ai_runs/trust.json (داخل IGNORED_DIRS).
"""

from __future__ import annotations

import json
import os
import stat

import pytest

from core import workspace_trust as wt


class TestFailClosed:
    def test_missing_file_untrusted(self, tmp_path):
        assert wt.is_trusted(tmp_path) is False
        assert wt.read_trust_record(tmp_path) is None

    def test_nonexistent_root_untrusted_no_raise(self, tmp_path):
        assert wt.is_trusted(tmp_path / "no-such-dir") is False

    def test_corrupt_json_untrusted(self, tmp_path):
        p = wt.trust_path(tmp_path)
        p.parent.mkdir(parents=True)
        p.write_text("{broken json", encoding="utf-8")
        assert wt.is_trusted(tmp_path) is False

    @pytest.mark.parametrize("payload", [
        [],                          # ليس dict
        {},                          # بلا مفتاح
        {"trusted": 1},              # int ليس bool (صرامة isinstance)
        {"trusted": "true"},         # سلسلة
        {"trusted": None},
    ])
    def test_non_bool_values_untrusted(self, tmp_path, payload):
        p = wt.trust_path(tmp_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload), encoding="utf-8")
        assert wt.is_trusted(tmp_path) is False

    def test_explicit_false_untrusted(self, tmp_path):
        assert wt.set_trust(tmp_path, False) is True
        assert wt.is_trusted(tmp_path) is False
        # لكن السجل موجود وصحيح (قرار صريح — يميز عن الغياب)
        rec = wt.read_trust_record(tmp_path)
        assert rec is not None and rec["trusted"] is False


class TestDecisionCycle:
    def test_set_then_read_trusted(self, tmp_path):
        assert wt.set_trust(tmp_path, True) is True
        assert wt.is_trusted(tmp_path) is True

    def test_record_shape(self, tmp_path):
        wt.set_trust(tmp_path, True, decided_by="user")
        rec = json.loads(wt.trust_path(tmp_path).read_text(encoding="utf-8"))
        assert rec["version"] == wt.TRUST_VERSION
        assert rec["trusted"] is True
        assert rec["decided_by"] == "user"
        # ISO-8601 UTC
        assert "T" in rec["decided_at"] and (
            rec["decided_at"].endswith("+00:00") or rec["decided_at"].endswith("Z"))

    def test_revoke_trust(self, tmp_path):
        wt.set_trust(tmp_path, True)
        assert wt.is_trusted(tmp_path) is True
        wt.set_trust(tmp_path, False)
        assert wt.is_trusted(tmp_path) is False

    def test_overwrite_replaces_atomically(self, tmp_path):
        wt.set_trust(tmp_path, True)
        wt.set_trust(tmp_path, True)
        # لا يبقى ملف tmp بعد النجاح (os.replace استهلكه)
        leftovers = [f for f in os.listdir(wt.trust_path(tmp_path).parent)
                     if f.endswith(".tmp")]
        assert leftovers == []


class TestAtomicityAndLocation:
    def test_path_inside_ai_runs(self, tmp_path):
        p = wt.trust_path(tmp_path)
        assert p.parent.name == ".ai_runs"
        assert p.name == "trust.json"
        # داخل IGNORED_DIRS فعلًا (لا يظهر في الفهرس/البحث)
        from core.ignore_rules import IGNORED_DIRS
        assert ".ai_runs" in IGNORED_DIRS

    @pytest.mark.skipif(os.name == "nt", reason="صلاحيات POSIX")
    def test_write_failure_returns_false_no_raise(self, tmp_path):
        if os.geteuid() == 0:
            pytest.skip("root يتجاوز صلاحيات الملفات")
        ro = tmp_path / "ro-root"
        ro.mkdir()
        os.chmod(ro, stat.S_IRUSR | stat.S_IXUSR)  # لا كتابة
        try:
            assert wt.set_trust(ro, True) is False
            assert wt.is_trusted(ro) is False
        finally:
            os.chmod(ro, stat.S_IRWXU)

    def test_set_trust_creates_ai_runs_dir(self, tmp_path):
        assert not (tmp_path / ".ai_runs").exists()
        assert wt.set_trust(tmp_path, True) is True
        assert (tmp_path / ".ai_runs").is_dir()
