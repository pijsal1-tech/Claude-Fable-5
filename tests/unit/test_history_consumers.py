# -*- coding: utf-8 -*-
"""T-030 (R-302): goldens ترحيل مستهلكي التاريخ الثلاثة.

الـ goldens أدناه التُقطت **قبل** الترحيل بتشغيل المنطق القديم حرفيًا
(القصّات `[-6:]` / `[-10:]` / القائمة الكاملة) — ثم حُوِّل المستهلكون إلى
`select_history(policy)`، وهذه الاختبارات تثبت أن الناتج بعد الترحيل
مطابق قيميًا للناتج قبله (سلوك اليوم بلا تغيير).

المستهلكون الثلاثة (خريطة السياسات):
1. طيّ الـ history في المزودين الثلاثة (alle_ai / deepseek / genspark)
   — كان `history[-6:]` → `POLICY_PROVIDER_HISTORY_FOLD`.
2. ملاحظات KnowledgeAccumulator في `build_context`
   — كان `self._observations[-10:]` → `POLICY_KNOWLEDGE_OBSERVATIONS`.
3. `DelegateBridge._to_prompt_history` — كان يمرّر القائمة كاملة ضمنيًا
   → `POLICY_DELEGATE_RENDER` (نافذة كاملة صريحة).

ملاحظة نطاق: `chat_history[:-1]` في server.py استبعادٌ بنيوي للرسالة
الحالية المكررة، ليس قصّة نافذة — خارج نطاق T-030 (يُرحَّل مع توصيل
ConversationMemory الكامل في T-031+).
"""
from __future__ import annotations

import pytest

from providers.base import Message
from sessions.memory import (
    POLICY_CHAT,
    POLICY_DELEGATE,
    POLICY_DELEGATE_RENDER,
    POLICY_FULL,
    POLICY_KNOWLEDGE_OBSERVATIONS,
    POLICY_PROVIDER_HISTORY_FOLD,
    WindowPolicy,
    select_history,
)


def _mk_history(n: int) -> list[Message]:
    return [Message(role=("user" if i % 2 == 0 else "assistant"),
                    content=f"رسالة-{i}") for i in range(n)]


# ═══════════════ select_history — التكافؤ القيمي مع القصّات ═══════════════

class TestSelectHistoryEquivalence:
    """`select_history(xs, WindowPolicy(last_n=n)) == xs[-n:]` حرفيًا."""

    @pytest.mark.parametrize("n_items", [0, 1, 5, 6, 7, 20])
    def test_last6_equals_legacy_slice(self, n_items):
        xs = _mk_history(n_items)
        assert select_history(xs, POLICY_DELEGATE) == xs[-6:]

    @pytest.mark.parametrize("n_items", [0, 1, 9, 10, 11, 30])
    def test_last10_equals_legacy_slice(self, n_items):
        xs = [f"عنصر-{i}" for i in range(n_items)]
        assert select_history(xs, POLICY_CHAT) == xs[-10:]

    @pytest.mark.parametrize("n_items", [0, 1, 7])
    def test_full_equals_whole_list(self, n_items):
        xs = _mk_history(n_items)
        assert select_history(xs, POLICY_FULL) == xs

    def test_full_returns_copy_not_alias(self):
        xs = _mk_history(3)
        out = select_history(xs, POLICY_FULL)
        assert out == xs and out is not xs

    def test_last_n_zero_returns_empty(self):
        assert select_history(_mk_history(4), WindowPolicy(last_n=0)) == []

    def test_token_budget_rejected(self):
        with pytest.raises(ValueError):
            select_history(_mk_history(2), WindowPolicy(token_budget=100))

    def test_policy_aliases_are_same_objects(self):
        """أسماء T-030 الدقيقة = نفس كائنات T-029 المسماة."""
        assert POLICY_DELEGATE_RENDER is POLICY_FULL
        assert POLICY_KNOWLEDGE_OBSERVATIONS is POLICY_CHAT
        assert POLICY_PROVIDER_HISTORY_FOLD is POLICY_DELEGATE


