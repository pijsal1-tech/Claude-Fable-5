---
description: بناء AI Provider بـ Hybrid (Cloudflare bypass + Requests)
globs: "**/*.py"
---
# 🧠 Provider — Hybrid Mode (Level 2)

> **متى الـ Hybrid؟** لما في Cloudflare/hCaptcha بس في API endpoints.
> المبدأ: Browser مرة واحدة للتوكنات → Requests تكمل الباقي (أسرع 100x)

## البرومبت:

```
في Cloudflare على الموقع. المطلوب Hybrid Pattern:

📋 البيانات:
- Provider: [اسم]
- WAF: Cloudflare / hCaptcha / Turnstile
- الـ tokens المطلوبة من البراوزر: [cf_clearance؟ CSRF؟]

🎯 المطلوب:
1. Step 1: SeleniumBase `uc=True` → bypass WAF → يجمع الـ tokens بس
2. Step 2: Session curl_cffi → يكمل كل الـ register بـ الـ tokens دي
3. مفيش Selenium في الـ register نفسه — البراوزر مرة واحدة بس!

⛔ القيود:
- `uc=True` إلزامي في SeleniumBase
- مفيش `uc_open_with_reconnect` — استخدم `uc_open` + `sleep(8)` بدله
- WAF_REUSE_LIMIT = 5 (إعادة فتح البراوزر كل 5 accounts)
```

## Template الكود:

```python
from seleniumbase import SB
from curl_cffi import requests as cffi

def get_browser_tokens(site_url: str) -> dict:
    """يفتح البراوزر مرة واحدة → يجمع الـ tokens → يقفل"""
    with SB(uc=True, headless=False) as sb:
        sb.uc_open(site_url)
        import time; time.sleep(8)  # انتظر Cloudflare يخلص
        cookies = {c["name"]: c["value"] for c in sb.get_cookies()}
        csrf = sb.execute_script(
            "return document.querySelector('meta[name=csrf-token]')?.content"
        ) or ""
        return {"cookies": cookies, "csrf": csrf}

# الـ register كله بـ requests بعد كده
tokens = get_browser_tokens("https://SITE.com")
session = cffi.Session(impersonate="chrome124")
session.cookies.update(tokens["cookies"])
session.headers["x-csrf-token"] = tokens["csrf"]

# كل الـ steps هنا بـ requests فقط! ⚡
```
