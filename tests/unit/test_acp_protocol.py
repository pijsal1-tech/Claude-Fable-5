# -*- coding: utf-8 -*-
"""
اختبارات TSK-736a — نواة بروتوكول ACP النقية (القرار 8 من تسلسل D-19).

صفر subprocess وصفر شبكة (القرار الواعي 5 في مواصفة TSK-736):
- protocol: بناء/تحليل JSON-RPC 2.0 fail-closed.
- connection: مراسلة فوق FakeTransport مُحقَن — round-trip، ردود خارج
  الترتيب، إشعارات متداخلة، JSON فاسد يُتجاهَل، مهلة، EOF يوقظ
  المنتظرين، أخطاء المعالج لا تسرّب تفاصيل.
"""
from __future__ import annotations

import json
import queue
import threading

import pytest

from chain.acp.connection import (
    AcpConnection,
    AcpConnectionClosed,
    AcpProtocolError,
    AcpTimeoutError,
)
from chain.acp.protocol import (
    ERR_PATH_FORBIDDEN,
    INTERNAL_ERROR,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    ErrorResponse,
    Notification,
    Request,
    Response,
    parse_line,
    serialize,
)


# ═══ protocol: البناء ═══

class TestSerialize:
    def test_request_roundtrip(self):
        line = serialize(Request(id=1, method="session/prompt",
                                 params={"text": "مرحبا"}))
        obj = json.loads(line)
        assert obj == {"jsonrpc": "2.0", "id": 1,
                       "method": "session/prompt",
                       "params": {"text": "مرحبا"}}

    def test_request_without_params_omits_key(self):
        obj = json.loads(serialize(Request(id=2, method="initialize")))
        assert "params" not in obj

    def test_notification_has_no_id(self):
        obj = json.loads(serialize(Notification(method="session/update",
                                                params={"k": 1})))
        assert "id" not in obj
        assert obj["method"] == "session/update"

    def test_response(self):
        obj = json.loads(serialize(Response(id="abc", result={"ok": True})))
        assert obj == {"jsonrpc": "2.0", "id": "abc", "result": {"ok": True}}

    def test_error_response_with_null_id(self):
        obj = json.loads(serialize(ErrorResponse(id=None,
                                                 code=INVALID_REQUEST,
                                                 message="bad")))
        assert obj["id"] is None
        assert obj["error"] == {"code": INVALID_REQUEST, "message": "bad"}

    def test_arabic_not_escaped(self):
        line = serialize(Notification(method="m", params={"t": "نص عربي"}))
        assert "نص عربي" in line


# ═══ protocol: التحليل fail-closed ═══

class TestParseLine:
    def test_request(self):
        msg = parse_line('{"jsonrpc":"2.0","id":5,"method":"fs/read_text_file","params":{"path":"a.py"}}')
        assert isinstance(msg, Request)
        assert msg.id == 5 and msg.method == "fs/read_text_file"
        assert msg.params == {"path": "a.py"}

    def test_notification(self):
        msg = parse_line('{"jsonrpc":"2.0","method":"session/update","params":{}}')
        assert isinstance(msg, Notification)

    def test_response(self):
        msg = parse_line('{"jsonrpc":"2.0","id":1,"result":null}')
        assert isinstance(msg, Response)
        assert msg.result is None

    def test_error_response(self):
        msg = parse_line('{"jsonrpc":"2.0","id":1,"error":{"code":-32601,"message":"nope"}}')
        assert isinstance(msg, ErrorResponse)
        assert msg.code == METHOD_NOT_FOUND

    @pytest.mark.parametrize("bad", [
        "",                                        # فارغ
        "   ",                                     # مسافات
        "not json at all",                         # ضجيج banner
        "[1,2,3]",                                 # ليس dict
        '"string"',                                # JSON نصي
        '{"id":1,"method":"m"}',                   # بلا jsonrpc
        '{"jsonrpc":"1.0","id":1,"method":"m"}',   # نسخة خاطئة
        '{"jsonrpc":"2.0","id":1}',                # لا method/result/error
        '{"jsonrpc":"2.0","method":""}',           # method فارغ
        '{"jsonrpc":"2.0","method":123}',          # method ليس نصًا
        '{"jsonrpc":"2.0","id":1,"method":"m","params":[1]}',  # positional
        '{"jsonrpc":"2.0","id":true,"method":"m"}',            # id=bool
        '{"jsonrpc":"2.0","id":1.5,"result":1}',               # id=float
        '{"jsonrpc":"2.0","id":1,"error":"x"}',    # error ليس dict
        '{"jsonrpc":"2.0","id":1,"error":{"message":"x"}}',    # بلا code
    ])
    def test_malformed_returns_none(self, bad):
        assert parse_line(bad) is None

    def test_never_raises_on_garbage_bytes_text(self):
        # ضجيج شبيه بسجلات وكيل حقيقي — لا انهيار
        for noise in ("INFO: starting agent…", "\x00\x01", "{" * 500):
            assert parse_line(noise) is None


