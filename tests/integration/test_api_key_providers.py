# -*- coding: utf-8 -*-
"""TSK-735c (القرار 7 من تسلسل D-19 / قيد D-20) — توصيل مزودي API-key.

معايير القبول المثبَّتة (مواصفة TSK-735 في DEVELOPMENT_TASKS):
  1. إدخال معرَّف في ``providers.api_providers`` يظهر في /api/models
     براية ``key_configured`` الصحيحة (true بمفتاح جانبي، false بدونه).
  2. **بلا قسم ⇒ صفر تغيير سلوك**: /api/models مطابق للقائمة الساكنة.
  3. switch-model لمزود api_providers ينجح بمفتاح مزروع (قراءة طازجة
     من الملف الجانبي)؛ وبلا مفتاح ⇒ 400 برسالة إرشادية.
  4. **اختبار العقد الشامل — عدم-الترديد (V3 §0 قيد 6)**: المفتاح
     الكناري المزروع لا يظهر في /api/models ولا /api/settings ولا
     استجابة switch-model (نجاحًا أو فشلًا).
  5. الشكل المعطوب في api_providers (إدخال بلا id/base_url) يُسقَط
     صامتًا — لا أعطال.
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import server  # noqa: E402
from core.provider_keys import KEYS_FILENAME  # noqa: E402

SECRET = "sk-CANARY-735c-never-echoed"

CONFIG_WITH_PROVIDERS = """\
# تعليق عربي — بيئة اختبار TSK-735c
force_command_approval: true
providers:
  api_providers:
    - id: "my_openai"
      name: "OpenAI (مفتاحي)"
      base_url: "https://api.example.test/v1"
      models: ["gpt-4o", "gpt-4o-mini"]
    - id: "no_key_provider"
      name: "بلا مفتاح"
      base_url: "http://localhost:11434/v1"
      models: ["qwen2.5-coder"]
    - id: ""
      base_url: "http://broken.invalid"
    - id: "no_url_provider"
"""

CONFIG_WITHOUT_SECTION = """\
force_command_approval: true
providers:
  use_ai:
    model: "gateway-claude-sonnet-5"