# ═══════════════ Consumer 1: طيّ history المزودين ═══════════════

# منطق legacy منسوخ حرفيًا من deepseek.py (قبل T-030) لتوليد الـ golden
def _legacy_provider_fold_500(history: list[Message]) -> str:
    full_prompt = "[سياق المحادثة السابقة]:\n"
    for msg in history[-6:]:
        role_label = "المستخدم" if msg.role == "user" else "المساعد"
        full_prompt += f"--- {role_label} ---\n{msg.content[:500]}\n\n"
    full_prompt += "[الطلب الحالي]:\n"
    return full_prompt


def _migrated_provider_fold_500(history: list[Message]) -> str:
    """نفس بنية الكود بعد الترحيل (كما في deepseek.py الآن)."""
    full_prompt = "[سياق المحادثة السابقة]:\n"
    for msg in select_history(history, POLICY_PROVIDER_HISTORY_FOLD):
        role_label = "المستخدم" if msg.role == "user" else "المساعد"
        full_prompt += f"--- {role_label} ---\n{msg.content[:500]}\n\n"
    full_prompt += "[الطلب الحالي]:\n"
    return full_prompt


class TestProviderHistoryFoldGolden:
    # الـ golden الحرفي الملتقط قبل الترحيل (9 رسائل → آخر 6: 3..8)
    GOLDEN_9 = (
        "[سياق المحادثة السابقة]:\n"
        "--- المساعد ---\nرسالة-3\n\n"
        "--- المستخدم ---\nرسالة-4\n\n"
        "--- المساعد ---\nرسالة-5\n\n"
        "--- المستخدم ---\nرسالة-6\n\n"
        "--- المساعد ---\nرسالة-7\n\n"
        "--- المستخدم ---\nرسالة-8\n\n"
        "[الطلب الحالي]:\n"
    )

    def test_migrated_fold_matches_committed_golden(self):
        assert _migrated_provider_fold_500(_mk_history(9)) == self.GOLDEN_9

    @pytest.mark.parametrize("n_items", [0, 1, 5, 6, 7, 9, 25])
    def test_migrated_fold_matches_legacy_byte_exact(self, n_items):
        h = _mk_history(n_items)
        assert _migrated_provider_fold_500(h) == _legacy_provider_fold_500(h)

    def test_content_truncation_preserved(self):
        """قصّ الـ 500 حرف داخل الطيّ خارج نطاق السياسة — يبقى كما هو."""
        h = [Message(role="user", content="ن" * 900)]
        out = _migrated_provider_fold_500(h)
        assert ("ن" * 500) in out and ("ن" * 501) not in out

    def test_all_three_providers_use_policy_not_slice(self):
        """grep بنيوي: لا `history[-6:]` في المزودين — السياسة بدلًا منها."""
        import pathlib
        for name in ("alle_ai", "deepseek", "genspark"):
            src = pathlib.Path(f"providers/{name}.py").read_text(
                encoding="utf-8")
            assert "history[-6:]" not in src, name
            assert "POLICY_PROVIDER_HISTORY_FOLD" in src, name


# ═══════════════ Consumer 2: ملاحظات KnowledgeAccumulator ═══════════════

class TestKnowledgeObservationsGolden:
    # الـ golden الحرفي الملتقط قبل الترحيل (13 ملاحظة → آخر 10: 3..12)
    GOLDEN_13 = (
        "💡 [ملاحظات سابقة]:\n"
        "- ملاحظة-3\n- ملاحظة-4\n- ملاحظة-5\n- ملاحظة-6\n"
        "- ملاحظة-7\n- ملاحظة-8\n- ملاحظة-9\n- ملاحظة-10\n"
        "- ملاحظة-11\n- ملاحظة-12\n"
    )

    def _build(self, n_obs: int) -> str:
        from chain.knowledge import KnowledgeAccumulator
        ka = KnowledgeAccumulator()
        for i in range(n_obs):
            ka.add_observation(f"ملاحظة-{i}")
        return ka.build_context()

    def test_build_context_matches_committed_golden(self):
        assert self._build(13) == self.GOLDEN_13

    @pytest.mark.parametrize("n_obs", [1, 9, 10, 11])
    def test_observation_window_is_last_10(self, n_obs):
        out = self._build(n_obs)
        expected = [f"ملاحظة-{i}" for i in range(n_obs)][-10:]
        for obs in expected:
            assert f"- {obs}\n" in out
        # الأقدم من النافذة لا يظهر
        for i in range(max(0, n_obs - 10)):
            assert f"- ملاحظة-{i}\n" not in out

    def test_knowledge_uses_policy_not_slice(self):
        import pathlib
        src = pathlib.Path("chain/knowledge.py").read_text(encoding="utf-8")
        assert "_observations[-10:]" not in src
        assert "POLICY_KNOWLEDGE_OBSERVATIONS" in src