# ═══ connection: FakeTransport (القرار الواعي 5 — صفر subprocess) ═══

class FakeTransport:
    """زوج طوابير: ما يقرؤه العميل نضعه في incoming؛ ما يكتبه نلتقطه."""

    def __init__(self):
        self.incoming: queue.Queue[str | None] = queue.Queue()
        self.sent: list[str] = []
        self._lock = threading.Lock()

    def read_line(self):
        return self.incoming.get()

    def write_line(self, line: str) -> None:
        with self._lock:
            self.sent.append(line)

    # مساعدات اختبار
    def feed(self, line: str) -> None:
        self.incoming.put(line)

    def feed_eof(self) -> None:
        self.incoming.put(None)

    def sent_objs(self) -> list[dict]:
        with self._lock:
            return [json.loads(x) for x in self.sent]


@pytest.fixture()
def wired():
    """اتصال فوق FakeTransport مع خيط ضخ يُنظَّف تلقائيًا."""
    transport = FakeTransport()
    notes: list[Notification] = []
    conn = AcpConnection(transport,
                         on_notification=notes.append,
                         timeout_seconds=5.0)
    pump = threading.Thread(target=conn.pump_forever, daemon=True)
    pump.start()
    yield transport, conn, notes
    transport.feed_eof()
    pump.join(timeout=5.0)
    assert not pump.is_alive()


class TestConnectionRoundTrip:
    def test_request_gets_matching_response(self, wired):
        transport, conn, _ = wired
        result_box = {}

        def respond():
            # ننتظر خروج الطلب ثم نرد بنفس الـ id
            while not transport.sent:
                pass
            req = json.loads(transport.sent[0])
            transport.feed(json.dumps({"jsonrpc": "2.0", "id": req["id"],
                                       "result": {"ok": 1}}))
        t = threading.Thread(target=respond, daemon=True)
        t.start()
        result_box["r"] = conn.request("initialize", {"v": 1})
        t.join(timeout=5.0)
        assert result_box["r"] == {"ok": 1}

    def test_out_of_order_responses_resolve_correct_waiters(self, wired):
        transport, conn, _ = wired
        results: dict[str, object] = {}
        barrier = threading.Barrier(3)

        def call(name, method):
            barrier.wait(timeout=5.0)
            results[name] = conn.request(method)

        t1 = threading.Thread(target=call, args=("a", "m/one"), daemon=True)
        t2 = threading.Thread(target=call, args=("b", "m/two"), daemon=True)
        t1.start(); t2.start()
        barrier.wait(timeout=5.0)
        # ننتظر خروج الطلبين ثم نرد **بعكس** الترتيب
        while len(transport.sent) < 2:
            pass
        reqs = transport.sent_objs()
        by_method = {r["method"]: r["id"] for r in reqs}
        transport.feed(json.dumps({"jsonrpc": "2.0",
                                   "id": by_method["m/two"], "result": "R2"}))
        transport.feed(json.dumps({"jsonrpc": "2.0",
                                   "id": by_method["m/one"], "result": "R1"}))
        t1.join(timeout=5.0); t2.join(timeout=5.0)
        assert results == {"a": "R1", "b": "R2"}

    def test_notifications_interleaved_with_response(self, wired):
        transport, conn, notes = wired

        def respond():
            while not transport.sent:
                pass
            req = json.loads(transport.sent[0])
            transport.feed(json.dumps({"jsonrpc": "2.0", "method":
                                       "session/update",
                                       "params": {"chunk": "a"}}))
            transport.feed(json.dumps({"jsonrpc": "2.0", "id": req["id"],
                                       "result": "done"}))
        threading.Thread(target=respond, daemon=True).start()
        assert conn.request("session/prompt") == "done"
        # الإشعار وصل للمعالج ولم يعطّل مطابقة الرد
        assert any(n.params.get("chunk") == "a" for n in notes)

    def test_garbage_lines_ignored_pump_continues(self, wired):
        transport, conn, _ = wired
        transport.feed("Starting agent v1.2.3…")   # banner
        transport.feed("{broken json")

        def respond():
            while not transport.sent:
                pass
            req = json.loads(transport.sent[0])
            transport.feed(json.dumps({"jsonrpc": "2.0", "id": req["id"],
                                       "result": 42}))
        threading.Thread(target=respond, daemon=True).start()
        assert conn.request("ping") == 42

    def test_error_response_raises_protocol_error(self, wired):
        transport, conn, _ = wired

        def respond():
            while not transport.sent:
                pass
            req = json.loads(transport.sent[0])
            transport.feed(json.dumps({
                "jsonrpc": "2.0", "id": req["id"],
                "error": {"code": ERR_PATH_FORBIDDEN,
                          "message": "مسار محظور"}}))
        threading.Thread(target=respond, daemon=True).start()
        with pytest.raises(AcpProtocolError) as ei:
            conn.request("fs/read_text_file", {"path": "x"})
        assert ei.value.code == ERR_PATH_FORBIDDEN


