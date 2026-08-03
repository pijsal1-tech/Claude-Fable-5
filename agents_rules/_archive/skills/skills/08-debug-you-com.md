# 🔥 Debug: You.com — Descope + Next.js RSC (10 مشاكل)

> **استخدم الملف ده لأي Provider بيستخدم:** Descope / Next.js Server Actions / RSC

## 🗺️ خريطة الـ Flow:
```
Emailnator → email
  ↓ flow/start → executionId + stepId
  ↓ flow/next → OTP للإيميل
  ↓ wait OTP → Emailnator
  ↓ flow/next → DS + DSR cookies
  ↓ GET /platform/api-keys → تفعيل subscription
  ↓ POST /platform/api-keys → API Key
```

## المشاكل الـ 10 بالخلاصة:

| # | المشكلة | الخطأ | الحل السريع |
|---|---------|-------|------------|
| 1 | Emailnator بطيء | `ReadTimeout` | timeout=30s + retry 3x |
| 2 | flow/start → 404 | Missing headers | ضيف 5 `x-descope-*` headers |
| 3 | stepId ناقص | `KeyError: screen` | `stepId` في ROOT مش nested |
| 4 | flow/next → 400 | Missing fields | `interactionId` + `componentsVersion` + `isCustomScreen` |
| 5 | OTP 400 | Wrong interactionId | `interactionId` = HTML element id |
| 6 | Tokens مش موجودة | بيدور في مكان غلط | Check 3 أماكن: authInfo / response cookies / session cookies |
| 7 | API key response 50K chars | `JSONDecodeError` | RSC مش JSON — استخدم regex |
| 8 | "No subscription found" | POST فاشل | GET الصفحة أولاً ثم POST |
| 9 | next-action hash بيتغير | build-specific | auto-discover من JS chunks |
| 10 | Server Action 400 | JSON بدل multipart | `multipart/form-data` + `accept: text/x-component` |

## 🔴 الكود المرجعي للمشاكل الأكثر شيوعاً:

```python
# ✅ Descope Headers الإلزامية (مشكلة #2)
session.headers.update({
    "Authorization": f"Bearer {PROJECT_ID}",
    "x-descope-project-id": PROJECT_ID,
    "x-descope-sdk-name": "nextjs",
    "x-descope-sdk-version": "0.15.12",
    "x-descope-sdk-session-id": sdk_session_id,
})

# ✅ flow/next body الصحيح (مشكلة #4)
body = {
    "executionId": exec_id, "stepId": step_id,
    "interactionId": "S-VOZ5i7gc",     # من HTML
    "componentsVersion": "2.3.1",
    "input": {"email": email},
    "isCustomScreen": False,
}

# ✅ RSC parsing (مشكلة #7)
import re
key_match = re.search(
    r'"success"\s*:\s*true\s*,\s*"data"\s*:\s*\{[^}]*"key"\s*:\s*"(ydc-sk-[^"]+)"',
    response.text,
)

# ✅ Descope Tokens الـ 3 أماكن (مشكلة #6)
ds = (data.get("authInfo", {}).get("sessionJwt") or
      response.cookies.get("DS") or
      session.cookies.get("DS", ""))
```

## البرومبت للـ debug:

```
عندي مشكلة في Provider بيستخدم Descope/Next.js.

الخطأ: [الـ error message بالظبط]
الـ Step: [رقم الخطوة في الـ Flow]
الكود: [الكود المشكوك فيه]

اقرأ `.agents/skills/08-debug-you-com.md` وحدد:
أي من الـ 10 مشاكل دي قريبة من مشكلتي؟
```