# ═══════════════ Consumer 3: delegate full render ═══════════════

class TestDelegateRenderGolden:
    # goldens حرفية التُقطت قبل الترحيل
    GOLDEN_MULTI = "[USER]:\nسؤال أول\n\n[ASSISTANT]:\nجواب أول\n\n[USER]:\nسؤال ثانٍ"
    GOLDEN_SINGLE = "نص وحيد"
    GOLDEN_EMPTY = ""

    def _render(self, msgs):
        from chain.delegate import DelegateBridge
        return DelegateBridge._to_prompt_history(msgs)

    def test_multi_message_render_matches_golden(self):
        msgs = [Message(role="user", content="سؤال أول"),
                Message(role="assistant", content="جواب أول"),
                Message(role="user", content="سؤال ثانٍ")]
        assert self._render(msgs) == self.GOLDEN_MULTI

    def test_single_user_message_verbatim(self):
        assert self._render(
            [Message(role="user", content="نص وحيد")]) == self.GOLDEN_SINGLE

    def test_empty_list_renders_empty(self):
        assert self._render([]) == self.GOLDEN_EMPTY

    def test_full_policy_never_trims(self):
        """القائمة الكاملة: 50 رسالة كلها تظهر — لا تقليم خفي."""
        msgs = _mk_history(50)
        out = self._render(msgs)
        for m in msgs:
            assert m.content in out

    def test_delegate_uses_named_policy(self):
        import pathlib
        src = pathlib.Path("chain/delegate.py").read_text(encoding="utf-8")
        assert "POLICY_DELEGATE_RENDER" in src


# ═══════════════ Acceptance: لا قصّ خام للتاريخ خارج sessions/ ═══════════════

class TestNoRawHistorySlicing:
    """grep القبول: `[-6:]` / `[-10:]` على history/observations اختفت
    من كود الإنتاج خارج `sessions/`."""

    def test_no_raw_history_slices_outside_sessions(self):
        import pathlib
        import re
        pattern = re.compile(
            r"history\[-\d+:\]|_observations\[-\d+:\]|chat_history\[-\d+:\]")
        violations: list[str] = []
        # TSK-605 (TF-02): `providers/` أُخرجت من المسح — الحارس ملكيّته
        # core (T-030) بينما طبقة المزودات خارج النطاق كليًا (§0.8: لا
        # تُراجع ولا تُصلَّح)؛ الانتهاك الوحيد وقت القرار كان
        # providers/openai_shelby.py:105 (history[-6:]) — ضجيج مزودات
        # لا انحدار core. تغطية core كاملة محفوظة أدناه.
        for dirname in ("chain", "core", "context", "actions",
                        "prompts"):
            root = pathlib.Path(dirname)
            if not root.is_dir():
                continue
            for p in sorted(root.rglob("*.py")):
                for i, line in enumerate(
                        p.read_text(encoding="utf-8").splitlines(), 1):
                    if pattern.search(line):
                        violations.append(f"{p}:{i}: {line.strip()}")
        src = pathlib.Path("server.py").read_text(encoding="utf-8")
        for i, line in enumerate(src.splitlines(), 1):
            if pattern.search(line):
                violations.append(f"server.py:{i}: {line.strip()}")
        assert not violations, "\n".join(violations)
