# -*- coding: utf-8 -*-
"""TSK-731b (BATCH-P3/D-11) — عقد GET /api/update-check.

معايير القبول (DEVELOPMENT_TASKS §BATCH-P3 / TSK-731):
- **معطَّلة افتراضيًا**: config بلا قسم updates أو check_enabled ليست
  True حرفيًا أو manifest_url فارغة ⇒ {ok, enabled: false} مع **صفر لمس
  شبكة** (حارس: requests.get مُرقَّع ليرمي — يجب ألا يُلمَس).
- مفعَّلة + manifest سليم ⇒ {enabled, current, latest,
  update_available, url}.
- فشل الفحص (شبكة/JSON/schema) ⇒ صامت: latest=null،
  update_available=false — لا 5xx.
- **تطهير**: manifest_url لا تُردَّد في الاستجابة (قد تحمل tokens).
- config.yaml: مثال updates يبقى معلَّقًا (الافتراضي بلا فحص —
  نمط حارس hooks/728c).
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import server  # noqa: E402
from core.version import __version__  # noqa: E402


def _get(monkeypatch, cfg):
    monkeypatch.setattr(server, "_load_config", lambda: cfg, raising=False)
    client = server.app.test_client()
    resp = client.get("/api/update-check")
    assert resp.status_code == 200
    return resp.get_json()


def _forbid_network(monkeypatch):
    """يرقّع requests.get ليرمي — أي لمس شبكة يفشل الاختبار."""
    import requests

    def _boom(*a, **kw):                       # pragma: no cover
        raise AssertionError("network touched on disabled path")

    monkeypatch.setattr(requests, "get", _boom)


class TestDisabledByDefault:
    """المسار الافتراضي: معطَّل ⇒ صفر شبكة (IR-1)."""

    @pytest.mark.parametrize("cfg", [
        {},                                            # لا قسم updates
        None,                                          # config فارغ
        {"updates": {}},                               # قسم فارغ
        {"updates": {"check_enabled": False,
                     "manifest_url": "https://x.y/m.json"}},
        {"updates": {"check_enabled": "true",          # نص لا bool
                     "manifest_url": "https://x.y/m.json"}},
        {"updates": {"check_enabled": True}},          # بلا url
        {"updates": {"check_enabled": True, "manifest_url": ""}},
        {"updates": {"check_enabled": True, "manifest_url": "   "}},
        {"updates": "not-a-dict"},                     # قسم معطوب
    ])
    def test_disabled_zero_network(self, monkeypatch, cfg):
        _forbid_network(monkeypatch)
        data = _get(monkeypatch, cfg)
        assert data == {"ok": True, "enabled": False}


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class TestEnabledPath:
    """مفعَّلة صراحةً — الفحص يمر عبر core.update_check."""

    CFG = {"updates": {"check_enabled": True,
                       "manifest_url": "https://x.y/manifest.json"}}

    def _patch_manifest(self, monkeypatch, resp):
        import requests
        monkeypatch.setattr(requests, "get", lambda *a, **kw: resp)

    def test_update_available(self, monkeypatch):
        self._patch_manifest(monkeypatch, _FakeResponse(
            200, {"latest": "99.0.0", "url": "https://x.y/dl"}))
        data = _get(monkeypatch, self.CFG)
        assert data["ok"] is True and data["enabled"] is True
        assert data["current"] == __version__
        assert data["latest"] == "99.0.0"
        assert data["update_available"] is True
        assert data["url"] == "https://x.y/dl"

    def test_already_latest(self, monkeypatch):
        self._patch_manifest(monkeypatch, _FakeResponse(
            200, {"latest": __version__, "url": "https://x.y/dl"}))
        data = _get(monkeypatch, self.CFG)
        assert data["update_available"] is False
        assert data["latest"] == __version__

    def test_network_failure_silent(self, monkeypatch):
        import requests

        def _fail(*a, **kw):
            raise requests.RequestException("boom")

        monkeypatch.setattr(requests, "get", _fail)
        data = _get(monkeypatch, self.CFG)
        assert data == {"ok": True, "enabled": True,
                        "current": __version__, "latest": None,
                        "update_available": False, "url": ""}

    @pytest.mark.parametrize("resp", [
        _FakeResponse(404, {}),
        _FakeResponse(200, ValueError("bad json")),
        _FakeResponse(200, ["not", "a", "dict"]),
        _FakeResponse(200, {"latest": "not-a-version"}),
    ])
    def test_bad_manifest_silent(self, monkeypatch, resp):
        self._patch_manifest(monkeypatch, resp)
        data = _get(monkeypatch, self.CFG)
        assert data["ok"] is True and data["enabled"] is True
        assert data["latest"] is None
        assert data["update_available"] is False

    def test_manifest_url_not_echoed(self, monkeypatch):
        """التطهير: manifest_url (قد تحمل token) لا تظهر في الاستجابة."""
        secret_url = "https://x.y/manifest.json?token=SECRET-QS"
        cfg = {"updates": {"check_enabled": True,
                           "manifest_url": secret_url}}
        self._patch_manifest(monkeypatch, _FakeResponse(
            200, {"latest": "99.0.0", "url": "https://x.y/dl"}))
        data = _get(monkeypatch, cfg)
        raw = json.dumps(data, ensure_ascii=False)
        assert "SECRET-QS" not in raw
        assert "manifest.json" not in raw


class TestConfigExampleCommented:
    """نمط حارس 728c: مثال config.yaml يبقى معلَّقًا."""

    def test_updates_not_active_in_config(self):
        import yaml
        cfg = yaml.safe_load(
            (ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
        assert "updates" not in cfg, \
            "مثال updates يجب أن يبقى معلَّقًا — الافتراضي بلا فحص تحديث"

    def test_example_text_present(self):
        text = (ROOT / "config.yaml").read_text(encoding="utf-8")
        assert "# updates:" in text
        assert "check_enabled" in text
