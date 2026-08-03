# 📥 Input Formats + القواعد الإلزامية

> **📌 الملف ده بيوصف إزاي تبعت بيانات Provider للـ AI + القواعد الإلزامية لكل سكريبت.**

---

## 📥 شكل المدخلات — 3 أشكال

### الشكل 1 — Curls (الأحسن ✅)
```
Provider: NewAI
URL: https://newai.com
Temp email: emailnator
Verification: code (6 digits)

# Step 1: Register
curl 'https://newai.com/api/auth/register' \
  -H 'content-type: application/json' \
  -H 'origin: https://newai.com' \
  -d '{"email":"test@test.com","password":"pass123"}'
# Response: {"user_id": "xxx", "session_token": "yyy"}

# Step 2: Verify email
curl 'https://newai.com/api/auth/verify' \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer {{session_token}}' \
  -d '{"code":"123456"}'
# Response: {"access_token": "zzz", "refresh_token": "www"}
```

### الشكل 2 — عناصر (لو مفيش curls)
```
Provider: NewAI
URL: https://newai.com/signup
Temp email: emailnator
Verification: link

Email input: input[type="email"]
Password: input[name="password"]
Submit: button[type="submit"]
Success: .user-avatar
```

### الشكل 3 — هجين (Cloudflare + API)
```
Provider: NewAI
URL: https://newai.com
Temp email: emailnator
Verification: code

# الموقع فيه Cloudflare — لازم متصفح يعدي الحمايه الأول
# بعد ما يعدي، خد الكوكيز وكمّل requests

curl 'https://newai.com/api/register' \
  -H 'cookie: cf_clearance={{cf_clearance}}' \
  -H 'content-type: application/json' \
  -d '{"email":"{{email}}","password":"{{password}}"}'
```

---

## ⛔ القواعد الإلزامية (Non-Negotiable)

### 1. refresh.py — Signature ثابت
```python
def refresh(email: str) -> bool:
    """يجدد credentials ويحدث accounts.json + last_updated"""
```

### 2. accounts.json — حقول إلزامية
```json
{
  "email": "...",
  "provider": "mailtm",
  "api_key": "...",
  "status": "active",
  "last_updated": "...",
  "expires_in": 24,
  "email_creds": {
    "password_mailtm": "...",
    "token_mailtm": "...",
    "account_id_mailtm": "..."
  }
}
```
> **⚠️ `provider` = auto-detect:** `gmail.com`→`"emailnator"` | `ridermail.shop`→`"dropmailx"` | باقي→`"mailtm"`
>
> **🔴 `email_creds` إلزامي لـ Mail.tm بس!** Keys suffixed دايماً.

### 3. Dynamic Token Chaining ⚡
```python
resp1 = session.post("/register", json={...})
token = resp1.json()["session_token"]  # ← ديناميك!

resp2 = session.post("/verify",
    headers={"Authorization": f"Bearer {token}"},
    json={...}
)
```

### 4. Atomic Write
```python
tmp = filepath.with_suffix(".tmp")
json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
pathlib.Path(tmp).replace(filepath)
```

### 5. مفيش Hardcoded keys — كلها Config أو `.env`
### 6. UTF-8 fix: `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`
### 7. `uc=True` لو استخدمت Selenium

---

## 📐 إعدادات افتراضية

| الإعداد | القيمة |
|---------|--------|
| `headless` | `false` |
| `timeout` | `20s` |
| `default_password` | `"A9!k@e3#Qz1$Lp"` |
| `delay_between` | `5-15s` random |
| `expires_in` | `24h` |
| `max_accounts` | `0` (unlimited) |
| `session_format` | `full` |

---

## 🚨 قاعدة التوثيق اللحظي

> **⛔ بعد ما تحل أي مشكلة → ضيف قاعدة في `15-live-rules-full.md` فوراً!**

| الموقف | الإجراء |
|--------|---------|
| ✅ حليت مشكلة | ضيف قاعدة |
| ✅ اكتشفت pattern | ضيف في `04-code-patterns.md` |
| ✅ خلصت provider | حدث `07-after-task.md` |
| ✅ لقيت anti-pattern | ضيف في `13-anti-patterns.md` |
| ❌ لسه بتجرّب | **متضيفش** |

### الشكل:
```
| #رقم | القاعدة (جملة واحدة) | [Tag] | 🔴/🟡/🟢 | Provider |
```
