# -*- coding: utf-8 -*-
"""اختبارات T-051 (R-703): توحيد المزود الافتراضي — config يفوز.

معايير القبول المغطاة:
- تغيير config.default_provider يغيّر مزود الإقلاع observably (الحل
  النقي `_resolve_default_provider` هو نقطة القرار الوحيدة في main()).
- الـ hardcode القديم ``genspark:claude-sonnet-5`` مختفٍ (grep بنيوي).
- boot smoke: القرار يعمل مع config.yaml الحقيقي للريبو.
"""
import pathlib

import server
from server import _read_config, _resolve_default_provider

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


# ═══════════════════════ config يفوز ═══════════════════════

class TestConfigWins:
    def test_no_cli_uses_config_default_provider(self):
        """معيار القبول: تغيير config يغيّر مزود الإقلاع."""
        cfg = {"default_provider": "deepseek"}
        assert _resolve_default_provider(None, cfg) == ("deepseek", None)
        cfg = {"default_provider": "use_ai"}
        assert _resolve_default_provider(None, cfg) == ("use_ai", None)

    def test_config_provider_section_supplies_model(self):
        cfg = {"default_provider": "use_ai",
               "providers": {"use_ai": {"model": "gateway-claude-sonnet-5"}}}
        assert _resolve_default_provider(None, cfg) == (
            "use_ai", "gateway-claude-sonnet-5")

    def test_missing_section_model_falls_to_provider_class_default(self):
        """بلا موديل في config ⇒ None — صنف المزود يطبق افتراضيه الخاص
        (مصدر واحد للقيمة، لا نسخة ثانية في server.py)."""
        cfg = {"default_provider": "genspark", "providers": {}}
        assert _resolve_default_provider(None, cfg) == ("genspark", None)

    def test_empty_config_falls_back_to_use_ai(self):
        """ملاذ الإقلاع الأخير = مرآة قيمة config.yaml المشحونة."""
        assert _resolve_default_provider(None, {}) == ("use_ai", None)
        assert _resolve_default_provider(None, None) == ("use_ai", None)


class TestCLIPrecedence:
    def test_explicit_prov_colon_model_wins_over_config(self):
        cfg = {"default_provider": "use_ai"}
        assert _resolve_default_provider("genspark:claude-sonnet-5", cfg) == (
            "genspark", "claude-sonnet-5")

    def test_bare_model_goes_to_config_provider_not_hardcode(self):
        """الـ quirk القديم: موديل بلا مزود كان يذهب لـ genspark المضمّن.
        الآن يذهب لمزود config — التناقض الذي أزاله T-051."""
        cfg = {"default_provider": "deepseek"}
        assert _resolve_default_provider("some-model", cfg) == (
            "deepseek", "some-model")


# ═══════════════════════ boot smoke + بنية ═══════════════════════

class TestBootSmoke:
    def test_real_config_yaml_resolves(self):
        """config.yaml الحقيقي: default_provider=use_ai + موديل قسمه."""
        cfg = _read_config()
        prov_id, model_name = _resolve_default_provider(None, cfg)
        assert prov_id == cfg["default_provider"]
        # قسم providers.use_ai في config الحقيقي يحدد الموديل
        assert model_name == cfg["providers"][prov_id]["model"]

    def test_read_config_tolerant_of_missing_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(server, "_DIR", tmp_path)
        assert _read_config() == {}


class TestHardcodeGone:
    def test_no_hardcoded_default_in_server_code(self):
        """معيار القبول (grep): الـ hardcode مختفٍ من كود server.py."""
        src = (REPO_ROOT / "server.py").read_text(encoding="utf-8")
        code = "\n".join(ln for ln in src.splitlines()
                         if not ln.lstrip().startswith("#"))
        assert 'or "genspark:claude-sonnet-5"' not in code
        assert 'prov_id = "genspark"' not in code

    def test_main_delegates_to_resolver(self):
        src = (REPO_ROOT / "server.py").read_text(encoding="utf-8")
        assert "_resolve_default_provider(args.model, _read_config())" in src
