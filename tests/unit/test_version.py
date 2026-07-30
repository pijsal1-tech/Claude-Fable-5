# -*- coding: utf-8 -*-
"""TSK-716 (P0-4 / دفعة D-8) — رقم الإصدار القانوني.

الضمانات المثبَّتة:
1. core/version.py هو المصدر الوحيد: ثابت SemVer صالح.
2. server.APP_VERSION يعكسه حرفيًا (import واحد — لا نسخ).
3. /api/info يعرض المفتاح ``version`` بنفس القيمة (إضافة مفتاح فقط —
   المفاتيح القائمة ok/project/provider/history_length لم تُمس؛
   تجميد السطح في test_rest_blueprints يبقى الحكم).
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.version import __version__  # noqa: E402
import server  # noqa: E402

# SemVer 2.0.0 (مبسّط: MAJOR.MINOR.PATCH مع pre-release اختياري).
_SEMVER = re.compile(
    r"^\d+\.\d+\.\d+(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$")


def test_version_is_valid_semver():
    assert _SEMVER.match(__version__), (
        f"رقم الإصدار ليس SemVer صالحًا: {__version__!r}")


def test_server_reexports_same_version():
    assert server.APP_VERSION == __version__


def test_api_info_exposes_version(monkeypatch):
    """المفتاح version في /api/info = الثابت القانوني؛ المفاتيح القائمة سليمة."""
    class _FakeScan(dict):
        pass

    class _FakeFM:
        root = pathlib.Path("/tmp/fake-project")

        def scan_project(self):
            return {"total_files": 0, "total_size_kb": 0}

    monkeypatch.setattr(server, "fm", _FakeFM(), raising=False)
    monkeypatch.setattr(server, "provider", None, raising=False)

    client = server.app.test_client()
    resp = client.get("/api/info")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["version"] == __version__
    # المفاتيح القائمة لم تُمس (إضافة مفتاح فقط):
    for key in ("ok", "project", "provider", "history_length"):
        assert key in data, f"مفتاح قائم اختفى: {key}"
