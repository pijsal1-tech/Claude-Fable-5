# 🔴 Debug: Cursor AI — WorkOS + Cloudflare Turnstile

---

## Auth Flow المصحح (v2):
```
GET /sign-up → 307 → /bootstrap → 307 → /sign-up?client_id=...&state=...
  ↓
POST /sign-up (RSC multipart):
  إدخال Name + Email → ضغط Continue
  ↓
POST Continue with email code (CDP Click / JS)
  يضغط على الزرار بدل الباسورد (مفيش باسورد في الفلو ده)
  ↓
POST /magic-code (RSC multipart):
  يدخل 6 أرقام وصلوا في الإيميل (Subject: Sign in to Cursor, From: reply@cursor.sh)
  → 303
  ↓
POST /radar-challenge/send (multipart):
  يطلب رقم هاتف → بيتم إدخال الرقم والـ SMS يدوياً
```

## التقنيات:
| العنصر | القيمة |
|--------|--------|
| **Auth** | WorkOS |
| **client_id** | `client_01GS6W3C96KW4WRS6Z93JCE2RJ` |
| **Protection** | Cloudflare Turnstile (`bot_detection_token`) |
| **Format** | Next.js RSC (`text/x-component`) + `multipart/form-data` |
| **Verify** | OTP 6 أرقام + 📞 Phone |
| **Level** | Level 2: Hybrid (SeleniumBase `uc=True`) |

---

## القواعد:

| # | القاعدة | أهمية |
|---|---------|-------|
| 1 | `uc=True` لتخطي Cloudflare — `uc_open` + `sleep(8)` | 🔴 |
| 2 | Oonetimemail (stuurmy.app) يحتاج فتح المتصفح لحل Turnstile | 🔴 |
| 3 | مفيش Password — الفلو بيستخدم زر "Continue with email code" | 🔴 |
| 4 | React type: `_react_type` (nativeSetter + input+change events) إلزامي | 🔴 |
| 5 | زر الـ Continue with email code مخفي في الـ DOM، بيحتاج CDP/JS للكليك | 🟡 |
| 6 | Phone SMS — حالياً يتم إدخاله يدوياً في الترمنال `input()` | 🔴 |

---

## Selectors:
```python
# ─── Cursor Selectors (v2) ───
SEL_FIRST_NAME = "input[name='first_name'], input[placeholder*='First']"
SEL_LAST_NAME  = "input[name='last_name'], input[placeholder*='Last']"
SEL_EMAIL      = "input[name='email'], input[type='email']"
SEL_SUBMIT     = "button[type='submit']"
SEL_OTP_INPUT  = "input[name='code'], input[type='text'][maxlength='6']"
```

---

## المشاكل المحتملة:

| المشكلة | الحل |
|---------|------|
| Cloudflare block | `uc=True` + `sleep(8)` + browser مفتوح |
| Turnstile مش بيتحل | استنى أكتر (10-15s) أو أعد المتصفح |
| OTP مش بيوصل | جرب email provider تاني (`--provider mailtm`) |
| Phone verification | لسه مفيش SMS service — الحساب يتسجل `pending_phone` |
| Selectors اتغيرت | افحص DevTools (F12) وحدث الـ `SEL_*` constants |