"""


@pytest.fixture()
def env(monkeypatch, tmp_path):
    """بيئة معزولة: config في tmp + مفتاح جانبي لمزود واحد فقط."""
    (tmp_path / "config.yaml").write_text(CONFIG_WITH_PROVIDERS,
                                          encoding="utf-8")
    (tmp_path / KEYS_FILENAME).write_text(
        json.dumps({"version": 1, "keys": {"my_openai": SECRET}}),
        encoding="utf-8")
    monkeypatch.setattr(server, "_DIR", tmp_path)
    monkeypatch.setattr(server, "_workspace_trusted", lambda: True)
    return tmp_path


@pytest.fixture()
def env_no_section(monkeypatch, tmp_path):
    (tmp_path / "config.yaml").write_text(CONFIG_WITHOUT_SECTION,
                                          encoding="utf-8")
    monkeypatch.setattr(server, "_DIR", tmp_path)
    monkeypatch.setattr(server, "_workspace_trusted", lambda: True)
    return tmp_path


def _client():
    return server.app.test_client()


def _models(c):
    r = c.get("/api/models")
    assert r.status_code == 200
    return r.get_json()


# ═════════════ 1. الظهور في /api/models براية صحيحة ═════════════

class TestModelsListing:
    def test_configured_providers_appear_with_flags(self, env):
        with _client() as c:
            data = _models(c)
        by_id = {p["id"]: p for p in data["providers"]}
        assert "my_openai" in by_id
        assert by_id["my_openai"]["key_configured"] is True
        assert by_id["my_openai"]["models"] == ["gpt-4o", "gpt-4o-mini"]
        assert by_id["my_openai"]["name"] == "🔑 OpenAI (مفتاحي)"
        assert "no_key_provider" in by_id
        assert by_id["no_key_provider"]["key_configured"] is False

    def test_malformed_entries_dropped_silently(self, env):
        with _client() as c:
            ids = {p["id"] for p in _models(c)["providers"]}
        assert "" not in ids
        assert "no_url_provider" not in ids

    def test_static_providers_still_present(self, env):
        with _client() as c:
            ids = {p["id"] for p in _models(c)["providers"]}
        # القائمة الساكنة لم تُمس — إلحاق لا استبدال
        for static_id in ("genspark", "deepseek", "use_ai", "blackbox"):
            assert static_id in ids


# ═════════════ 2. بلا قسم = صفر تغيير سلوك ═══════════════════════

class TestOptIn:
    def test_no_section_list_is_static_only(self, env_no_section):
        with _client() as c:
            providers = _models(c)["providers"]
        assert all("key_configured" not in p for p in providers)
        ids = {p["id"] for p in providers}
        assert "my_openai" not in ids

    def test_missing_keys_file_no_crash(self, monkeypatch, tmp_path):
        (tmp_path / "config.yaml").write_text(CONFIG_WITH_PROVIDERS,
                                              encoding="utf-8")
        monkeypatch.setattr(server, "_DIR", tmp_path)
        with _client() as c:
            by_id = {p["id"]: p for p in _models(c)["providers"]}
        assert by_id["my_openai"]["key_configured"] is False


# ═════════════ 3. switch-model — الفرع العام ═════════════════════

class TestSwitchModel:
    def test_switch_succeeds_with_key(self, env):
        with _client() as c:
            r = c.post("/api/switch-model",
                       json={"provider": "my_openai", "model": "gpt-4o"})
        assert r.status_code == 200
        body = r.get_json()
        assert body["ok"] is True
        assert body["provider"] == "my_openai"

    def test_switch_rejected_without_key(self, env):
        with _client() as c:
            r = c.post("/api/switch-model",
                       json={"provider": "no_key_provider",
                             "model": "qwen2.5-coder"})
        assert r.status_code == 400
        assert "provider_keys.json" in r.get_json()["error"]

    def test_fresh_key_read_on_switch(self, env):
        """قراءة طازجة: إضافة المفتاح بعد الإقلاع تنفذ بلا إعادة تشغيل."""
        with _client() as c:
            r1 = c.post("/api/switch-model",
                        json={"provider": "no_key_provider",
                              "model": "qwen2.5-coder"})
            assert r1.status_code == 400
            (env / KEYS_FILENAME).write_text(
                json.dumps({"version": 1, "keys": {
                    "my_openai": SECRET,
                    "no_key_provider": "tok-added-later"}}),
                encoding="utf-8")
            r2 = c.post("/api/switch-model",
                        json={"provider": "no_key_provider",
                              "model": "qwen2.5-coder"})
            assert r2.status_code == 200

    def test_unknown_provider_still_400(self, env):
        with _client() as c:
            r = c.post("/api/switch-model",
                       json={"provider": "ghost", "model": "x"})
        assert r.status_code == 400


# ═════════════ 4. عقد عدم-الترديد الشامل (V3 §0 قيد 6) ═══════════

class TestKeyNeverEchoed:
    def test_key_absent_from_all_responses(self, env):
        with _client() as c:
            responses = [
                c.get("/api/models").get_data(as_text=True),
                c.get("/api/settings").get_data(as_text=True),
                c.post("/api/switch-model",
                       json={"provider": "my_openai",
                             "model": "gpt-4o"}).get_data(as_text=True),
                c.post("/api/switch-model",
                       json={"provider": "no_key_provider",
                             "model": "q"}).get_data(as_text=True),
            ]
        for body in responses:
            assert SECRET not in body

    def test_settings_still_excludes_providers_section(self, env):
        """سابقة TSK-722a تبقى: قسم providers مستبعد كليًا من settings."""
        with _client() as c:
            data = c.get("/api/settings").get_json()
        assert "providers" not in json.dumps(data)
        assert "api.example.test" not in json.dumps(data)
