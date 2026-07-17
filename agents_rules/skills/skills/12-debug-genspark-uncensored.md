# 🔥 Debug: Genspark + Uncensored.ai

---

## 🟢 Genspark — Azure AD B2C (3 قواعد)

### القاعدة #1: `cookies.jar` مش شغال مع curl_cffi

```python
# ❌ غلط — مش هيشتغل مع curl_cffi
cookies = {c.name: c.value for c in sess.cookies.jar}

# ✅ صح — universal لـ requests و curl_cffi
cookies = dict(sess.cookies)
```

> **📌** `dict(sess.cookies)` = **universal** — الـ bug صامت بيرجع dict فاضي!

### القاعدة #2: Turnstile Invisible = blocker لـ pure requests

| محاولة | نتيجة |
|--------|-------|
| ❌ cloudscraper | فشل |
| ❌ curl_cffi alone | فشل |
| ❌ Groq Vision | مش image captcha! |
| ✅ Capsolver ($2/1000) | شغال |
| ✅ browser حقيقي | شغال |

> **📌** لو email provider فيه Turnstile → شيله أو Capsolver/$2captcha

### القاعدة #3: DRY duplicate → grep أولاً!

```bash
# ✅ قبل حذف أي duplicate
grep -n "B2C_BASE" genspark_register.py
# L77: B2C_BASE = f"..."    ← 5 مراجع ← ابقيه!
# L91: B2C_BASE = f"..."    ← 0 مراجع ← امسحه!
```

> **📌** اختبر بعد كل حذف: `python -c "import ast; ast.parse(open('file.py').read())"`

---

## 🟣 Uncensored.ai — Clerk JWT (8 قواعد)

### 🗺️ خريطة الـ Flow:
```
Emailnator → Gmail alias
  ↓ [1/8] فتح /signup (SeleniumBase uc=True)
  ↓ [2/8] ملء الاسم + الإيميل + الباسورد
  ↓ [3/8] حل Turnstile (تلقائي بالمتصفح)
  ↓ [4/8] poll Emailnator → OTP 6 أرقام
  ↓ [5/8] إدخال OTP → verified
  ↓ [6/8] Clerk JWT من localStorage
  ↓ [7/8] حفظ في accounts_uncensored.json
  ↓ [8/8] refresh: Layer 0→1→2
```

### القاعدة #1: Clerk JWT = short-lived (~1 ساعة)

```python
SESSION_VALID_HRS = 20  # بيتحكم في متى نجدد

def _is_fresh(account: dict) -> bool:
    last = account.get("last_updated", "")
    if not last: return False
    dt = datetime.fromisoformat(last)
    if dt.tzinfo: dt = dt.replace(tzinfo=None)
    return (datetime.now() - dt).total_seconds() < SESSION_VALID_HRS * 3600
```

> **📌** اعتمد على `last_updated` + `SESSION_VALID_HRS` بدل decode JWT expiry.

### القاعدة #2: Clerk 422 = incomplete account

```python
# في monitor.py
"uncensored": {
    "skip_status": ["inactive", "banned", "❌", "layer1_failed"],
}

# في refresh.py
if resp.status_code == 422:
    account["status"] = "layer1_failed"
    return False
```

### القاعدة #3: Rate Limiting (429)

```python
CLERK_DELAY = 2  # ثانية إلزامية بين كل Clerk API call

for acc in accounts:
    result = refresh_layer1(acc)
    time.sleep(CLERK_DELAY)  # ← بدونه 429 حتمي!
```

### القاعدة #4: Turnstile = SeleniumBase uc=True فقط

```python
with SB(uc=True, headless=False) as sb:
    sb.uc_open("https://uncensored.ai/signup")
    # Turnstile بيتحل تلقائي مع uc=True
```

### القاعدة #5: مراجعة سطر بسطر مع golden reference
> مقارنة **سطر بسطر** مع `cohere_register.py` — مش surface review!

### القاعدة #6: `step(num, total, msg)` explicit

```python
# ❌ global counter هش
_step_n = 0
def step(msg): global _step_n; _step_n += 1; ...

# ✅ explicit + thread-safe
def step(num: int, total: int, msg: str): ...
```

### القاعدة #7: HTML `data-*` = dynamic params

```python
# ❌ غلط — code مش hash!
code = hashlib.sha384(email.encode()).hexdigest()

# ✅ صح — من HTML attribute
r = sess.get(BASE_URL)
m = re.search(r'data-code=["\']([0-9a-f]{32,})["\'\]', r.text)
code = m.group(1)
```

### القاعدة #8: Real browser credentials أولاً
> جرب بـ credentials حقيقية من البراوزر = يختصر ساعات debug!

---

## 🟢 Genspark SSE Parser (3 formats)

```python
# Genspark ask_proxy بيرجع SSE في 3 formats مختلفة!

for line in response.iter_lines():
    line = line.decode("utf-8", errors="replace").strip()
    if not line:
        continue

    # Format 1: field_name/field_value (Genspark native)
    if line.startswith("field_name:"):
        current_field = line.split(":", 1)[1].strip()
        continue
    if line.startswith("field_value:"):
        value = line.split(":", 1)[1].strip()
        if current_field == "content":
            print(value, end="", flush=True)
        continue

    # Format 2: OpenAI delta
    if line.startswith("data:"):
        data = line[5:].strip()
        if data == "[DONE]": break
        try:
            j = json.loads(data)
            chunk = j["choices"][0]["delta"].get("content", "")
            print(chunk, end="", flush=True)
        except: pass
        continue

    # Format 3: direct content
    print(line, end="", flush=True)
```

> **📌** parser لازم يدعم الـ 3 — Genspark بيبدل بينهم!

---

## 🟣 Uncensored Chat — WebSocket End Detection

```python
import websocket, json

ws = websocket.create_connection(WS_URL, header=headers)
ws.send(json.dumps({"message": prompt, "chat_id": chat_id}))

full_text = ""
while True:
    msg = ws.recv()
    data = json.loads(msg)

    # ❌ غلط: انتظار message_type: "done" (مبتتبعتش أصلاً!)
    # ✅ صح: رصد end_of_stream
    if data.get("end_of_stream"):
        full_text = data.get("raw_text", full_text)
        break

    chunk = data.get("content", "")
    print(chunk, end="", flush=True)
    full_text += chunk

ws.close()
```

> **📌** `end_of_stream: true` + `raw_text` = الطريقة الوحيدة لمعرفة إن الرد خلص!

