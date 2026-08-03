# 🔥 Debug: Mistral — Ory Kratos + Django CSRF (4 مشاكل)

> **استخدم الملف ده لأي Provider بيستخدم:** Ory Kratos / Django CSRF backend

## 🗺️ خريطة الـ Flow:
```
Mail.tm → email
  ↓ GET /self-service/registration/browser → flow_id + csrf_token
  ↓ POST /self-service/registration?flow={id} → session + verification_flow
  ↓ poll inbox → OTP 6 أرقام
  ↓ POST /self-service/verification?flow={id} → email verified
  ↓ GET admin.mistral.ai/ → csrftoken cookie (Django)
  ↓ POST /api/users/organizations → org uuid
  ↓ POST /api/users/verify-phone/send-code → SMS
```

## المشاكل الـ 4 بالخلاصة:

| # | المشكلة | الخطأ | الحل السريع |
|---|---------|-------|------------|
| 1 | Ory Kratos بيرجع HTML | `JSONDecodeError` | `Accept: application/json` إلزامي |
| 2 | CSRF 403 مع وجود Cookie | `{"detail": "CSRF check Failed"}` | لازم 4 حاجات: cookie + header + Referer + Origin |
| 3 | دومين غلط | 404/403 | HAR analysis أولاً — `admin.mistral.ai` مش `console` |
| 4 | رقم فون مرفوض | `"can't be verified"` | جرب رقم تاني / fallback input |

## 🔴 الكود المرجعي:

```python
# ✅ Ory Kratos (مشكلة #1)
session.headers["Accept"] = "application/json"   # إلزامي لكل endpoints
r = session.get(f"{AUTH_BASE}/self-service/registration/browser")
data = r.json()  # ✅ الآن بيرجع JSON

# ✅ Django CSRF كامل (مشكلة #2)
# أولاً: اجمع الـ csrftoken من GET request عادي
session.get(f"{CONSOLE_BASE}/join")  # بيسيت csrftoken cookie تلقائياً
csrftoken = session.cookies.get("csrftoken")

# ثانياً: ابعته في الـ POST مع 3 headers إضافيين
headers = {
    "x-csrftoken": csrftoken,                   # ← header
    "Content-Type": "application/json",
    "Referer": f"{CONSOLE_BASE}/join",           # ← إلزامي
    "Origin": CONSOLE_BASE,                      # ← إلزامي
}
# csrftoken cookie بتتبعت تلقائياً مع الـ session
```

## البرومبت للـ debug:

```
عندي مشكلة في Provider بيستخدم Ory Kratos أو Django CSRF.

الخطأ: [الـ error بالظبط]
الـ Endpoint: [الـ URL]
الـ Headers الحالية: [قائمة الـ headers]

اقرأ `.agents/skills/09-debug-mistral.md` وحدد أي مشكلة دي
وادي الحل المباشر.
```
