# -*- coding: utf-8 -*-
"""TSK-734a (D-19-6): وحدة permissions_overrides النقية.

عقود مثبتة (من المواصفة):
1. round-trip: write ثم read يعيد نفس المحتوى.
2. fail-closed على كل عطب: غياب/JSON مكسور/ليس dict/مفتاح غريب/
   نوع خاطئ ⇒ read يعيد {} بلا رفع.
3. write يرفض المحتوى غير المسموح بلا لمس القرص (صفر تغيير حالة).
4. overrides فارغ = حذف الملف (عودة نظيفة).
5. apply_to_config: دمج بلا تحوير للمدخلات؛ الأسبقية للمفتاحين
   المسموحين حصرًا؛ overrides غير صالح ⇒ نسخة config كما هي.
"""
from __future__ import annotations

import json

import pytest

from core.permissions_overrides import (
    ALLOWED_KEYS, OVERRIDES_FILENAME, apply_to_config, overrides_path,
    read_overrides, validate_overrides, write_overrides,
)


VALID = {
    "force_command_approval": True,
    "agent.command_allowlist": {"test": "pytest -q", "lint": "ruff ."},
}


# ═══════════ round-trip ═══════════

def test_write_then_read_round_trip(tmp_path):
    assert write_overrides(tmp_path, VALID) is True
    assert read_overrides(tmp_path) == VALID
    # الملف JSON صالح على القرص (شكل {version, overrides})
    data = json.loads(overrides_path(tmp_path).read_text("utf-8"))
    assert data["overrides"] == VALID


def test_single_key_round_trip(tmp_path):
    assert write_overrides(tmp_path, {"force_command_approval": False})
    assert read_overrides(tmp_path) == {"force_command_approval": False}


# ═══════════ fail-closed عند القراءة ═══════════

def test_read_missing_file_returns_empty(tmp_path):
    assert read_overrides(tmp_path) == {}


def test_read_broken_json_returns_empty(tmp_path):
    overrides_path(tmp_path).write_text("{broken", encoding="utf-8")
    assert read_overrides(tmp_path) == {}


def test_read_non_dict_payload_returns_empty(tmp_path):
    overrides_path(tmp_path).write_text('["list"]', encoding="utf-8")
    assert read_overrides(tmp_path) == {}


def test_read_unknown_key_rejects_whole_file(tmp_path):
    # fail-closed: مفتاح غريب واحد يرفض الملف كله — لا قبول جزئي
    payload = {"version": 1, "overrides": {
        "force_command_approval": True,
        "auto_execute": True,        # غير مسموح
    }}
    overrides_path(tmp_path).write_text(
        json.dumps(payload), encoding="utf-8")
    assert read_overrides(tmp_path) == {}


def test_read_wrong_type_rejects_whole_file(tmp_path):
    payload = {"version": 1, "overrides": {
        "force_command_approval": "yes",   # ليس bool
    }}
    overrides_path(tmp_path).write_text(
        json.dumps(payload), encoding="utf-8")
    assert read_overrides(tmp_path) == {}


def test_read_bad_allowlist_entries_rejects(tmp_path):
    payload = {"version": 1, "overrides": {
        "agent.command_allowlist": {"test": "   "},   # قيمة فارغة
    }}
    overrides_path(tmp_path).write_text(
        json.dumps(payload), encoding="utf-8")
    assert read_overrides(tmp_path) == {}


# ═══════════ write: تحقق صارم + مسح ═══════════

def test_write_rejects_unknown_key_without_touching_disk(tmp_path):
    assert write_overrides(tmp_path, {"auto_execute": True}) is False
    assert not overrides_path(tmp_path).exists()


def test_write_rejects_non_bool_force(tmp_path):
    assert write_overrides(
        tmp_path, {"force_command_approval": 1}) is False
    assert not overrides_path(tmp_path).exists()


def test_write_rejects_bad_allowlist(tmp_path):
    for bad in ({"t": ""}, {"": "x"}, {"t": 5}, ["t"], "str"):
        assert write_overrides(
            tmp_path, {"agent.command_allowlist": bad}) is False
    assert not overrides_path(tmp_path).exists()


