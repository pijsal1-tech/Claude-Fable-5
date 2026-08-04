# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  اختبارات core/provider_keys — TSK-735a (القرار 7 / D-20)

  العقود المُثبَتة:
  1. round-trip قراءة: ملف سليم ⇒ الخريطة كاملة + key_for يصيب.
  2. fail-closed على كل عطب: غياب/JSON معطوب/جذر ليس dict/
     keys ليست dict ⇒ {} بلا استثناء.
  3. إسقاط صامت للإدخال المعطوب: القيم غير النصية/الفارغة تُسقَط
     والإدخالات السليمة تبقى.
  4. قراءة طازجة: تعديل الملف بين استدعاءين يظهر فورًا (لا cache).
  5. denylist: `provider_keys.json` محجوب في path_policy
     (is_secret_file) — أدوات الوكيل وSafeReader لا تقرآنه.
═══════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import pathlib

from core.provider_keys import (
    KEYS_FILENAME,
    KEYS_VERSION,
    key_for,
    keys_path,
    read_provider_keys,
)


def _write(tmp_path, payload) -> pathlib.Path:
    p = tmp_path / KEYS_FILENAME
    if isinstance(payload, str):
        p.write_text(payload, encoding="utf-8")
    else:
        p.write_text(json.dumps(payload, ensure_ascii=False),
                     encoding="utf-8")
    return p


# ═══ 1) round-trip ═══════════════════════════════════════════════

class TestReadRoundTrip:
    def test_valid_file_full_map(self, tmp_path):
        _write(tmp_path, {"version": KEYS_VERSION,
                          "keys": {"my_openai": "sk-TEST-abc",
                                   "local_llm": "token-xyz"}})
        assert read_provider_keys(tmp_path) == {
            "my_openai": "sk-TEST-abc", "local_llm": "token-xyz"}

    def test_key_for_hit_and_miss(self, tmp_path):
        _write(tmp_path, {"version": 1, "keys": {"gem": "AIza-FAKE"}})
        assert key_for(tmp_path, "gem") == "AIza-FAKE"
        assert key_for(tmp_path, "ghost") is None

    def test_keys_path_is_beside_config(self, tmp_path):
        assert keys_path(tmp_path) == tmp_path / KEYS_FILENAME
        # يقبل str أيضًا (server يمرر _DIR كـ str أحيانًا)
        assert keys_path(str(tmp_path)) == tmp_path / KEYS_FILENAME

    def test_version_field_not_required_for_read(self, tmp_path):
        # القارئ متسامح مع غياب version — الشكل الرسمي يتضمنها لكن
        # القراءة fail-open على الحقول الوصفية (لا على الأنواع).
        _write(tmp_path, {"keys": {"p": "k"}})
        assert read_provider_keys(tmp_path) == {"p": "k"}


# ═══ 2) fail-closed على كل عطب ═══════════════════════════════════

class TestFailClosed:
    def test_missing_file_empty(self, tmp_path):
        assert read_provider_keys(tmp_path) == {}
        assert key_for(tmp_path, "any") is None

    def test_broken_json_empty(self, tmp_path):
        _write(tmp_path, "{ not json ][")
        assert read_provider_keys(tmp_path) == {}

    def test_root_not_dict_empty(self, tmp_path):
        for payload in (["list"], "string", 42, None, True):
            _write(tmp_path, payload)
            assert read_provider_keys(tmp_path) == {}, repr(payload)

    def test_keys_not_dict_empty(self, tmp_path):
        for keys in (["a"], "sk-x", 7, None):
            _write(tmp_path, {"version": 1, "keys": keys})
            assert read_provider_keys(tmp_path) == {}, repr(keys)

    def test_keys_field_absent_empty(self, tmp_path):
        _write(tmp_path, {"version": 1})
        assert read_provider_keys(tmp_path) == {}

    def test_directory_instead_of_file_empty(self, tmp_path):
        (tmp_path / KEYS_FILENAME).mkdir()
        assert read_provider_keys(tmp_path) == {}


# ═══ 3) إسقاط صامت للإدخال المعطوب ═══════════════════════════════

class TestBadEntryDropped:
    def test_non_string_values_dropped_good_kept(self, tmp_path):
        _write(tmp_path, {"version": 1, "keys": {
            "good": "sk-ok",
            "num": 123,
            "none": None,
            "listy": ["sk"],
            "empty": "",
            "blank": "   ",
        }})
        assert read_provider_keys(tmp_path) == {"good": "sk-ok"}

    def test_non_string_or_blank_ids_dropped(self, tmp_path):
        p = tmp_path / KEYS_FILENAME
        # مفتاح فارغ/أبيض في JSON (المفاتيح دائمًا نصوص في JSON —
        # نختبر الفراغ والبياض)
        p.write_text('{"keys": {"": "k1", "  ": "k2", "ok": "k3"}}',
                     encoding="utf-8")
        assert read_provider_keys(tmp_path) == {"ok": "k3"}


# ═══ 4) قراءة طازجة — لا cache ═══════════════════════════════════

class TestFreshRead:
    def test_edit_between_reads_is_visible(self, tmp_path):
        _write(tmp_path, {"keys": {"p": "old-key"}})
        assert key_for(tmp_path, "p") == "old-key"
        _write(tmp_path, {"keys": {"p": "new-key"}})
        assert key_for(tmp_path, "p") == "new-key"

    def test_delete_between_reads_is_visible(self, tmp_path):
        _write(tmp_path, {"keys": {"p": "k"}})
        assert read_provider_keys(tmp_path) == {"p": "k"}
        (tmp_path / KEYS_FILENAME).unlink()
        assert read_provider_keys(tmp_path) == {}


# ═══ 5) denylist — الملف محجوب عن أدوات الوكيل ═══════════════════

class TestSecretDenylist:
    def test_filename_is_secret(self):
        from chain.path_policy import is_secret_file
        assert is_secret_file(pathlib.Path(KEYS_FILENAME)) is True

    def test_filename_in_denylist_constant(self):
        from chain.path_policy import SECRETS_DENYLIST_NAMES
        assert KEYS_FILENAME in SECRETS_DENYLIST_NAMES

    def test_evasion_variants_blocked(self):
        # التطبيع (TSK-CEV-117) يغطي الاسم الجديد تلقائيًا
        from chain.path_policy import is_secret_file
        for evasion in (f"{KEYS_FILENAME} ", f"{KEYS_FILENAME}.",
                        f"{KEYS_FILENAME}\u200b",
                        f"{KEYS_FILENAME}::$DATA"):
            assert is_secret_file(pathlib.Path(evasion)) is True, evasion

    def test_similar_legitimate_names_not_blocked(self):
        from chain.path_policy import is_secret_file
        for name in ("provider_keys_doc.md", "providers.json",
                     "provider_keys.py"):
            assert is_secret_file(pathlib.Path(name)) is False, name
