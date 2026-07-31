# -*- coding: utf-8 -*-
"""TSK-728b — اختبارات عقد حقن pre_command في CommandRunner + توصيل server.

المحروس:
1. hook_runner=None (الافتراضي) ⇒ سلوك اليوم حرفيًا — لا نداء للخطّافات.
2. hook فاشل ⇒ الأمر محجوب **قبل** أي فحص موافقة (fail-closed).
3. hook ناجح ⇒ الأمر يمضي لمساره الطبيعي (الموافقات كما هي — تشديد-فقط).
4. الحجب يسبق الفحوص: حتى أمر «آمن» يُحجب لو الـ hook رفضه.
5. server.py يبني الخطّافات من config.yaml عبر _hook_runner() المُكاش
   ويوصّلها في موضعَي بناء CommandRunner (المصنع + main).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from actions.command_runner import CommandRunner
from core.hooks import HookRunner, HookSpec

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable

HOOK_PASS = f'{PY} -c "import sys; sys.exit(0)"'
HOOK_FAIL = f'{PY} -c "import sys; sys.exit(3)"'


class _SpyRunner(HookRunner):
    """جاسوس يسجّل النداءات دون تغيير العقد."""

    def __init__(self, allow: bool):
        super().__init__(hooks={})
        self.allow = allow
        self.calls: list[str] = []

    def pre_command(self, command: str):
        self.calls.append(command)
        if self.allow:
            return True, ""
        return False, "⛔ حُجب الأمر بواسطة hook (تشديد-فقط، fail-closed): spy"


class TestDefaultBehaviorUnchanged:
    def test_none_hook_runner_is_default(self, tmp_path):
        runner = CommandRunner(cwd=str(tmp_path))
        assert runner.hook_runner is None, "الافتراضي None = سلوك اليوم"

    def test_safe_command_runs_without_hooks(self, tmp_path):
        runner = CommandRunner(cwd=str(tmp_path), auto_approve=True)
        result = runner.run(f"{PY} --version", need_approval=False)
        assert result["success"]


class TestPreCommandInjection:
    def test_failing_hook_blocks_before_execution(self, tmp_path):
        spy = _SpyRunner(allow=False)
        runner = CommandRunner(cwd=str(tmp_path), auto_approve=True,
                               hook_runner=spy)
        result = runner.run("echo hi", need_approval=False)
        assert not result["success"]
        assert "حُجب" in result["error"]
        assert spy.calls == ["echo hi"]

    def test_passing_hook_allows_execution(self, tmp_path):
        spy = _SpyRunner(allow=True)
        runner = CommandRunner(cwd=str(tmp_path), auto_approve=True,
                               hook_runner=spy)
        result = runner.run(f"{PY} --version", need_approval=False)
        assert result["success"]
        assert len(spy.calls) == 1

    def test_real_failing_hook_blocks_even_safe_command(self, tmp_path):
        """حتى الأمر «الآمن» يُحجب — الـ hook يضيف صرامة فوق كل الطبقات."""
        hooks = HookRunner(hooks={"pre_command": [HookSpec(HOOK_FAIL)]})
        runner = CommandRunner(cwd=str(tmp_path), auto_approve=True,
                               hook_runner=hooks)
        result = runner.run("echo hi", need_approval=False)
        assert not result["success"]
        assert "fail-closed" in result["error"]

    def test_real_passing_hook_transparent(self, tmp_path):
        hooks = HookRunner(hooks={"pre_command": [HookSpec(HOOK_PASS)]})
        runner = CommandRunner(cwd=str(tmp_path), auto_approve=True,
                               hook_runner=hooks)
        result = runner.run(f"{PY} --version", need_approval=False)
        assert result["success"]

    def test_hook_cannot_weaken_dangerous_gate(self, tmp_path, monkeypatch):
        """hook ناجح لا يمنح موافقة: الأمر الخطير ما زال يسأل المستخدم.

        نرفض عبر _ask_approval الموهوم — لو الـ hook استطاع الإضعاف
        لنُفِّذ الأمر رغم الرفض.
        """
        hooks = HookRunner(hooks={"pre_command": [HookSpec(HOOK_PASS)]})
        runner = CommandRunner(cwd=str(tmp_path), auto_approve=False,
                               hook_runner=hooks)
        monkeypatch.setattr(runner, "_ask_approval", lambda c: False)
        result = runner.run("rm something", need_approval=True)
        assert not result["success"]
        assert "رفض المستخدم" in result["error"], \
            "hook ناجح يجب ألا يتجاوز بوابة الموافقة"


class TestPostHooks728c:
    """728c: post_run في CommandRunner + post_write عبر درز T-049."""

    def test_post_run_called_with_exit_code(self, tmp_path):
        calls = []

        class _PostSpy(HookRunner):
            def post_run(self, command, exit_code):
                calls.append((command, exit_code))
                return []

        runner = CommandRunner(cwd=str(tmp_path), auto_approve=True,
                               hook_runner=_PostSpy(hooks={}))
        result = runner.run(f"{PY} --version", need_approval=False)
        assert result["success"]
        assert len(calls) == 1 and calls[0][1] == 0

    def test_post_run_failure_does_not_change_result(self, tmp_path):
        hooks = HookRunner(hooks={"post_run": [HookSpec(HOOK_FAIL)]})
        runner = CommandRunner(cwd=str(tmp_path), auto_approve=True,
                               hook_runner=hooks)
        result = runner.run(f"{PY} --version", need_approval=False)
        assert result["success"], "فشل post_run تحذير فقط — لا يغيّر النتيجة"

    def test_post_write_via_t049_seam(self, tmp_path):
        from actions.file_manager import FileManager
        fm = FileManager(str(tmp_path))
        seen = []
        fm.add_write_hook(lambda rel: seen.append(rel))
        fm.write_file("a.txt", "hello")
        assert seen == ["a.txt"]

    def test_server_registers_post_write_hook(self):
        src = (ROOT / "server.py").read_text(encoding="utf-8")
        assert "def _post_write_hook" in src
        assert src.count("fm.add_write_hook(_post_write_hook)") == 2, \
            "موضعا بناء FileManager (المصنع + main) يجب أن يسجّلا post_write"

    def test_config_example_is_commented_out(self):
        cfg = (ROOT / "config.yaml").read_text(encoding="utf-8")
        import yaml
        parsed = yaml.safe_load(cfg) or {}
        assert "hooks" not in parsed, \
            "مثال config.yaml يجب أن يبقى معلَّقًا — الافتراضي بلا خطّافات"


class TestServerWiring:
    """التوصيل في server.py — فحص بنيوي (بلا إقلاع Flask)."""

    SRC = (ROOT / "server.py").read_text(encoding="utf-8")

    def test_helper_exists_and_lazy(self):
        assert "def _hook_runner()" in self.SRC
        assert "HookRunner.from_config(_load_config())" in self.SRC

    def test_both_construction_sites_wired(self):
        assert self.SRC.count("hook_runner=_hook_runner()") == 2, \
            "موضعا بناء CommandRunner (المصنع + main) يجب أن يوصّلا الخطّافات"

    def test_helper_builds_empty_runner_without_config_section(self):
        import importlib
        import core.hooks as hooks_mod
        importlib.reload(hooks_mod)
        runner = hooks_mod.HookRunner.from_config({"model": "x"})
        assert runner.is_empty


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
