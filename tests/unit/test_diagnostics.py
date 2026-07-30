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