class TestConnectionFailClosed:
    def test_timeout_raises(self):
        transport = FakeTransport()
        conn = AcpConnection(transport, timeout_seconds=0.05)
        pump = threading.Thread(target=conn.pump_forever, daemon=True)
        pump.start()
        with pytest.raises(AcpTimeoutError):
            conn.request("never/answered")
        transport.feed_eof()
        pump.join(timeout=5.0)

    def test_eof_wakes_pending_waiters(self):
        transport = FakeTransport()
        conn = AcpConnection(transport, timeout_seconds=30.0)
        pump = threading.Thread(target=conn.pump_forever, daemon=True)
        pump.start()
        errs: list[Exception] = []

        def call():
            try:
                conn.request("m")
            except Exception as exc:   # noqa: BLE001 — نلتقط للتحقق
                errs.append(exc)
        t = threading.Thread(target=call, daemon=True)
        t.start()
        while not transport.sent:      # الطلب خرج والخيط منتظر
            pass
        transport.feed_eof()           # موت العملية
        t.join(timeout=5.0)
        assert not t.is_alive()
        assert len(errs) == 1 and isinstance(errs[0], AcpConnectionClosed)
        assert conn.closed

    def test_request_after_close_raises(self):
        transport = FakeTransport()
        conn = AcpConnection(transport)
        conn.close()
        with pytest.raises(AcpConnectionClosed):
            conn.request("m")

    def test_stale_response_id_ignored(self, wired):
        transport, conn, _ = wired
        # رد لطلب لا وجود له — يُتجاهَل بلا انهيار، والضخ يستمر
        transport.feed(json.dumps({"jsonrpc": "2.0", "id": 999,
                                   "result": "stale"}))

        def respond():
            while not transport.sent:
                pass
            req = json.loads(transport.sent[0])
            transport.feed(json.dumps({"jsonrpc": "2.0", "id": req["id"],
                                       "result": "fresh"}))
        threading.Thread(target=respond, daemon=True).start()
        assert conn.request("m") == "fresh"


class TestIncomingRequestHandling:
    """طلبات عكسية من الوكيل (fs/*, request_permission) — أساس 736b."""

    def _conn(self, handler):
        transport = FakeTransport()
        conn = AcpConnection(transport, on_request=handler)
        return transport, conn

    def test_handler_result_sent_as_response(self):
        transport, conn = self._conn(lambda req: {"content": "hi"})
        transport.feed(json.dumps({"jsonrpc": "2.0", "id": 7,
                                   "method": "fs/read_text_file",
                                   "params": {"path": "a.py"}}))
        transport.feed_eof()
        conn.pump_forever()
        objs = transport.sent_objs()
        assert objs == [{"jsonrpc": "2.0", "id": 7,
                         "result": {"content": "hi"}}]

    def test_handler_protocol_error_sent_with_its_code(self):
        def deny(req):
            raise AcpProtocolError(ERR_PATH_FORBIDDEN, "مسار محظور")
        transport, conn = self._conn(deny)
        transport.feed(json.dumps({"jsonrpc": "2.0", "id": 8,
                                   "method": "fs/read_text_file",
                                   "params": {"path": "/etc/passwd"}}))
        transport.feed_eof()
        conn.pump_forever()
        err = transport.sent_objs()[0]["error"]
        assert err["code"] == ERR_PATH_FORBIDDEN

    def test_handler_crash_no_detail_leak(self):
        secret = "sk-CANARY-736-do-not-echo"

        def boom(req):
            raise RuntimeError(f"leak? {secret}")
        transport, conn = self._conn(boom)
        transport.feed(json.dumps({"jsonrpc": "2.0", "id": 9,
                                   "method": "m", "params": {}}))
        transport.feed_eof()
        conn.pump_forever()
        raw = transport.sent[0]
        obj = json.loads(raw)
        assert obj["error"]["code"] == INTERNAL_ERROR
        # الكناري غائب: الرسالة = اسم النوع فقط (عقد عدم-الترديد)
        assert secret not in raw
        assert obj["error"]["message"] == "RuntimeError"

    def test_no_handler_returns_method_not_found(self):
        transport = FakeTransport()
        conn = AcpConnection(transport)
        transport.feed(json.dumps({"jsonrpc": "2.0", "id": 3,
                                   "method": "fs/write_text_file",
                                   "params": {}}))
        transport.feed_eof()
        conn.pump_forever()
        assert transport.sent_objs()[0]["error"]["code"] == METHOD_NOT_FOUND

    def test_notification_handler_crash_does_not_stop_pump(self):
        transport = FakeTransport()

        def bad_note(note):
            raise ValueError("boom")
        conn = AcpConnection(transport, on_notification=bad_note)
        transport.feed(json.dumps({"jsonrpc": "2.0",
                                   "method": "session/update",
                                   "params": {}}))
        transport.feed(json.dumps({"jsonrpc": "2.0",
                                   "method": "session/update",
                                   "params": {}}))
        transport.feed_eof()
        conn.pump_forever()      # لا يرفع — وصل EOF بعد معالجة الاثنين
        assert conn.closed
