# -*- coding: utf-8 -*-
"""T-029 (R-302): اختبارات ConversationMemory — الواجهة والسياسات
والتثبيت والطي فوق مخزن JSONL الحقيقي (لا mocks للتخزين).
"""
from __future__ import annotations

import pathlib

import pytest

from sessions.memory import (
    ConversationMemory,
    POLICY_CHAT,
    POLICY_DELEGATE,
    POLICY_FULL,
    Turn,
    WindowPolicy,
)
from sessions.store import SessionStore


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> SessionStore:
    return SessionStore(tmp_path / "sessions", fsync="never")


@pytest.fixture()
def memory(store: SessionStore) -> ConversationMemory:
    meta = store.create()
    return ConversationMemory(store, meta.id)


def _fill(memory: ConversationMemory, n: int) -> list[int]:
    ids = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        ids.append(memory.append(role, f"رسالة {i}"))
    return ids


# ═════════════════ append / turns ═════════════════

class TestAppendAndTurns:

    def test_append_returns_sequential_turn_ids(self, memory):
        assert _fill(memory, 3) == [0, 1, 2]

    def test_turns_reflect_log_order(self, memory):
        _fill(memory, 4)
        turns = memory.turns()
        assert [t.turn_id for t in turns] == [0, 1, 2, 3]
        assert [t.content for t in turns] == [f"رسالة {i}" for i in range(4)]
        assert all(t.ts for t in turns)

    def test_turn_ids_stable_across_instances(self, store, memory):
        """turn_id مشتق من السجل — نسخة جديدة ترى نفس الفهارس وتكمل."""
        _fill(memory, 3)
        fresh = ConversationMemory(store, memory._session_id)
        assert fresh.append("user", "رابعة") == 3
        assert [t.turn_id for t in fresh.turns()] == [0, 1, 2, 3]

    def test_agent_visibility_recorded(self, memory):
        memory.append("tool", "نتيجة أداة", visibility="agent")
        assert memory.turns()[0].visibility == "agent"

    def test_bad_visibility_rejected(self, memory):
        with pytest.raises(ValueError):
            memory.append("user", "x", visibility="secret")

    def test_extra_fields_persisted(self, store, memory):
        memory.append("tool", "خرج", visibility="agent", tool_name="read")
        rec = store.replay(memory._session_id).records[0]
        assert rec["tool_name"] == "read"

    def test_plain_t027_records_read_as_turns(self, store):
        """توافق خلفي: سجلات T-027/T-028 (بلا kind) أدوار مرئية user."""
        meta = store.create()
        store.append_message(meta.id, "user", "قديمة")
        mem = ConversationMemory(store, meta.id)
        turns = mem.turns()
        assert len(turns) == 1
        assert turns[0].visibility == "user"
        # والإلحاق الجديد يكمل الترقيم فوقها
        assert mem.append("assistant", "جديدة") == 1


# ═════════════════ سياسات النافذة ═════════════════

class TestWindowPolicies:

    def test_full_policy_returns_everything(self, memory):
        _fill(memory, 12)
        assert len(memory.window(POLICY_FULL)) == 12

    def test_chat_policy_matches_legacy_minus_10_slice(self, memory):
        """خريطة T-030: POLICY_CHAT ≡ messages[-10:] حرفيًا."""
        _fill(memory, 15)
        window = memory.window(POLICY_CHAT)
        assert [t.content for t in window] == [
            f"رسالة {i}" for i in range(5, 15)]

    def test_delegate_policy_matches_legacy_minus_6_slice(self, memory):
        _fill(memory, 15)
        window = memory.window(POLICY_DELEGATE)
        assert [t.content for t in window] == [
            f"رسالة {i}" for i in range(9, 15)]

    def test_last_n_larger_than_history(self, memory):
        _fill(memory, 3)
        assert len(memory.window(WindowPolicy(last_n=10))) == 3

    def test_last_n_zero(self, memory):
        _fill(memory, 3)
        assert memory.window(WindowPolicy(last_n=0)) == []

    def test_agent_turns_excluded_by_default(self, memory):
        memory.append("user", "سؤال")
        memory.append("tool", "نتيجة أداة", visibility="agent")
        memory.append("assistant", "جواب")
        contents = [t.content for t in memory.window(POLICY_CHAT)]
        assert contents == ["سؤال", "جواب"]

    def test_agent_turns_included_when_asked(self, memory):
        memory.append("user", "سؤال")
        memory.append("tool", "نتيجة أداة", visibility="agent")
        window = memory.window(WindowPolicy(include_agent=True))
        assert [t.content for t in window] == ["سؤال", "نتيجة أداة"]

    def test_window_order_is_always_log_order(self, memory):
        _fill(memory, 8)
        window = memory.window(WindowPolicy(last_n=4))
        assert [t.turn_id for t in window] == sorted(
            t.turn_id for t in window)

    def test_invalid_policy_values_rejected(self):
        with pytest.raises(ValueError):
            WindowPolicy(last_n=-1)
        with pytest.raises(ValueError):
            WindowPolicy(token_budget=-5)


# ═════════════════ ميزانية التوكنز ═════════════════

