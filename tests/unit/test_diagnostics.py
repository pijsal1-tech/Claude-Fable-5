# -*- coding: utf-8 -*-
"""TSK-721 (P1-2 / D-9) — عقد /api/diagnostics: المفاتيح + عدم-التسريب.

معايير القبول (DEVELOPMENT_TASKS §BATCH-P1 / TSK-721):
- المفاتيح موجودة: version/platform/dependencies/project_name/provider/
  metrics_summary.
- **فحص عدم-تسريب**: لا نمط sk-/ghp_/api_key/token في الحصيلة كاملة،
  ولا مسار مطلق (المشروع يظهر بالاسم فقط).
- تطهير المزود: مفاتيح get_info الوصفية فقط تمر — أي مفتاح غريب
  (url/key) يُسقط.
- فشل المقاييس لا يُفشل التشخيص (metrics_summary=None).
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import server  # noqa: E402
from core.version import __version__  # noqa: E402


class _FakeFM:
    root = pathlib.Path("/tmp/secret-parent-dir/my-project")

    def scan_project(self):
        return {"total_files": 0, "total_size_kb": 0}


class _LeakyProvider:
    """get_info يعيد مفاتيح وصفية + تسريبات مقصودة — التطهير يجب أن يسقطها."""

    def get_info(self):
        return {
            "name": "fake", "description": "d", "model": "m",
            "available": True, "initialized": True,
            "api_key": "sk-LEAKED-SECRET",          # يجب ألا يمر
            "base_url": "https://x.y/?token=ghp_LEAK",  # يجب ألا يمر
        }


def _get(monkeypatch, provider=None, metrics=None):
    monkeypatch.setattr(server, "fm", _FakeFM(), raising=False)
    monkeypatch.setattr(server, "provider", provider, raising=False)
    monkeypatch.setattr(server, "run_metrics_store", metrics, raising=False)
    client = server.app.test_client()
    resp = client.get("/api/diagnostics")
    assert resp.status_code == 200
    return resp.get_json()


def test_contract_keys_present(monkeypatch):
    data = _get(monkeypatch)
    assert data["ok"] is True
    d = data["diagnostics"]
    for key in ("version", "platform", "dependencies", "project_name",
                "provider", "metrics_summary"):
        assert key in d, f"مفتاح عقد غائب: {key}"
    assert d["version"] == __version__
    assert d["platform"]["system"]
    assert d["dependencies"]["flask"] is True
    assert d["project_name"] == "my-project"


def test_no_secret_patterns_in_payload(monkeypatch):
    data = _get(monkeypatch, provider=_LeakyProvider())
    raw = json.dumps(data, ensure_ascii=False)
    for pattern in ("sk-", "ghp_", "api_key", "token", "base_url"):
        assert pattern not in raw, f"تسريب نمط سري: {pattern}"


def test_no_absolute_paths_in_payload(monkeypatch):
    data = _get(monkeypatch)
    raw = json.dumps(data, ensure_ascii=False)
    assert "/tmp/secret-parent-dir" not in raw   # الاسم فقط — لا المسار
    assert data["diagnostics"]["project_name"] == "my-project"


def test_provider_sanitized_to_descriptive_keys_only(monkeypatch):
    data = _get(monkeypatch, provider=_LeakyProvider())
    prov = data["diagnostics"]["provider"]
    assert set(prov) == {"name", "description", "model",
                         "available", "initialized"}


def test_metrics_failure_does_not_fail_diagnostics(monkeypatch):
    class _BrokenMetrics:
        def summary(self):
            raise RuntimeError("boom")

    data = _get(monkeypatch, metrics=_BrokenMetrics())
    assert data["ok"] is True
    assert data["diagnostics"]["metrics_summary"] is None


def test_no_provider_yields_empty_dict(monkeypatch):
    data = _get(monkeypatch, provider=None)
    assert data["diagnostics"]["provider"] == {}


# ═══════════════ TSK-730a (BATCH-P3): مفتاح plugins ═══════════════
# glass-box: المُحمَّلون/المحجورون يظهرون في حزمة التشخيص —
# أسماء/مراحل/أسباب فقط (عقد التطهير TSK-721 يبقى صامدًا).

class _FakePluginRegistry:
    """سجل مزيف بنفس سطح StrategyPluginRegistry المستهلَك (loaded/quarantined)."""

    def __init__(self, loaded=None, quarantined=None):
        self._loaded = dict(loaded or {})
        self._quarantined = list(quarantined or [])

    @property
    def loaded(self):
        return dict(self._loaded)

    @property
    def quarantined(self):
        return list(self._quarantined)


class _FakeQuarantine:
    def __init__(self, name, stage, reason):
        self.name, self.stage, self.reason = name, stage, reason

    def to_dict(self):
        return {"name": self.name, "stage": self.stage,
                "reason": self.reason}


def _get_with_registry(monkeypatch, registry):
    monkeypatch.setattr(server, "plugin_registry", registry, raising=False)
    return _get(monkeypatch)


def test_plugins_key_present_and_empty_when_no_registry(monkeypatch):
    """registry=None (قبل الإقلاع/في الاختبارات) ⇒ قوائم فارغة — لا كسر عقد."""
    data = _get_with_registry(monkeypatch, None)
    assert data["diagnostics"]["plugins"] == {
        "loaded": [], "quarantined": []}


def test_plugins_loaded_and_quarantined_exposed(monkeypatch):
    reg = _FakePluginRegistry(
        loaded={"zeta": object, "alpha": object},
        quarantined=[_FakeQuarantine("bad_one", "dry_run",
                                     "build returned None")])
    data = _get_with_registry(monkeypatch, reg)
    plugins = data["diagnostics"]["plugins"]
    assert plugins["loaded"] == ["alpha", "zeta"]        # مفروزة
    assert plugins["quarantined"] == [
        {"name": "bad_one", "stage": "dry_run",
         "reason": "build returned None"}]


def test_plugins_no_secret_or_path_leak(monkeypatch):
    """عقد التطهير: حتى مع سجل حي، الحصيلة كاملة بلا أنماط سرية/مسارات."""
    reg = _FakePluginRegistry(
        loaded={"demo_echo": object},
        quarantined=[_FakeQuarantine("broken", "import",
                                     "ImportError: no module named x")])
    data = _get_with_registry(monkeypatch, reg)
    raw = json.dumps(data, ensure_ascii=False)
    for pattern in ("sk-", "ghp_", "api_key", "base_url",
                    "/tmp/secret-parent-dir"):
        assert pattern not in raw, f"تسريب: {pattern}"


def test_plugins_registry_failure_does_not_fail_diagnostics(monkeypatch):
    """سجل ينفجر عند القراءة ⇒ قوائم فارغة — التشخيص لا يفشل أبدًا."""
    class _Broken:
        @property
        def loaded(self):
            raise RuntimeError("boom")

        @property
        def quarantined(self):
            raise RuntimeError("boom")

    data = _get_with_registry(monkeypatch, _Broken())
    assert data["ok"] is True
    assert data["diagnostics"]["plugins"] == {
        "loaded": [], "quarantined": []}
