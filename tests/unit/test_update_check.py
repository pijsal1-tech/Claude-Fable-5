# -*- coding: utf-8 -*-
"""TSK-731a (BATCH-P3) — عقد فحص التحديث اليدوي: مقارنة + جلب صامت-الفشل.

معايير القبول (DEVELOPMENT_TASKS §TSK-731):
- عقد compare_versions: rc/final/أقدم/أحدث/مساوٍ/نص فاسد ⇒ None.
- فشل الشبكة/schema ⇒ None صامت — لا استثناء يتسرب أبدًا.
- صفر استيراد وقت-تحميل لـ requests (نمط T-109).
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.update_check import (  # noqa: E402
    UpdateInfo,
    check_for_update,
    compare_versions,
    parse_version,
)


class TestParseVersion:
    @pytest.mark.parametrize("text,expected_none", [
        ("1.0.0", False), ("1.0.0-rc.1", False), ("10.20.30", False),
        ("1.0", True), ("1.0.0-beta.1", True), ("v1.0.0", True),
        ("", True), ("garbage", True), ("1.0.0-rc.", True),
    ])
    def test_accepts_and_rejects(self, text, expected_none):
        assert (parse_version(text) is None) is expected_none

    def test_non_string_is_none(self):
        assert parse_version(None) is None  # type: ignore[arg-type]

    def test_whitespace_tolerated(self):
        assert parse_version("  1.0.0 ") is not None


class TestCompareVersions:
    @pytest.mark.parametrize("a,b,expected", [
        ("1.0.0", "1.0.0", 0),
        ("1.0.0-rc.1", "1.0.0-rc.1", 0),
        ("1.0.0-rc.1", "1.0.0", -1),        # النهائي أحدث من rc
        ("1.0.0", "1.0.0-rc.9", 1),
        ("1.0.0-rc.1", "1.0.0-rc.2", -1),   # rc أعلى رقمًا أحدث
        ("1.0.0", "1.0.1", -1),
        ("1.1.0", "1.0.9", 1),
        ("2.0.0", "1.9.9", 1),
    ])
    def test_ordering(self, a, b, expected):
        assert compare_versions(a, b) == expected

    def test_invalid_side_yields_none(self):
        assert compare_versions("bad", "1.0.0") is None
        assert compare_versions("1.0.0", "bad") is None


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, raise_json=False):
        self.status_code = status_code
        self._payload = payload
        self._raise_json = raise_json

    def json(self):
        if self._raise_json:
            raise ValueError("not json")
        return self._payload


class TestCheckForUpdate:
    def _patch_get(self, monkeypatch, response=None, exc=None):
        import requests

        def _fake_get(url, timeout):
            if exc is not None:
                raise exc
            return response

        monkeypatch.setattr(requests, "get", _fake_get)

    def test_update_available(self, monkeypatch):
        self._patch_get(monkeypatch, _FakeResponse(
            payload={"latest": "1.0.1", "url": "https://example/dl"}))
        info = check_for_update("https://example/manifest", "1.0.0-rc.1")
        assert info == UpdateInfo(current="1.0.0-rc.1", latest="1.0.1",
                                  update_available=True,
                                  url="https://example/dl")

    def test_already_latest(self, monkeypatch):
        self._patch_get(monkeypatch, _FakeResponse(
            payload={"latest": "1.0.0-rc.1"}))
        info = check_for_update("https://example/m", "1.0.0-rc.1")
        assert info is not None and info.update_available is False
        assert info.url == ""

    def test_network_failure_silent_none(self, monkeypatch):
        self._patch_get(monkeypatch, exc=OSError("net down"))
        assert check_for_update("https://example/m", "1.0.0-rc.1") is None

    def test_non_200_silent_none(self, monkeypatch):
        self._patch_get(monkeypatch, _FakeResponse(status_code=404))
        assert check_for_update("https://example/m", "1.0.0-rc.1") is None

    def test_bad_json_silent_none(self, monkeypatch):
        self._patch_get(monkeypatch, _FakeResponse(raise_json=True))
        assert check_for_update("https://example/m", "1.0.0-rc.1") is None

    def test_bad_schema_silent_none(self, monkeypatch):
        self._patch_get(monkeypatch, _FakeResponse(payload=["not", "dict"]))
        assert check_for_update("https://example/m", "1.0.0-rc.1") is None
        self._patch_get(monkeypatch, _FakeResponse(payload={"latest": "??"}))
        assert check_for_update("https://example/m", "1.0.0-rc.1") is None

    def test_empty_url_or_bad_current_no_network(self, monkeypatch):
        """URL فارغ أو إصدار حالي فاسد ⇒ None قبل أي لمس للشبكة."""
        import requests

        def _boom(*a, **k):
            raise AssertionError("network touched")

        monkeypatch.setattr(requests, "get", _boom)
        assert check_for_update("", "1.0.0") is None
        assert check_for_update("https://example/m", "garbage") is None


class TestLazyImportContract:
    def test_no_toplevel_requests_import(self):
        """نمط T-109: صفر import requests أعلى الوحدة (بنيوي)."""
        src = (ROOT / "core" / "update_check.py").read_text(encoding="utf-8")
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import requests", "from requests")):
                # مسموح فقط داخل دالة (مسافة بادئة)
                assert line != stripped, f"استيراد أعلى الوحدة: {line}"

    def test_importing_module_does_not_load_requests(self):
        """تشغيلي (subprocess معزول): استيراد الوحدة لا يحمّل requests."""
        code = ("import sys; import core.update_check; "
                "sys.exit(1 if 'requests' in sys.modules else 0)")
        proc = subprocess.run([sys.executable, "-c", code],
                              cwd=ROOT, capture_output=True)
        assert proc.returncode == 0, proc.stderr.decode()
