# -*- coding: utf-8 -*-
"""QA-T06 (جزء TSK-104) — سقف تاريخ المحادثة عند نقطة الإرسال (NF-07).

صفر استدعاءات AI خارجية: الاختبار على _payload_history/_history_payload_policy
مباشرة عبر sctx مزيّف — لا شبكة، لا مزود.

معيار القبول (IMPLEMENTATION_TASKS): جلسة 200 رسالة → حمولة history
مسقوفة وفق config؛ اختبار وحدة على القصّ.
"""
import server
from providers.base import Message
from sessions.memory import WindowPolicy


class _StubSctx:
    def __init__(self, n_messages: int):
        self.chat_history = [
            Message(role="user" if i % 2 == 0 else "assistant",
                    content=f"رسالة {i}")
            for i in range(n_messages)
        ]


class TestPolicyFromConfig:
    """_history_payload_policy: قراءة history.payload_last_n بتسامح."""

    def test_key_present(self):
        p = server._history_payload_policy({"history": {"payload_last_n": 40}})
        assert p == WindowPolicy(last_n=40)

    def test_key_absent_means_no_cap(self):
        """غياب المفتاح = بلا سقف — الافتراضي المتوافق سلوكيًا الموثّق."""
        assert server._history_payload_policy({}) == WindowPolicy()
        assert server._history_payload_policy({"history": {}}) == WindowPolicy()

    def test_null_means_no_cap(self):
        p = server._history_payload_policy({"history": {"payload_last_n": None}})
        assert p == WindowPolicy()

    def test_invalid_value_tolerant_fallback(self):
        """قيمة غير صالحة ⇒ سقوط متسامح على بلا سقف (لا يعطّل الرد)."""
        p = server._history_payload_policy({"history": {"payload_last_n": "abc"}})
        assert p == WindowPolicy()
        p = server._history_payload_policy({"history": {"payload_last_n": -3}})
        assert p == WindowPolicy()

    def test_config_yaml_has_key(self):
        """config.yaml الفعلي يحمل المفتاح الجديد (TSK-104)."""
        cfg = server._read_config()
        assert "history" in cfg
        assert "payload_last_n" in cfg["history"]


class TestPayloadHistoryCapped:
    """معيار القبول: جلسة 200 رسالة → الحمولة مسقوفة وفق config."""

    def test_200_messages_capped(self):
        sctx = _StubSctx(200)
        out = server._payload_history(sctx, {"history": {"payload_last_n": 40}})
        assert len(out) == 40
        # آخر 40 من الـ 199 (بعد الاستبعاد البنيوي للرسالة الحالية)
        assert out == sctx.chat_history[:-1][-40:]
        assert out[-1].content == "رسالة 198"

    def test_current_message_always_excluded(self):
        """الاستبعاد البنيوي [:-1] محفوظ — الرسالة الحالية تمر في الـ prompt."""
        sctx = _StubSctx(5)
        out = server._payload_history(sctx, {"history": {"payload_last_n": 100}})
        assert len(out) == 4
        assert all(m.content != "رسالة 4" for m in out)

    def test_no_cap_backward_compatible(self):
        """بلا مفتاح: نفس سلوك ما قبل TSK-104 حرفيًا (chat_history[:-1])."""
        sctx = _StubSctx(200)
        out = server._payload_history(sctx, {})
        assert out == sctx.chat_history[:-1]
        assert len(out) == 199

    def test_short_history_unaffected_by_cap(self):
        sctx = _StubSctx(10)
        out = server._payload_history(sctx, {"history": {"payload_last_n": 40}})
        assert out == sctx.chat_history[:-1]

    def test_empty_history(self):
        sctx = _StubSctx(0)
        assert server._payload_history(sctx, {"history": {"payload_last_n": 40}}) == []