def test_write_rejects_non_dict(tmp_path):
    assert write_overrides(tmp_path, None) is False       # type: ignore
    assert write_overrides(tmp_path, ["x"]) is False      # type: ignore


def test_write_empty_deletes_file(tmp_path):
    write_overrides(tmp_path, VALID)
    assert overrides_path(tmp_path).exists()
    assert write_overrides(tmp_path, {}) is True
    assert not overrides_path(tmp_path).exists()
    assert read_overrides(tmp_path) == {}


def test_write_empty_when_no_file_is_ok(tmp_path):
    assert write_overrides(tmp_path, {}) is True


def test_write_invalid_keeps_previous_content(tmp_path):
    # صفر تغيير حالة: الرفض لا يمس المحتوى السابق الصالح
    write_overrides(tmp_path, VALID)
    assert write_overrides(tmp_path, {"bogus": 1}) is False
    assert read_overrides(tmp_path) == VALID


# ═══════════ apply_to_config ═══════════

def test_apply_overrides_take_precedence():
    cfg = {"force_command_approval": False,
           "agent": {"command_allowlist": {"old": "old cmd"},
                     "command_timeout_seconds": 30},
           "language": "mix"}
    merged = apply_to_config(cfg, VALID)
    assert merged["force_command_approval"] is True
    assert merged["agent"]["command_allowlist"] == VALID[
        "agent.command_allowlist"]
    # باقي config يمر كما هو (بما فيه مفاتيح agent الأخرى)
    assert merged["agent"]["command_timeout_seconds"] == 30
    assert merged["language"] == "mix"


def test_apply_does_not_mutate_inputs():
    cfg = {"agent": {"command_allowlist": {"old": "old cmd"}}}
    ov = dict(VALID)
    merged = apply_to_config(cfg, ov)
    assert cfg["agent"]["command_allowlist"] == {"old": "old cmd"}
    assert ov == VALID
    merged["agent"]["command_allowlist"]["new"] = "x"
    assert "new" not in VALID["agent.command_allowlist"]


def test_apply_empty_or_invalid_overrides_is_identity_copy():
    cfg = {"force_command_approval": False, "language": "ar"}
    for ov in ({}, {"bogus": 1}, None):
        merged = apply_to_config(cfg, ov)   # type: ignore[arg-type]
        assert merged == cfg
        assert merged is not cfg            # نسخة لا مرجع


def test_apply_allowlist_only_leaves_force_untouched():
    cfg = {"force_command_approval": False}
    merged = apply_to_config(
        cfg, {"agent.command_allowlist": {"t": "pytest"}})
    assert merged["force_command_approval"] is False
    assert merged["agent"]["command_allowlist"] == {"t": "pytest"}


def test_apply_handles_non_dict_agent_section():
    # agent قسم معطوب في config ⇒ الدمج يبني قسمًا نظيفًا (لا انفجار)
    cfg = {"agent": "broken"}
    merged = apply_to_config(
        cfg, {"agent.command_allowlist": {"t": "pytest"}})
    assert merged["agent"] == {"command_allowlist": {"t": "pytest"}}


# ═══════════ validate_overrides (العقد المباشر) ═══════════

def test_validate_contract():
    assert validate_overrides({}) is True
    assert validate_overrides(VALID) is True
    assert validate_overrides({"force_command_approval": True}) is True
    assert validate_overrides("nope") is False
    assert validate_overrides({"x": 1}) is False
    # bool ليس قيمة allowlist صالحة (isinstance(True, str) == False)
    assert validate_overrides(
        {"agent.command_allowlist": {"k": True}}) is False


def test_allowed_keys_frozen():
    # التجميد: توسيع السطح قرار واعٍ يكسر هنا أولًا
    assert ALLOWED_KEYS == frozenset(
        {"force_command_approval", "agent.command_allowlist"})
    assert OVERRIDES_FILENAME == "permissions_overrides.json"
