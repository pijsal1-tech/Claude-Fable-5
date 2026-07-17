# 🔥 Debug: DeepSeek — Pure Requests Client بدون Browser

> **قاعدة:** DeepSeek ممكن يشتغل بدون Browser بالكامل: Android headers + curl_cffi + WASM PoW

## 🗺️ خريطة الـ Flow:
```
Login → token
  ↓ PoW challenge → WASM solve → answer
  ↓ POST /chat/completion (SSE stream)
  ↓ response_message_id → parent for next turn
```

---

## المشكلة #1: WAF يمنع requests العادية 🔴

| البند | التفاصيل |
|-------|---------|
| **الخطأ** | `HTTP 403` أو redirect لـ Cloudflare |
| **السبب** | DeepSeek بيتحقق من TLS fingerprint + headers |
| **الحل** | Android mobile headers + `curl_cffi` impersonate `safari15_3` |

```python
from curl_cffi import requests

ANDROID_HEADERS = {
    "Host": "chat.deepseek.com",
    "User-Agent": "DeepSeek/1.0.13 Android/35",
    "x-client-platform": "android",
    "x-client-version": "1.3.0-auto-resume",
    "x-client-locale": "zh_CN",
    "Connection": "keep-alive",
}

session = requests.Session(impersonate="safari15_3")
session.headers.update(ANDROID_HEADERS)
```

> **📌 القاعدة:** DeepSeek WAF bypass = `safari15_3` + Android headers — مش Browser!

---

## المشكلة #2: PoW Challenge يمنع كل request 🔴

| البند | التفاصيل |
|-------|---------|
| **الخطأ** | Chat API بترفض request بدون PoW header |
| **السبب** | DeepSeek بيطلب SHA3/Keccak hash قبل كل رسالة |
| **الحل** | WASM module بـ wasmtime — يحل SHA3 في Python |

```python
from wasmtime import Store, Module, Linker

class PoWSolver:
    def __init__(self, wasm_path):
        self._store  = Store()
        self._linker = Linker(self._store.engine)
        self._module = Module(self._store.engine, open(wasm_path,"rb").read())

    def solve(self, challenge: dict) -> int:
        # ... حل SHA3 بدون browser
```

> **📌 القاعدة:** DeepSeek PoW = SHA3 WASM — يتحل بـ wasmtime Python بدون browser!

---

## المشكلة #3: SSE Stream بيرجع جزء من الرد 🔴

| البند | التفاصيل |
|-------|---------|
| **الخطأ** | الرد = كلمة واحدة أو جزء |
| **السبب** | أول chunk = full format `{"p","o","v"}`, باقيهم = shorthand `{"v":"text"}` |
| **الحل** | Parser يتعامل مع الاتنين |

```python
# أول chunk: {"p":"response/content","o":"APPEND","v":"text"}
# باقي chunks: {"v":"text"} بدون p

for chunk in stream:
    if "p" in chunk and chunk["p"] == "response/content":
        mode = "content"
    elif "v" in chunk:  # shorthand continuation
        if mode == "content": yield chunk["v"]
```

> **📌 القاعدة:** SSE JSON Patch = أول chunk فيه path `p`، باقيهم shorthand بدون `p`.

---

## المشكلة #4: Multi-turn لا يتذكر السياق 🔴

| البند | التفاصيل |
|-------|---------|
| **الخطأ** | Model ما بيتذكرش الرسايل السابقة |
| **السبب** | `parent_message_id` ما بيتبعتش |
| **الحل** | اقرأ `response_message_id` من SSE → ابعته كـ `parent_message_id` |

```python
# من SSE:
if "response_message_id" in chunk:
    self._last_msg_id = chunk["response_message_id"]

# في request التالي:
{"parent_message_id": self._last_msg_id, ...}
```

---

## ✅ جدول القواعد (6 قواعد)

| # | القاعدة | النوع |
|---|---------|-------|
| 1 | WAF = `safari15_3` + Android headers + curl_cffi | Network |
| 2 | PoW = SHA3 WASM بـ wasmtime — مش browser | Auth |
| 3 | SSE = أول chunk بـ `p`، باقيهم shorthand `{"v":"text"}` | Parsing |
| 4 | Multi-turn = `response_message_id` → `parent_message_id` | Multi-turn |
| 5 | refresh = curl_cffi + Android headers — `acc["token"]` = raw string | Refresh |
| 6 | Search Results بتندمج في الرد تلقائياً — مفيش SSE path منفصل | Search |
