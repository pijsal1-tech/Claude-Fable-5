# 🔥 Debug: Perplexity — Mobile Android API (3 مشاكل)

> **مهم:** Perplexity بيستخدم **Mobile Android API مش Web API!**
> كل الـ headers لازم تكون Android SDK headers.

## 🗺️ خريطة الـ Flow:
```
Mail.tm → email
  ↓ POST /api/auth/signin-email {email, useNumericOtp: "true"}
  ↓ poll inbox → OTP 6 أرقام
  ↓ POST /api/auth/signin-otp {email, otp} → Bearer token
  ↓ GET /rest/auth/refresh_perplexity_jwt → perplexity_jwt
```

## المشاكل الـ 3:

| # | المشكلة | الخطأ | الحل |
|---|---------|-------|------|
| 1 | Cloudflare بيبلوك | 403 Forbidden | `curl_cffi` + `impersonate="chrome124"` |
| 2 | Headers غلط | 401 / 400 | Android Mobile headers إلزامية |
| 3 | OTP format | parse error | OTP = 6 أرقام بس — strip spaces |

## Android Headers الإلزامية:

```python
PERPLEXITY_HEADERS = {
    "user-agent": "okhttp/4.12.0",
    "x-client-name": "perplexity-android",
    "x-client-version": "1.0.0",
    "accept-encoding": "gzip",
    "content-type": "application/json",
}

from curl_cffi import requests as cffi

# ✅ Cloudflare bypass
resp = cffi.post(
    "https://www.perplexity.ai/api/auth/signin-email",
    data={"email": email, "useNumericOtp": "true"},
    headers=PERPLEXITY_HEADERS,
    impersonate="chrome124",
    timeout=30,
)
```

## البرومبت للـ debug:

```
عندي مشكلة في Provider بيستخدم Mobile API.

الخطأ: [الـ error]
الـ Headers الحالية: [قائمة headers]

اقرأ `.agents/skills/10-debug-perplexity.md`
وحدد إيه الـ headers الناقصة وادي الحل.
```
