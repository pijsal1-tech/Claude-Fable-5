# -*- coding: utf-8 -*-
"""
QA-T08 (جزء TSK-203) — انحدار التوحيد: MAX_SMART_FILE_SIZE + قارئ config.
Validates: TSK-203 (NF-23(2)+(3)).

معيار القبول (grep): تعريف واحد للثابت؛ ≤1 موضع yaml.safe_load في
server.py. + سلوك القارئ الموحّد _load_config: مُكاش، تسامحي، متوافق
مع alias _read_config التاريخي. صفر نداءات AI خارجية.
"""
import pathlib
import re

import pytest

import server

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _server_src() -> str:
    return (REPO_ROOT / "server.py").read_text(encoding="utf-8")


def _code_lines(src: str) -> list[str]:
    """أسطر الكود فقط — التعليقات لا تُحتسب في grep-asserts."""
    return [ln for ln in src.splitlines()
            if not ln.lstrip().startswith("#")]


class TestGrepAsserts:
    """معايير القبول الحرفية لـ TSK-203 (بوابة QA-T08)."""

    def test_single_constant_definition(self):
        """تعريف واحد فقط لـ MAX_SMART_FILE_SIZE في server.py."""
        code = _code_lines(_server_src())
        defs = [ln for ln in code
                if re.match(r"\s*MAX_SMART_FILE_SIZE\s*=", ln)]
        assert len(defs) == 1, f"وجد {len(defs)} تعريفًا: {defs}"

    def test_at_most_one_yaml_safe_load(self):
        """≤1 موضع yaml.safe_load في كود server.py (داخل _load_config فقط)."""
        code = _code_lines(_server_src())
        hits = [ln for ln in code if "yaml.safe_load" in ln]
        assert len(hits) <= 1, f"وجد {len(hits)} موضعًا: {hits}"

    def test_no_direct_config_open_outside_loader(self):
        """لا فتح مباشر لـ config.yaml خارج _load_config."""
        src = _server_src()
        # اقتطاع جسم _load_config ثم فحص الباقي
        marker = "def _load_config()"
        assert marker in src
        idx = src.index(marker)
        # نهاية الدالة = أول def تالٍ
        rest_idx = src.index("\ndef ", idx + 1)
        outside = src[:idx] + src[rest_idx:]
        code = _code_lines(outside)
        opens = [ln for ln in code
                 if "open(" in ln and "config.yaml" in ln]
        assert opens == [], f"فتح مباشر خارج القارئ: {opens}"


class TestLoaderBehavior:
    """سلوك القارئ الموحّد _load_config."""

    def test_read_config_is_alias(self):
        """الاسم التاريخي _read_config = نفس الدالة (توافق خلفي)."""
        assert server._read_config is server._load_config

    def test_real_config_loads(self):
        cfg = server._load_config()
        assert isinstance(cfg, dict) and cfg  # config الحقيقي غير فارغ
        assert "default_provider" in cfg

    def test_cached_same_object(self):
        """مُكاش: نداءان يعيدان نفس الكائن (لا قراءة قرص ثانية)."""
        assert server._load_config() is server._load_config()

    def test_tolerant_of_missing_file(self, monkeypatch, tmp_path):
        """ملف مفقود → {} (لا استثناء — لا يمنع الإقلاع)."""
        monkeypatch.setattr(server, "_DIR", tmp_path)
        assert server._load_config() == {}

    def test_cache_keyed_by_path(self, monkeypatch, tmp_path):
        """الكاش بمفتاح المسار — monkeypatch لـ _DIR يُقرأ من مساره."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("marker_key: tsk203\n", encoding="utf-8")
        monkeypatch.setattr(server, "_DIR", tmp_path)
        assert server._load_config().get("marker_key") == "tsk203"

    def test_tolerant_of_broken_yaml(self, monkeypatch, tmp_path):
        """YAML مكسور → {} (التسامح محفوظ — الصخب في المحلّلات المتخصصة)."""
        (tmp_path / "config.yaml").write_text("{{ broken: [", encoding="utf-8")
        monkeypatch.setattr(server, "_DIR", tmp_path)
        assert server._load_config() == {}


class TestConsumersUnified:
    """المواضع الست القديمة تستهلك القارئ الموحّد الآن."""

    def test_session_binding_policy_uses_loader(self, monkeypatch):
        """_session_binding_policy يقرأ عبر _load_config."""
        monkeypatch.setattr(
            server, "_load_config",
            lambda: {"session_binding": {"warn_only": False,
                                         "policy": "block"}})
        assert server._session_binding_policy() == "block"

    def test_history_policy_uses_loader(self, monkeypatch):
        """_history_payload_policy (بلا cfg صريح) يقرأ عبر القارئ الموحّد."""
        monkeypatch.setattr(server, "_read_config",
                            lambda: {"history": {"payload_last_n": 7}})
        assert server._history_payload_policy().last_n == 7

    def test_main_reads_via_loader_source(self):
        """grep: مواضع main (auto_execute/planner/retention/routing/backend)
        كلها عبر _load_config — لا import yaml محلي متبقٍ فيها."""
        src = _server_src()
        code = "\n".join(_code_lines(src))
        # لا يبقى أي import yaml محلي داخل الدوال (المسموح: داخل _load_config)
        local_imports = code.count("import yaml as _yaml")
        assert local_imports <= 1, \
            f"بقي {local_imports} import yaml محلي — التوحيد ناقص"
