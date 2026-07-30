# -*- coding: utf-8 -*-
"""
بوابة TSK-502 — راية إلزام الموافقة force_command_approval (NF-16).

Accept:
- الراية مفعّلة ⇒ كل أمر (REST /api/run، /api/run-file، apply-actions)
  يمر ببوابة الموافقة إلزاميًا — حتى الآمن وحتى مع auto_approve.
- الافتراضي (false / config غائب) متوافق سلوكيًا: لا موافقة تفاعلية
  في هذه المسارات (need_approval=False كما قبل TSK-502).
- الأوامر الخطيرة تتطلب موافقة دائمًا في الحالتين (الراية توسّع
  البوابة ولا تضيّقها).

صفر نداءات AI خارجية؛ لا تنفيذ أوامر فعلي (approval مرفوض في
اختبارات الإلزام، وأوامر echo البسيطة في اختبارات التوافق).
"""
import pathlib

import pytest

import server
from actions.command_runner import CommandRunner

REPO = pathlib.Path(__file__).resolve().parents[2]


# ═══════════════ CommandRunner.run(force_approval=...) ═══════════════

class TestRunnerForceApproval:
    """السلوك الوحدوي للراية في CommandRunner.run."""

    def _runner(self, tmp_path, approve: bool):
        r = CommandRunner(cwd=str(tmp_path), auto_approve=True)
        r._approval_calls = []

        def _fake_ask(command):
            r._approval_calls.append(command)
            return approve
        r._ask_approval = _fake_ask
        return r

    def test_safe_command_gated_when_forced(self, tmp_path):
        """أمر آمن + auto_approve=True — الراية تجبره على البوابة."""
        r = self._runner(tmp_path, approve=False)
        result = r.run("echo hi", need_approval=False, force_approval=True)
        assert r._approval_calls == ["echo hi"]
        assert result["success"] is False
        assert result["error"] == "رفض المستخدم"

    def test_forced_and_approved_executes(self, tmp_path):
        """الموافقة عبر البوابة ⇒ التنفيذ يمضي طبيعيًا."""
        r = self._runner(tmp_path, approve=True)
        result = r.run("echo hi", need_approval=False, force_approval=True)
        assert r._approval_calls == ["echo hi"]
        assert result["success"] is True

    def test_default_no_gate_backward_compat(self, tmp_path):
        """الافتراضي (force_approval غائب) = صفر نداءات بوابة — توافق."""
        r = self._runner(tmp_path, approve=False)
        result = r.run("echo hi", need_approval=False)
        assert r._approval_calls == []
        assert result["success"] is True

    def test_dangerous_still_gated_without_flag(self, tmp_path):
        """أمر خطير يتطلب موافقة دائمًا حتى بلا الراية (لا تضييق)."""
        r = self._runner(tmp_path, approve=False)
        result = r.run("rm something", need_approval=False)
        assert r._approval_calls == ["rm something"]
        assert result["success"] is False


# ═══════════════ راية config في server ═══════════════

class TestConfigFlag:
    """_force_command_approval يقرأ config.yaml عبر القارئ الموحّد."""

    def test_flag_on(self, monkeypatch):
        monkeypatch.setattr(server, "_load_config",
                            lambda: {"force_command_approval": True})
        assert server._force_command_approval() is True

    def test_flag_off(self, monkeypatch):
        # TSK-725b: false الصريحة تُحترم **في مساحة موثوقة فقط** —
        # نثبّت الثقة هنا لاختبار عقد config التاريخي بمعزل.
        monkeypatch.setattr(server, "_workspace_trusted", lambda: True)
        monkeypatch.setattr(server, "_load_config",
                            lambda: {"force_command_approval": False})
        assert server._force_command_approval() is False

    def test_untrusted_workspace_forces_true_despite_explicit_false(
            self, monkeypatch):
        """TSK-725b (Workspace Trust): مساحة غير موثوقة ⇒ إلزام
        الموافقة حتى مع false صريحة في config (fail-closed يعلو)."""
        monkeypatch.setattr(server, "_workspace_trusted", lambda: False)
        monkeypatch.setattr(server, "_load_config",
                            lambda: {"force_command_approval": False})
        assert server._force_command_approval() is True

    def test_flag_absent_defaults_true(self, monkeypatch):
        """TSK-617 (قرار D-1): config بلا المفتاح ⇒ **True** —
        الافتراض البرمجي الآمن (fail-closed)؛ قبل TSK-617 كان False."""
        monkeypatch.setattr(server, "_load_config", lambda: {})
        assert server._force_command_approval() is True

    def test_repo_config_documents_flag_default_false(self):
        """config.yaml المشحون يوثّق الراية بقيمة **صريحة** false
        (تعطيل واعٍ لـ localhost — TSK-617 يحترم الصريح كما هو)."""
        import yaml
        cfg = yaml.safe_load((REPO / "config.yaml").read_text(encoding="utf-8"))
        assert "force_command_approval" in cfg
        assert cfg["force_command_approval"] is False


