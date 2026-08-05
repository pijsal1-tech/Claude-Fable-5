# -*- coding: utf-8 -*-
"""وكيل ACP دمية محلي — TSK-736c (القرار 8 من تسلسل D-19).

سكربت بايثون محلي خالص (لا تنزيل، لا شبكة — القرار الواعي 5):
يتكلم JSON-RPC 2.0 بأسطر فوق stdio ويكفي لاختبار التكامل الوحيد
المسموح له subprocess حقيقي:

- ``initialize`` → ``{"protocolVersion": 1, "agent": "echo"}``.
- ``session/new`` → ``{"sessionId": "echo-1"}``.
- ``session/prompt``:
  * نص يبدأ بـ ``READ:<path>`` ⇒ يصدر طلبًا عكسيًا
    ``fs/read_text_file`` ويعيد ``READ_OK:<content>`` أو
    ``READ_DENIED:<code>`` — يثبت أن denylist الأسرار تصل الوكيل
    كرفض لا كمحتوى (كناري).
  * نص يبدأ بـ ``WRITE:<path>:<content>`` ⇒ طلب عكسي
    ``fs/write_text_file`` ويعيد ``WRITE_OK`` أو
    ``WRITE_DENIED:<code>`` — يثبت «لا موافقة ⇒ لا كتابة».
  * غير ذلك ⇒ يبث إشعار ``session/update`` ثم يعيد ``ECHO:<نص>``.
"""
import json
import sys

_counter = [0]


def _send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _reverse(method, params):
    """طلب عكسي للعميل — ينتظر الرد المطابق للمعرّف على stdin."""
    _counter[0] += 1
    rid = "agent-%d" % _counter[0]
    _send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if msg.get("id") == rid and "method" not in msg:
            return msg
    return {}


def _prompt_text(params):
    text = ""
    for block in (params or {}).get("prompt") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            text += str(block.get("text", ""))
    return text


def _handle_prompt(mid, params):
    text = _prompt_text(params)
    if text.startswith("READ:"):
        resp = _reverse("fs/read_text_file", {"path": text[len("READ:"):]})
        if "error" in resp:
            out = "READ_DENIED:%s" % resp["error"].get("code")
        else:
            out = "READ_OK:%s" % (resp.get("result") or {}).get("content", "")
    elif text.startswith("WRITE:"):
        _, path, content = text.split(":", 2)
        resp = _reverse("fs/write_text_file",
                        {"path": path, "content": content})
        if "error" in resp:
            out = "WRITE_DENIED:%s" % resp["error"].get("code")
        else:
            out = "WRITE_OK"
    else:
        _send({"jsonrpc": "2.0", "method": "session/update",
               "params": {"sessionId": "echo-1", "kind": "progress",
                          "text": "echoing"}})
        out = "ECHO:%s" % text
    _send({"jsonrpc": "2.0", "id": mid,
           "result": {"stopReason": "end_turn", "text": out}})


def main():
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        method = msg.get("method")
        mid = msg.get("id")
        if method == "initialize":
            _send({"jsonrpc": "2.0", "id": mid,
                   "result": {"protocolVersion": 1, "agent": "echo"}})
        elif method == "session/new":
            _send({"jsonrpc": "2.0", "id": mid,
                   "result": {"sessionId": "echo-1"}})
        elif method == "session/prompt":
            _handle_prompt(mid, msg.get("params"))
        elif mid is not None:
            _send({"jsonrpc": "2.0", "id": mid,
                   "error": {"code": -32601, "message": "unknown"}})


if __name__ == "__main__":
    main()
