# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  اختبارات providers/openai_compat — TSK-735b (القرار 7 / D-20)

  **صفر شبكة** (قرار المواصفة 5): كل النقل عبر monkeypatch على
  requests داخل الوحدة — بناء الطلب يُختبَر بالتقاط الوسائط.

  العقود المُثبَتة:
  1. بناء الطلب: URL = base_url/chat/completions؛ الترويسة تحمل
     المفتاح المحقون؛ payload بشكل chat/completions القياسي.
  2. 401/403 ⇒ ProviderAuthenticationError؛ 5xx/429 ⇒ Transient؛
     **رسالة الخطأ لا تحمل المفتاح ولا نص استجابة الخادم**.
  3. غياب المفتاح: is_available/initialize = False بلا استثناء؛
     send/stream يرفضان قبل أي نداء شبكة.
  4. عدم-الترديد: المفتاح لا يظهر في get_info/repr/str.
  5. stream: SSE قياسي يُفكَّك قطعًا؛ [DONE] يُنهي؛ السطر المعطوب
     يُتجاوَز.
═══════════════════════════════════════════════════════
"""
from __future__ import annotations

import json

import pytest

import providers.openai_compat as oc
from providers.base import (
    ProviderAuthenticationError,
    ProviderTimeoutError,
    ProviderTransientError,
)
from providers.openai_compat import OpenAICompatConfig, OpenAICompatProvider

SECRET = "sk-CANARY-735-do-not-echo"


def _provider(**kw) -> OpenAICompatProvider:
    cfg = OpenAICompatConfig(
        model=kw.pop("model", "test-model"),
        base_url=kw.pop("base_url", "https://api.example.test/v1"),
        api_key=kw.pop("api_key", SECRET),
        provider_id=kw.pop("provider_id", "my_test"),
        **kw,
    )
    return OpenAICompatProvider(cfg)


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, lines=None,
                 body_text="server says: Authorization leaked?"):
        self.status_code = status_code
        self._payload = payload
        self._lines = lines or []
        self.text = body_text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def iter_lines(self):
        yield from self._lines


@pytest.fixture
def capture(monkeypatch):
    """يلتقط وسائط requests.post ويعيد استجابة قابلة للبرمجة."""
    calls: list[dict] = []
    box = {"response": _FakeResponse(payload={
        "choices": [{"message": {"content": "مرحبا"}}]})}

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return box["response"]

    monkeypatch.setattr(oc.requests, "post", fake_post)
    return {"calls": calls, "box": box}


# ═══ 1) بناء الطلب ═══════════════════════════════════════════════

class TestRequestConstruction:
    def test_send_url_headers_payload(self, capture):
        p = _provider()
        out = p.send("سؤال", system_prompt="نظام")
        assert out == "مرحبا"
        call = capture["calls"][0]
        assert call["url"] == "https://api.example.test/v1/chat/completions"
        assert call["headers"]["Authorization"] == f"Bearer {SECRET}"
        body = call["json"]
        assert body["model"] == "test-model"
        assert body["stream"] is False
        assert body["messages"][0] == {"role": "system", "content": "نظام"}
        assert body["messages"][-1] == {"role": "user", "content": "سؤال"}

    def test_trailing_slash_in_base_url_normalized(self, capture):
        p = _provider(base_url="http://localhost:11434/v1/")
        p.send("hi")
        assert capture["calls"][0]["url"] == (
            "http://localhost:11434/v1/chat/completions")

    def test_history_is_flattened_in_order(self, capture):
        from providers.base import Message
        p = _provider()
        p.send("ثالثة", history=[Message(role="user", content="أولى"),
                                 Message(role="assistant", content="ثانية")])
        msgs = capture["calls"][0]["json"]["messages"]
        assert [(m["role"], m["content"]) for m in msgs] == [
            ("user", "أولى"), ("assistant", "ثانية"), ("user", "ثالثة")]

    def test_stream_flag_true_for_stream(self, capture):
        capture["box"]["response"] = _FakeResponse(lines=[b"data: [DONE]"])
        list(_provider().stream("hi"))
        assert capture["calls"][0]["json"]["stream"] is True


# ═══ 2) خريطة الأخطاء + عدم-الترديد في الرسائل ═══════════════════

class TestErrorMapping:
    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_error_types(self, capture, status):
        capture["box"]["response"] = _FakeResponse(status_code=status)
        with pytest.raises(ProviderAuthenticationError) as exc:
            _provider().send("hi")
        msg = str(exc.value)
        assert SECRET not in msg
        assert "Authorization leaked" not in msg  # نص الخادم لا يُردَّد
        assert str(status) in msg

    @pytest.mark.parametrize("status,exc_type", [
        (429, ProviderTransientError),
        (500, ProviderTransientError),
        (503, ProviderTransientError),
        (404, ProviderTransientError),
    ])
    def test_non_auth_errors_transient(self, capture, status, exc_type):
        capture["box"]["response"] = _FakeResponse(status_code=status)
        with pytest.raises(exc_type) as exc:
            _provider().send("hi")
        assert SECRET not in str(exc.value)

    def test_timeout_maps_to_provider_timeout(self, monkeypatch):
        def raise_timeout(url, **kw):
            raise oc.requests.Timeout("boom")
        monkeypatch.setattr(oc.requests, "post", raise_timeout)
        with pytest.raises(ProviderTimeoutError) as exc:
            _provider().send("hi")
        assert SECRET not in str(exc.value)

    def test_network_error_message_hides_details(self, monkeypatch):
        # نص الاستثناء الخام قد يحمل الترويسات — لا يُمرَّر
        def raise_conn(url, **kw):
            raise oc.requests.ConnectionError(
                f"failed with header Bearer {SECRET}")
        monkeypatch.setattr(oc.requests, "post", raise_conn)
        with pytest.raises(ProviderTransientError) as exc:
            _provider().send("hi")
        assert SECRET not in str(exc.value)

    def test_malformed_json_transient(self, capture):
        capture["box"]["response"] = _FakeResponse(payload=None)
        with pytest.raises(ProviderTransientError):
            _provider().send("hi")


# ═══ 3) غياب المفتاح — حالة مشروعة fail-closed ═══════════════════

class TestMissingKey:
    def test_unavailable_without_key_or_url(self):
        assert _provider(api_key="").is_available() is False
        assert _provider(base_url="").is_available() is False
        assert _provider().is_available() is True

    def test_initialize_false_no_exception(self):
        p = _provider(api_key="")
        assert p.initialize() is False
        assert p._initialized is False

    def test_send_and_stream_refuse_before_any_network(self, monkeypatch):
        def explode(url, **kw):  # pragma: no cover — يجب ألا يُستدعى
            raise AssertionError("network call attempted without key")
        monkeypatch.setattr(oc.requests, "post", explode)
        p = _provider(api_key="")
        with pytest.raises(ProviderAuthenticationError):
            p.send("hi")
        with pytest.raises(ProviderAuthenticationError):
            list(p.stream("hi"))


# ═══ 4) عدم-الترديد — المفتاح لا يظهر في أي تمثيل ════════════════

class TestNoEcho:
    def test_get_info_has_flag_not_key(self):
        info = _provider().get_info()
        assert info["key_configured"] is True
        assert SECRET not in json.dumps(info, ensure_ascii=False)

    def test_repr_and_str_hide_key(self):
        p = _provider()
        assert SECRET not in repr(p)
        assert SECRET not in str(p)

    def test_info_name_is_provider_id(self):
        assert _provider().get_info()["name"] == "my_test"


# ═══ 5) stream — تفكيك SSE القياسي ═══════════════════════════════

def _sse(*chunks: str, done: bool = True) -> list[bytes]:
    lines = []
    for c in chunks:
        payload = {"choices": [{"delta": {"content": c}}]}
        lines.append(f"data: {json.dumps(payload, ensure_ascii=False)}"
                     .encode("utf-8"))
        lines.append(b"")  # keep-alive فارغ
    if done:
        lines.append(b"data: [DONE]")
    return lines


class TestStream:
    def test_chunks_yielded_in_order(self, capture):
        capture["box"]["response"] = _FakeResponse(
            lines=_sse("مر", "حبا", " بك"))
        assert list(_provider().stream("hi")) == ["مر", "حبا", " بك"]

    def test_done_terminates_even_with_trailing_lines(self, capture):
        after_done = ('data: {"choices":[{"delta":{"content":"بعد"}}]}'
                      .encode("utf-8"))
        lines = _sse("قبل") + [after_done]
        capture["box"]["response"] = _FakeResponse(lines=lines)
        assert list(_provider().stream("hi")) == ["قبل"]

    def test_malformed_sse_line_skipped(self, capture):
        lines = [b"data: {broken json", b": comment line",
                 *_sse("سليم")]
        capture["box"]["response"] = _FakeResponse(lines=lines)
        assert list(_provider().stream("hi")) == ["سليم"]

    def test_auth_error_on_stream(self, capture):
        capture["box"]["response"] = _FakeResponse(status_code=401)
        with pytest.raises(ProviderAuthenticationError) as exc:
            list(_provider().stream("hi"))
        assert SECRET not in str(exc.value)