# ═══════════════ مسار REST /api/run كاملًا ═══════════════

class TestApiRunEndToEnd:
    """الراية مفعّلة ⇒ /api/run يمر بالبوابة؛ الافتراضي لا يمر."""

    @pytest.fixture
    def spy_runner(self, tmp_path, monkeypatch):
        r = CommandRunner(cwd=str(tmp_path), auto_approve=True)
        r._approval_calls = []

        def _fake_ask(command):
            r._approval_calls.append(command)
            return False
        r._ask_approval = _fake_ask
        monkeypatch.setattr(server, "cmd_runner", r)
        return r

    def test_forced_api_run_gated(self, spy_runner, monkeypatch):
        monkeypatch.setattr(server, "_load_config",
                            lambda: {"force_command_approval": True})
        client = server.app.test_client()
        resp = client.post("/api/run", json={"command": "echo hi"})
        data = resp.get_json()
        assert spy_runner._approval_calls == ["echo hi"]
        assert data["ok"] is False
        assert data["error"] == "رفض المستخدم"

    def test_flag_absent_api_run_gated(self, spy_runner, monkeypatch):
        """TSK-617 (قرار D-1): غياب المفتاح ⇒ البوابة تعمل (fail-closed)؛
        قبل TSK-617 كان الغياب = لا بوابة."""
        monkeypatch.setattr(server, "_load_config", lambda: {})
        client = server.app.test_client()
        resp = client.post("/api/run", json={"command": "echo hi"})
        data = resp.get_json()
        assert spy_runner._approval_calls == ["echo hi"]
        assert data["ok"] is False

    def test_explicit_false_api_run_not_gated(self, spy_runner, monkeypatch):
        """false صريح يُحترم — السلوك التاريخي (توافق config المشحون).
        TSK-725b: يتطلب الآن مساحة موثوقة (fail-closed يعلو دونها)."""
        monkeypatch.setattr(server, "_workspace_trusted", lambda: True)
        monkeypatch.setattr(server, "_load_config",
                            lambda: {"force_command_approval": False})
        client = server.app.test_client()
        resp = client.post("/api/run", json={"command": "echo hi"})
        data = resp.get_json()
        assert spy_runner._approval_calls == []
        assert data["ok"] is True


# ═══════════════ بنيوي: المواضع الثلاثة موصولة ═══════════════

class TestStructural:
    """كل مواضع need_approval=False (server.py + routes/run.py) تمرر الراية.

    TSK-613 (ADR-003): موضعا api_run/api_run_file انتقلا إلى
    routes/run.py — نفس الضمانة على الملفين معًا (الراية تُقرأ
    عبر _srv._force_command_approval() — نفس الدالة حرفيًا).
    """

    def test_all_need_approval_false_sites_pass_flag(self):
        src = (REPO / "server.py").read_text(encoding="utf-8") \
            + (REPO / "routes" / "run.py").read_text(encoding="utf-8")
        lines = src.splitlines()
        # مواضع النداء الفعلية فقط (سطر فيه .run( أو تكملة وسائطه) —
        # ذكر need_approval=False في docstring/تعليق ليس موضع تنفيذ.
        sites = [i for i, ln in enumerate(lines)
                 if "need_approval=False" in ln
                 and (".run(" in ln or ".run(" in lines[i - 1])]
        assert len(sites) == 3, \
            f"عدد مواضع need_approval=False تغيّر: {len(sites)}"
        for i in sites:
            window = "\n".join(lines[i:i + 3])
            assert "force_approval=_force_command_approval()" in window \
                or "force_approval=_srv._force_command_approval()" in window, \
                f"موضع L{i+1} لا يمرر راية force_command_approval:\n{window}"

    def test_readme_documents_deployment_limits(self):
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        assert "حدود النشر" in readme
        assert "force_command_approval" in readme
        assert "127.0.0.1" in readme