class TestTokenBudget:

    def test_budget_keeps_newest_whole_or_drop(self, memory):
        # 3 أدوار × ~25 توكن (100 حرف / 4) — ميزانية 60 تسع الأحدثَين
        for i in range(3):
            memory.append("user", f"{i}" * 100)
        window = memory.window(WindowPolicy(token_budget=60))
        assert [t.turn_id for t in window] == [1, 2]

    def test_budget_never_truncates_mid_turn(self, memory):
        memory.append("user", "ق" * 100)          # ~25 توكن
        memory.append("assistant", "ص" * 1000)    # ~250 توكن
        window = memory.window(WindowPolicy(token_budget=30))
        # الأحدث لا يسع (250 > 30) فيسقط كاملًا؛ الأقدم (25) يدخل كاملًا
        assert [len(t.content) for t in window] == [100]

    def test_budget_zero_gives_empty(self, memory):
        _fill(memory, 3)
        assert memory.window(WindowPolicy(token_budget=0)) == []

    def test_last_n_composes_with_budget(self, memory):
        # last_n=4 أولًا ثم الميزانية تشذّب الأربعة
        for i in range(8):
            memory.append("user", f"{i}" * 100)   # ~25 توكن للدور
        window = memory.window(WindowPolicy(last_n=4, token_budget=60))
        assert [t.turn_id for t in window] == [6, 7]


# ═════════════════ التثبيت ═════════════════

class TestPinning:

    def test_pinned_survives_last_n_trim(self, memory):
        ids = _fill(memory, 12)
        memory.pin(ids[0])   # أول دور — كان سيسقط من آخر-10
        window = memory.window(POLICY_CHAT)
        assert ids[0] in [t.turn_id for t in window]
        assert window[0].turn_id == ids[0]   # وبترتيب السجل

    def test_pinned_survives_token_budget(self, memory):
        memory.append("user", "تعليمات مثبتة " + "م" * 100)
        for i in range(5):
            memory.append("assistant", f"{i}" * 200)
        memory.pin(0)
        window = memory.window(WindowPolicy(token_budget=80))
        assert 0 in [t.turn_id for t in window]

    def test_pinned_budget_charged_first(self, memory):
        memory.append("user", "م" * 200)    # ~50 توكن — سيُثبَّت
        memory.append("user", "أ" * 100)    # ~25
        memory.append("user", "ب" * 100)    # ~25
        memory.pin(0)
        window = memory.window(WindowPolicy(token_budget=80))
        # 80 - 50 (مثبت) = 30 ⇒ يسع الأحدث فقط
        assert [t.turn_id for t in window] == [0, 2]

    def test_unpin_restores_normal_trimming(self, memory):
        ids = _fill(memory, 12)
        memory.pin(ids[0])
        memory.unpin(ids[0])
        assert ids[0] not in [t.turn_id for t in memory.window(POLICY_CHAT)]

    def test_pin_state_derived_from_log_across_instances(self, store, memory):
        ids = _fill(memory, 12)
        memory.pin(ids[1])
        fresh = ConversationMemory(store, memory._session_id)
        window = fresh.window(POLICY_CHAT)
        assert ids[1] in [t.turn_id for t in window]

    def test_pin_unknown_turn_rejected(self, memory):
        _fill(memory, 2)
        with pytest.raises(ValueError):
            memory.pin(99)

    def test_pin_markers_are_not_turns(self, memory):
        ids = _fill(memory, 3)
        memory.pin(ids[0])
        memory.unpin(ids[0])
        assert len(memory.turns()) == 3   # العلامات لا تظهر كأدوار


# ═════════════════ الأعقاب (stubs) ═════════════════

class TestStubs:

    def test_summary_stub_returns_none(self, memory):
        _fill(memory, 3)
        assert memory.summary() is None

    def test_search_stub_returns_empty(self, memory):
        _fill(memory, 3)
        assert memory.search("رسالة") == []


# ═════════════════ تكامل فوق JSONL الحقيقي ═════════════════

class TestJsonlIntegration:

    def test_append_window_round_trip_on_disk(self, store):
        """معيار القبول: append/window فوق المخزن الحقيقي على القرص."""
        meta = store.create()
        mem = ConversationMemory(store, meta.id)
        mem.append("user", "أول سؤال")
        mem.append("assistant", "أول جواب")
        mem.append("tool", "قراءة ملف", visibility="agent")
        mem.append("user", "ثاني سؤال")
        mem.pin(0)

        # عملية جديدة تمامًا (كاش بارد) — كل الحالة من القرص
        fresh_store = SessionStore(store.sessions_dir)
        fresh = ConversationMemory(fresh_store, meta.id)
        window = fresh.window(WindowPolicy(last_n=2))
        assert [t.content for t in window] == \
            ["أول سؤال", "أول جواب", "ثاني سؤال"]
        assert window[0].pinned is True

    def test_torn_tail_tolerated(self, store):
        """صدمة أثناء الكتابة — الذاكرة ترى الأدوار السليمة فقط."""
        meta = store.create()
        mem = ConversationMemory(store, meta.id)
        mem.append("user", "سليمة")
        with open(store.data_path(meta.id), "a", encoding="utf-8") as f:
            f.write('{"kind": "message", "role": "user", "con')
        fresh = ConversationMemory(SessionStore(store.sessions_dir), meta.id)
        assert [t.content for t in fresh.turns()] == ["سليمة"]
