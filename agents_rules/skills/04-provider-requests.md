---
description: بناء AI Provider بـ Requests فقط (Level 1 - الأسرع والأنظف)
globs: "**/*.py"
---
# ⚡ Provider — Requests Only (Level 1)

> **القاعدة الذهبية:** كل حاجة ممكن تتعمل بـ HTTP requests = اعملها requests!

## البرومبت — ابعته بعد إنهاء الـ Checklist:

```
الـ Checklist جاهز. الآن:

📋 البيانات:
- Provider: [اسم الموقع]
- Auth: [Descope / Firebase / JWT / Magic Link]
- Email: [Emailnator / Mail.tm / TempMail]
- Verify: [OTP 6 / Magic Link / Email Link]

🎯 المطلوب (بالترتيب):
1. رسم Dependency Flow: كل Step → output → input للـ Step التالي
2. (بعد موافقتي) كتابة register.py بـ curl_cffi

⛔ القيود الإلزامية:
- curl_cffi مش requests عادي
- Session واحد يحافظ على الكوكيز طول العملية
- كل token يتاخد ديناميكياً من response السابق (مفيش hardcoded!)
- try/except لكل request مع logging واضح
- atomic write للـ accounts.json
- colorama + fallback للـ terminal output
```

## Template الكود القياسي:

```python
from curl_cffi import requests as cffi
import json
from pathlib import Path

session = cffi.Session(impersonate="chrome124")
session.headers.update({
    "user-agent": "Mozilla/5.0 ...",
    "accept": "application/json",
    "content-type": "application/json",
    "origin": "https://SITE.com",
})

# Step 1
resp1 = session.post("https://SITE.com/api/step1", json={...})
TOKEN = resp1.json()["token"]  # ← دايماً ديناميك من response

# Step 2 — يستخدم output الـ Step الأول
resp2 = session.post("https://SITE.com/api/step2",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={...}
)
```

## accounts.json — الشكل الإلزامي:
```json
{
  "email": "...",
  "password": "...",
  "provider": "mailtm",
  "status": "active",
  "last_updated": "2026-03-27T00:00:00",
  "expires_in": 24
}
```
