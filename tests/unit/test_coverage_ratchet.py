# -*- coding: utf-8 -*-
"""اختبارات T-050 (R-703): بوابة التغطية التصاعدية + بنية CI.

معايير القبول المغطاة هنا:
- الـ ratchet **يمنع** انخفاض التغطية (verified once — الحالة المانعة
  مثبتة باختبار مباشر على القرار النقي وعلى الـ CLI بـ exit code 1).
- الأرضية increase-only: ``update`` لا يخفضها أبدًا.
- ملفات البنية موجودة وسليمة: workflow + baseline + .coveragerc.
"""
import json
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))
from coverage_ratchet import (  # noqa: E402
    next_baseline,
    ratchet,
    read_baseline,
    read_current,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
RATCHET = REPO_ROOT / "scripts" / "coverage_ratchet.py"


# ═══════════════════════ القرار النقي ═══════════════════════

class TestRatchetDecision:
    def test_below_baseline_fails(self):
        """معيار القبول: الـ ratchet يمنع PR يخفض التغطية."""
        ok, msg = ratchet(current=39.9, baseline=40.0)
        assert ok is False
        assert "FAIL" in msg and "39.9" in msg and "40.0" in msg

    def test_equal_baseline_passes(self):
        ok, _ = ratchet(current=40.0, baseline=40.0)
        assert ok is True

    def test_above_baseline_passes(self):
        ok, msg = ratchet(current=68.9, baseline=40.0)
        assert ok is True and "OK" in msg


class TestNextBaseline:
    def test_update_never_lowers(self):
        """increase-only: قياس أدنى لا يخفض الأرضية أبدًا."""
        assert next_baseline(current=35.0, baseline=40.0) == 40.0

    def test_update_raises_with_margin(self):
        assert next_baseline(current=68.9, baseline=40.0) == 68.4

    def test_update_noop_within_margin(self):
        assert next_baseline(current=40.3, baseline=40.0) == 40.0


# ═══════════════════════ CLI end-to-end ═══════════════════════

def _write_fixture(tmp_path, baseline: float, current: float):
    (tmp_path / "coverage_baseline.txt").write_text(f"{baseline}\n",
                                                    encoding="utf-8")
    (tmp_path / "coverage.json").write_text(
        json.dumps({"totals": {"percent_covered": current}}),
        encoding="utf-8")


class TestRatchetCLI:
    def _run(self, tmp_path, mode: str):
        """تشغيل الـ CLI بمسارات fixture عبر monkeypatch بيئي بسيط:
        ننسخ السكريبت منطقيًا بتمرير المسارات عبر cwd — السكريبت يقرأ
        مسارات ثابتة من جذر الريبو، فنختبر الـ CLI الحقيقي على fixture
        بحقن الموديول مباشرة بدل subprocess معقد."""
        import coverage_ratchet as cr
        old_b, old_c = cr.BASELINE_FILE, cr.COVERAGE_JSON
        cr.BASELINE_FILE = tmp_path / "coverage_baseline.txt"
        cr.COVERAGE_JSON = tmp_path / "coverage.json"
        try:
            return cr.main(["coverage_ratchet.py", mode])
        finally:
            cr.BASELINE_FILE, cr.COVERAGE_JSON = old_b, old_c

    def test_check_exit_1_on_regression(self, tmp_path):
        """معيار القبول (verified once): بوابة CI تفشل على خفض تغطية."""
        _write_fixture(tmp_path, baseline=40.0, current=38.0)
        assert self._run(tmp_path, "check") == 1

    def test_check_exit_0_on_green(self, tmp_path):
        _write_fixture(tmp_path, baseline=40.0, current=41.0)
        assert self._run(tmp_path, "check") == 0

    def test_update_writes_higher_baseline(self, tmp_path):
        _write_fixture(tmp_path, baseline=40.0, current=68.9)
        assert self._run(tmp_path, "update") == 0
        assert float((tmp_path / "coverage_baseline.txt")
                     .read_text().strip()) == 68.4

    def test_update_never_writes_lower(self, tmp_path):
        _write_fixture(tmp_path, baseline=40.0, current=30.0)
        assert self._run(tmp_path, "update") == 0
        assert float((tmp_path / "coverage_baseline.txt")
                     .read_text().strip()) == 40.0

    def test_bad_mode_exit_2(self, tmp_path):
        _write_fixture(tmp_path, baseline=40.0, current=50.0)
        assert self._run(tmp_path, "bogus") == 2


# ═══════════════════════ بنية CI ═══════════════════════

class TestCIWiring:
    def test_workflow_exists_and_has_gates(self):
        wf = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8")
        assert "scripts/check.sh" in wf                 # البوابات البنيوية
        assert "coverage_ratchet.py check" in wf        # بوابة الـ ratchet
        assert "--cov-report=json" in wf                # مصدر القياس

    def test_baseline_file_tracked_and_valid(self):
        baseline = read_baseline(REPO_ROOT / "coverage_baseline.txt")
        assert baseline >= 40.0                         # مواصفة R-703

    def test_coveragerc_omits_non_production(self):
        rc = (REPO_ROOT / ".coveragerc").read_text(encoding="utf-8")
        assert "tests/*" in rc and "scripts/*" in rc

    def test_canary_fixtures_load(self):
        """R-703 Required Tests: canary يثبت أن الـ fixtures تُحمَّل."""
        fixture = REPO_ROOT / "tests" / "fixtures" / "sample_project"
        assert fixture.is_dir()
        assert any(fixture.iterdir())

    def test_read_current_parses_coverage_json(self, tmp_path):
        p = tmp_path / "coverage.json"
        p.write_text(json.dumps({"totals": {"percent_covered": 55.5}}),
                     encoding="utf-8")
        assert read_current(p) == 55.5
