# -*- coding: utf-8 -*-
"""TSK-611 (QG-01، ADR-001): اختبارات راوتر WS — جدول dispatch.

يغطي فجوة الأدلة (§TSK-611): لا golden مخصصًا لتوجيه WS كان موجودًا —
هذا الاختبار يثبّت (أ) دالة dispatch النقية، (ب) اكتمال جدول
WS_HANDLERS في server.py مقابل قائمة الأنواع الـ25 المستخرجة حرفيًا
من السلسلة الأصلية (server.py:2034..2539 قبل الاستخراج)،
(جـ) سلوك النوع المجهول = no-op صامت.
"""
import pytest

from core.ws_router import dispatch


# الأنواع الـ25 حرفيًا من السلسلة الأصلية (أدلة §TSK-611) — تجميد
# للتوجيه: أي حذف/إضافة غير مقصودة في الجدول تُكسر هنا.
ORIGINAL_MSG_TYPES = frozenset({
    "ping", "agent_approval_response", "cancel_agent",
    "confirm_path_action", "chain_approval_response",
    "rollback_run", "rollback_file", "message", "apply_action",
    "apply_all_actions", "execute_plan", "chain_message",
    "chain_cancel", "chain_status", "resume_scan", "resume_run",
    "discard_run", "list_runs", "cancel_run", "delegate_message",
    "delegate_approve", "delegate_reject", "memory_list",
    "memory_edit", "memory_delete",
    # TSK-732 (D-19-4): إضافة مقصودة — 4 أنواع للمهام الخلفية
    # (تستهلك FI-15) — التجميد 25 → 29.
    "background_delegate_message", "background_status",
    "background_approve", "background_reject",
})

# الأنواع المركّبة: مفتاحان → نفس المقبض (سلوك السلسلة الأصلية
# `msg_type in (...)`).
SHARED_HANDLER_GROUPS = [
    ("rollback_run", "rollback_file"),
    ("apply_all_actions", "execute_plan"),
]


class TestDispatchFunction:
    """دالة dispatch النقية — بلا server.py."""

    def test_routes_to_registered_handler_with_full_signature(self):
        calls = []
        handlers = {"foo": lambda ctx, sctx, msg: calls.append((ctx, sctx, msg))}
        msg = {"type": "foo", "x": 1}
        dispatch(handlers, "CTX", "SCTX", msg)
        assert calls == [("CTX", "SCTX", msg)]

    def test_unknown_type_is_silent_noop(self):
        """السلسلة الأصلية بلا else — نوع مجهول لا يفعل شيئًا."""
        assert dispatch({}, None, None, {"type": "no_such_type"}) is None

    def test_missing_type_key_defaults_to_empty_string(self):
        """يطابق ``msg.get("type", "")`` الأصلي حرفيًا."""
        hit = []
        handlers = {"": lambda ctx, sctx, msg: hit.append(True)}
        dispatch(handlers, None, None, {})
        assert hit == [True]

    def test_returns_handler_return_value(self):
        handlers = {"t": lambda ctx, sctx, msg: "RV"}
        assert dispatch(handlers, None, None, {"type": "t"}) == "RV"

    def test_only_matching_handler_called(self):
        calls = []
        handlers = {
            "a": lambda ctx, sctx, msg: calls.append("a"),
            "b": lambda ctx, sctx, msg: calls.append("b"),
        }
        dispatch(handlers, None, None, {"type": "b"})
        assert calls == ["b"]


class TestServerTable:
    """جدول WS_HANDLERS في server.py — اكتمال التوجيه المستخرج."""

    @pytest.fixture(scope="class")
    def table(self):
        import server
        return server.WS_HANDLERS

    def test_table_keys_exactly_match_original_25_types(self, table):
        # TSK-732 (D-19-4): التجميد صار 29 نوعًا (25 أصلية + 4 خلفية).
        assert set(table.keys()) == ORIGINAL_MSG_TYPES

    def test_all_handlers_are_callables_named_ws_prefix(self, table):
        for key, fn in table.items():
            assert callable(fn), key
            assert fn.__name__.startswith("_ws_"), (key, fn.__name__)

    def test_compound_types_share_one_handler(self, table):
        for a, b in SHARED_HANDLER_GROUPS:
            assert table[a] is table[b], (a, b)

    def test_handle_ws_message_unknown_type_noop(self, table):
        """التكامل: _handle_ws_message مع نوع مجهول لا يرمي ولا يرسل."""
        import server

        class _Sctx:
            def __init__(self):
                self.frames = []

            def send(self, frame):
                self.frames.append(frame)

        sctx = _Sctx()
        server._handle_ws_message(None, sctx, {"type": "definitely_unknown"})
        assert sctx.frames == []

    def test_handle_ws_message_ping_frame_bit_identical(self, table):
        """إطار pong كما كان حرفيًا (ctx=None → False)."""
        import server

        class _Sctx:
            def __init__(self):
                self.frames = []

            def send(self, frame):
                self.frames.append(frame)

        sctx = _Sctx()
        server._handle_ws_message(None, sctx, {"type": "ping"})
        assert sctx.frames == [{"type": "pong", "ctx": False}]
