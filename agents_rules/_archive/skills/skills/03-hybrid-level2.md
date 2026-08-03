# 🧠 Level 2 — Hybrid Mode (في Cloudflare/hCaptcha)

> **المبدأ:** Browser مرة واحدة للـ tokens → curl_cffi يكمل الباقي (100x أسرع)

## البرومبت:

```
في Cloudflare. المسار: Hybrid Level 2.

📋 Provider: [اسم]
WAF: [Cloudflare / Turnstile / hCaptcha]
Tokens المطلوبة من البراوزر: [cf_clearance؟ CSRF؟]

🎯 المطلوب:
1. SeleniumBase (uc=True) → يفتح مرة واحدة → يجمع الـ tokens بس → يقفل
2. curl_cffi → يكمل كل الـ register بالـ tokens دي

⛔ قواعد إلزامية:
- uc=True إلزامي في SeleniumBase
- استخدم uc_open عادي + sleep(8) (مش uc_open_with_reconnect!)
- WAF_REUSE_LIMIT = 5 (تفتح البراوزر كل 5 accounts)
- مفيش Selenium في الـ register نفسه
```

## Template جاهز:

```python
from seleniumbase import SB
from curl_cffi import requests as cffi
import time

WAF_REUSE_LIMIT = 5  # إعادة فتح المتصفح كل N accounts

def get_browser_tokens(site_url: str) -> dict:
    """يفتح البراوزر مرة واحدة → يجمع الـ tokens → يقفل"""
    with SB(uc=True, headless=False) as sb:
        sb.uc_open(site_url)          # مش uc_open_with_reconnect!
        time.sleep(8)                  # انتظر Cloudflare يخلص
        cookies = {c["name"]: c["value"] for c in sb.get_cookies()}
        csrf = sb.execute_script(
            "return document.querySelector('meta[name=csrf-token]')?.content"
        ) or ""
        return {"cookies": cookies, "csrf": csrf}

def register_with_tokens(tokens: dict, email: str, password: str) -> dict | None:
    """كل الـ register بـ requests — البراوزر عمله شغله وراح"""
    session = cffi.Session(impersonate="chrome124")
    session.cookies.update(tokens["cookies"])
    session.headers["x-csrf-token"] = tokens["csrf"]

    try:
        r1 = session.post("https://SITE.com/api/register",
            json={"email": email, "password": password}, timeout=30)
        r1.raise_for_status()
        # ... باقي الـ steps هنا كلها requests ⚡
        return {"email": email, "status": "active", ...}
    except Exception as e:
        print(f"❌ فشل: {e}")
        return None

# الحلقة الرئيسية مع WAF reuse
tokens = None
success_count = 0

for email in email_list:
    if tokens is None or success_count >= WAF_REUSE_LIMIT:
        tokens = get_browser_tokens("https://SITE.com")
        success_count = 0

    result = register_with_tokens(tokens, email, password)
    if result:
        success_count += 1
```

## متى تستخدم CDP للـ React buttons؟

```python
# لما sb.click() مش بيشتغل مع React/Next.js
def cdp_click(sb, text: str):
    """CDP = الوحيد اللي بيشتغل مع React — main world + userGesture=True"""
    sb.driver.execute_cdp_cmd("Runtime.evaluate", {
        "expression": f"""
            (function() {{
                const btn = Array.from(document.querySelectorAll('button'))
                    .find(el => el.innerText.includes('{text}'));
                if (!btn) return false;
                btn.scrollIntoView({{behavior:'instant', block:'center'}});
                btn.click();
                return true;
            }})()
        """,
        "returnByValue": True,
        "awaitPromise": False,
        "userGesture": True,   # ← السر! Chrome بيعامله كـ user gesture
    })
