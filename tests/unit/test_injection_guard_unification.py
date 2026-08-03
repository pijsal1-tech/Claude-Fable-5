# -*- coding: utf-8 -*-
"""اختبارات TSK-CEV-116 (NF-18): توحيد حارس الحقن في system السلاسل.

سياج سلوكي حتمي (P-11: FakeProvider يسجّل system_prompt فعليًّا —
صفر نداء نموذج حقيقي): يثبت أن **النص المُرسَل للمزوّد** في مسار
السلاسل (executor + دورة التفويض الثلاثية) ينتهي بحارس الحقن
INJECTION_GUARD_INSTRUCTION — نفس ضمانة مسار السيرفر/الدردشة —
وأن AgentPrompt.content يبقى نقيًّا (قرار نقطة الحقن عند مواقع
النداء لا داخل AgentLoader؛ انظر مواصفة TSK-CEV-116).
"""
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chain.agent_loader import AgentLoader                    # noqa: E402
from chain.delegate import DelegateBridge                     # noqa: E402
from chain.executor import ChainExecutor                      # noqa: E402
from prompts.templates import (                               # noqa: E402
    INJECTION_GUARD_INSTRUCTION,
    guarded_system,
)
from tests.fakes.fake_provider import FakeProvider            # noqa: E402

APPROVE_REVIEW = "[VERDICT]: APPROVE\n[SUMMARY]: عمل سليم"
IMPL = "نفذت المطلوب\n[TOUCHED]: src/utils.py"
GUARD_SUFFIX = "\n\n" + INJECTION_GUARD_INSTRUCTION


class TestGuardedSystemHelper:
    def test_appends_guard_with_system_prompt_separator(self):
        composed = guarded_system("ROLE CONTENT")
        assert composed.startswith("ROLE CONTENT")
        assert composed.endswith(GUARD_SUFFIX)
        # الحارس يظهر مرة واحدة بالضبط — لا ازدواج
        assert composed.count(INJECTION_GUARD_INSTRUCTION) == 1

    def test_empty_content_returns_bare_guard(self):
        """محتوى فارغ ⇒ الحارس وحده بلا فاصل معلّق."""
        assert guarded_system("") == INJECTION_GUARD_INSTRUCTION


class TestDelegateCycleSystemGuard:
    def test_all_three_phase_system_prompts_end_with_guard(self):
        """دورة تفويض كاملة (planner → executor → code_reviewer):
        كل system_prompt مُسجَّل لدى المزوّد ينتهي بالحارس."""
        provider = FakeProvider(responses=["brief-1", IMPL, APPROVE_REVIEW])
        loader = AgentLoader()
        bridge = DelegateBridge(provider, agent_loader=loader)

        run = bridge.run_delegation(
            "أضف دالة مساعدة", {"src/utils.py": "def x():\n    pass\n"})

        assert run.status == "waiting_approval"
        assert len(provider.calls) == 3
        for call in provider.calls:
            assert call.system_prompt.endswith(GUARD_SUFFIX), (
                f"system_prompt for phase call lacks the injection "
                f"guard suffix (TSK-CEV-116 regressed): "
                f"...{call.system_prompt[-80:]!r}")
            assert call.system_prompt.count(
                INJECTION_GUARD_INSTRUCTION) == 1

    def test_role_content_precedes_guard_and_stays_clean(self):
        """التركيب = محتوى الدور النقي + الفاصل + الحارس —
        وAgentPrompt.content نفسه يبقى بلا حارس (نقاء المصدر)."""
        provider = FakeProvider(responses=["brief-1", IMPL, APPROVE_REVIEW])
        loader = AgentLoader()
        bridge = DelegateBridge(provider, agent_loader=loader)
        bridge.run_delegation("مهمة", {"a.py": "x = 1\n"})

        for role, call in zip(("planner", "executor", "code_reviewer"),
                              provider.calls):
            content = loader.load(role).content
            assert INJECTION_GUARD_INSTRUCTION not in content, (
                f"AgentPrompt.content for {role} polluted with guard")
            assert call.system_prompt == guarded_system(content)


class TestExecutorSystemGuard:
    def test_call_provider_sends_guarded_system(self):
        """مسار السلاسل العام: _call_provider يركّب الدور + الحارس."""
        provider = FakeProvider(responses=["ok"])
        loader = AgentLoader()
        executor = ChainExecutor(provider, agent_loader=loader)

        agent_prompt = loader.load("executor")
        executor._call_provider("افعل شيئًا", agent_prompt)

        assert len(provider.calls) == 1
        sent = provider.calls[0].system_prompt
        assert sent == guarded_system(agent_prompt.content)
        assert sent.endswith(GUARD_SUFFIX)
        assert INJECTION_GUARD_INSTRUCTION not in agent_prompt.content
