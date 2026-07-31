# -*- coding: utf-8 -*-
"""TSK-728a — اختبارات HookRunner (core/hooks.py) بعقد «تشديد-فقط».

نقاط العقد المحروسة:
1. غياب قسم ``hooks:`` ⇒ runner فارغ ⇒ صفر subprocess ⇒ سلوك اليوم.
2. ``pre_command``: فشل/مهلة/خروج ≠0 ⇒ **حجب** (fail-closed).
3. ``post_write`` / ``post_run``: الفشل تحذير فقط — لا حجب.
4. لا قناة إضعاف: HookRunner لا يملك أي واجهة موافقة.
"""
from __future__ import annotations

import sys

import pytest

from core.hooks import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    HookRunner,
    HookSpec,
    _parse_specs,
)

PY = sys.executable

# أوامر خطّافات حقيقية صغيرة (subprocess فعلي — لا mocks للسلوك الجوهري)
HOOK_PASS = f'{PY} -c "import sys; sys.exit(0)"'
HOOK_FAIL = f'{PY} -c "import sys; sys.exit(3)"'
HOOK_SLEEP = f'{PY} -c "import time; time.sleep(30)"'
HOOK_ECHO_ENV = (
    f'{PY} -c "import os,sys; '
    f"sys.exit(0 if os.environ.get('HOOK_EVENT') else 7)\""
)


class TestFromConfig:
    """البناء من config — التسامح مع الشكل، الصرامة في التشغيل."""

    def test_missing_section_yields_empty_runner(self):
        runner = HookRunner.from_config({"model": "x"})
        assert runner.is_empty

    def test_none_and_non_dict_config_yield_empty(self):
        assert HookRunner.from_config(None).is_empty
        assert HookRunner.from_config("garbage").is_empty
        assert HookRunner.from_config({"hooks": "not-a-dict"}).is_empty

    def test_unknown_event_keys_ignored(self):
        runner = HookRunner.from_config(
            {"hooks": {"on_boot": [{"command": HOOK_PASS}]}}
        )
        assert runner.is_empty, "حدث غير معروف يجب أن يُتجاهَل"

    def test_valid_section_parsed(self):
        runner = HookRunner.from_config(
            {"hooks": {"pre_command": [{"command": HOOK_PASS, "timeout": 5}]}}
        )
        assert not runner.is_empty
        assert runner.hooks["pre_command"][0].timeout == 5.0

    def test_malformed_entries_dropped(self):
        specs = _parse_specs([
            "just-a-string",          # ليس dict
            {"timeout": 5},            # بلا command
            {"command": "   "},        # command فارغ
            {"command": HOOK_PASS, "timeout": "abc"},   # timeout فاسد
            {"command": HOOK_PASS, "timeout": -1},      # timeout سالب
        ])
        assert len(specs) == 2
        assert all(s.timeout == DEFAULT_TIMEOUT_SECONDS for s in specs)

    def test_timeout_capped_at_max(self):
        specs = _parse_specs([{"command": HOOK_PASS, "timeout": 9999}])
        assert specs[0].timeout == MAX_TIMEOUT_SECONDS


class TestPreCommandFailClosed:
    """العقد الأهم: pre_command يحجب عند أي شك."""

    def test_passing_hook_allows(self):
        runner = HookRunner(hooks={"pre_command": [HookSpec(HOOK_PASS)]})
        allowed, reason = runner.pre_command("echo hi")
        assert allowed and reason == ""

    def test_failing_hook_blocks(self):
        runner = HookRunner(hooks={"pre_command": [HookSpec(HOOK_FAIL)]})
        allowed, reason = runner.pre_command("echo hi")
        assert not allowed
        assert "حُجب" in reason and "fail-closed" in reason

    def test_timeout_blocks(self):
        runner = HookRunner(
            hooks={"pre_command": [HookSpec(HOOK_SLEEP, timeout=1.0)]}
        )
        allowed, reason = runner.pre_command("echo hi")
        assert not allowed
        assert "timeout" in reason

    def test_unlaunchable_hook_blocks(self):
        runner = HookRunner(
            hooks={"pre_command": [HookSpec("/no/such/binary_xyz")]}
        )
        allowed, _ = runner.pre_command("echo hi")
        assert not allowed, "فشل الإطلاق نفسه = fail-closed"

    def test_first_failure_short_circuits(self):
        runner = HookRunner(hooks={"pre_command": [
            HookSpec(HOOK_FAIL), HookSpec(HOOK_PASS),
        ]})
        allowed, _ = runner.pre_command("x")
        assert not allowed
        assert len(runner.audit) == 1, "الحجب يوقف السلسلة فورًا"

    def test_event_env_reaches_hook(self):
        runner = HookRunner(hooks={"pre_command": [HookSpec(HOOK_ECHO_ENV)]})
        allowed, _ = runner.pre_command("x")
        assert allowed, "HOOK_EVENT يجب أن يصل للخطّاف عبر البيئة"


class TestPostHooksWarnOnly:
    """post_write/post_run: الفعل وقع — الفشل تحذير لا حجب."""

    def test_post_write_failure_is_warning(self):
        runner = HookRunner(hooks={"post_write": [HookSpec(HOOK_FAIL)]})
        warnings = runner.post_write("src/app.py")
        assert len(warnings) == 1 and "⚠️" in warnings[0]

    def test_post_write_success_no_warnings(self):
        runner = HookRunner(hooks={"post_write": [HookSpec(HOOK_PASS)]})
        assert runner.post_write("src/app.py") == []

    def test_post_run_failure_is_warning_and_chain_continues(self):
        runner = HookRunner(hooks={"post_run": [
            HookSpec(HOOK_FAIL), HookSpec(HOOK_FAIL),
        ]})
        warnings = runner.post_run("pytest", exit_code=1)
        assert len(warnings) == 2, "post_* لا يقطع السلسلة"

    def test_empty_runner_zero_subprocess(self, monkeypatch):
        import core.hooks as hooks_mod

        def _boom(*a, **k):  # pragma: no cover - يفشل الاختبار إن نودي
            raise AssertionError("subprocess استُدعي رغم runner فارغ")

        monkeypatch.setattr(hooks_mod.subprocess, "run", _boom)
        runner = HookRunner.from_config({})
        assert runner.pre_command("x") == (True, "")
        assert runner.post_write("f") == []
        assert runner.post_run("c", 0) == []


class TestTightenOnlyContract:
    """لا قناة إضعاف بالبناء."""

    def test_no_approval_surface(self):
        surface = [n for n in dir(HookRunner) if "approv" in n.lower()]
        assert surface == [], "HookRunner يجب ألا يملك أي واجهة موافقة"

    def test_audit_records_every_execution(self):
        runner = HookRunner(hooks={
            "pre_command": [HookSpec(HOOK_PASS)],
            "post_run": [HookSpec(HOOK_FAIL)],
        })
        runner.pre_command("a")
        runner.post_run("b", 0)
        assert len(runner.audit) == 2
        assert runner.audit[0].ok and not runner.audit[1].ok

    def test_pre_command_result_is_bool_reason_tuple(self):
        allowed, reason = HookRunner().pre_command("x")
        assert isinstance(allowed, bool) and isinstance(reason, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
