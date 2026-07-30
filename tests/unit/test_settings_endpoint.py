# -*- coding: utf-8 -*-
"""TSK-722a (P1-4 / D-9) — عقد /api/settings: whitelist + عدم-التسريب.

معايير القبول (DEVELOPMENT_TASKS §BATCH-P1 / TSK-722a):
1. المفاتيح المسموحة تظهر بقيم config الحية.
2. **عدم-تسريب**: config مزروع بقسم providers يحوي api_key ⇒ لا
   sk-/api_key/providers في الاستجابة كاملة.
3. لا مسارات مطلقة: project_root مضبوط ⇒ فقط project_root_set=true؛
   retention.pinned تظهر كعدد فقط.
4. config فارغ/معطوب ⇒ استجابة سليمة بالقيم الفعالة الافتراضية
   (force_command_approval.effective=True fail-closed — D-1/TSK-617).
5. GET فقط (POST ⇒ 405) — لا مسار كتابة.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import server  # noqa: E402


_LEAKY_CFG = {
    "default_provider": "use_ai",
    "language": "mix",
    "auto_execute": False,
    "backup_before_edit": True,
    "max_context_files": 15,
    "force_command_approval": False,
    "project_root": "/tmp/secret-parent-dir/my-project",   # يجب ألا يمر
    "agent": {
        "command_allowlist": {"test": "pytest -q"},
        "command_timeout_seconds": 60,
        "command_output_max_chars": 8000,
        "internal_note": "should-not-pass",                # غير معلوم — يُسقط
    },
    "context_budget": {"model_window": 128000,
                       "reserved_output": 8000, "safety_margin": 0.10},
    "history": {"payload_last_n": 40},
    "context": {"semantic": {"enabled": True,
                             "timeout_seconds": 2.0, "top_k": 3}},
    "session_binding": {"warn_only": True, "policy": "warn"},
    "retention": {"max_count": None, "max_age_days": None,
                  "dry_run": True,
                  "pinned": ["/tmp/secret-parent-dir/sess1"]},  # عدد فقط
    "planner": "heuristic",
    "backend": "memory",
    "dispatch": "in-proc",
    "execution": {"stale_ttl_seconds": 900},
    "routing": {"direct_max": 2.0, "version": 1},
    # قسم مُستبعد كليًا — التسريبات المزروعة يجب ألا تظهر:
    "providers": {
        "use_ai": {"api_key": "sk-LEAKED-SECRET",
                   "base_url": "https://x.y/?token=ghp_LEAK"},
    },
}


def _get(monkeypatch, cfg):
    monkeypatch.setattr(server, "_load_config", lambda: cfg, raising=False)
    client = server.app.test_client()
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    return resp.get_json()


def test_whitelisted_values_pass_through(monkeypatch):
    data = _get(monkeypatch, _LEAKY_CFG)
    assert data["ok"] is True
    s = data["settings"]
    assert s["default_provider"] == "use_ai"
    assert s["language"] == "mix"
    assert s["auto_execute"] is False
    assert s["backup_before_edit"] is True
    assert s["max_context_files"] == 15
    assert s["planner"] == "heuristic"
    assert s["backend"] == "memory"
    assert s["dispatch"] == "in-proc"
    assert s["agent"]["command_allowlist"] == {"test": "pytest -q"}
    assert s["agent"]["command_timeout_seconds"] == 60
    assert "internal_note" not in s["agent"]        # مفتاح غير معلوم يُسقط
    assert s["context_budget"]["model_window"] == 128000
    assert s["history"]["payload_last_n"] == 40
    assert s["context_semantic"] == {"enabled": True,
                                     "timeout_seconds": 2.0, "top_k": 3}
    assert s["session_binding"] == {"warn_only": True, "policy": "warn"}
    assert s["execution"] == {"stale_ttl_seconds": 900}
    assert s["routing"]["direct_max"] == 2.0


def test_no_secret_patterns_in_payload(monkeypatch):
    data = _get(monkeypatch, _LEAKY_CFG)
    raw = json.dumps(data, ensure_ascii=False)
    for pattern in ("sk-", "ghp_", "api_key", "base_url", "providers"):
        assert pattern not in raw, f"تسريب نمط سري: {pattern}"


def test_no_absolute_paths_project_root_flag_only(monkeypatch):
    data = _get(monkeypatch, _LEAKY_CFG)
    raw = json.dumps(data, ensure_ascii=False)
    assert "/tmp/secret-parent-dir" not in raw          # لا مسار مطلق
    s = data["settings"]
    assert s["project_root_set"] is True                # راية فقط
    assert "project_root" not in s
    assert s["retention"]["pinned_count"] == 1          # عدد لا قائمة
    assert "pinned" not in s["retention"]


def test_force_approval_effective_and_explicit_flag(monkeypatch):
    # صريح false في config ⇒ effective=False + explicit=True
    data = _get(monkeypatch, _LEAKY_CFG)
    fca = data["settings"]["force_command_approval"]
    assert fca == {"effective": False, "explicit_in_config": True}


def test_empty_config_yields_failclosed_defaults(monkeypatch):
    # config فارغ (قراءة متعذرة ⇒ {}) — الاستجابة سليمة والقيم الفعالة
    data = _get(monkeypatch, {})
    s = data["settings"]
    assert s["default_provider"] is None
    assert s["agent"] is None
    assert s["retention"] is None
    assert s["context_semantic"] is None
    assert s["project_root_set"] is False
    # D-1/TSK-617: الغياب ⇒ إلزام الموافقة (fail-closed)
    assert s["force_command_approval"] == {"effective": True,
                                           "explicit_in_config": False}


def test_get_only_no_write_path(monkeypatch):
    monkeypatch.setattr(server, "_load_config", lambda: {}, raising=False)
    client = server.app.test_client()
    assert client.post("/api/settings").status_code == 405
    assert client.put("/api/settings").status_code == 405
