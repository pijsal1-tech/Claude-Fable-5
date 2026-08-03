---
description: بروتوكول كتابة refresh.py لأي Provider
globs: "**/refresh.py"
---
# 🔄 Skill — كتابة refresh.py

> **قاعدة ثابتة:** كل `refresh.py` لازم تكون signature بتاعته موحدة:
> `def refresh(email: str) -> bool:`

## البرومبت — ابعته لما تحتاج refresh.py:

```
عايز أكتب refresh.py لـ [اسم الـ Provider].

📋 البيانات:
- Provider: [اسم]
- Auth type: [JWT / Cookie / API Key]
- الـ accounts موجودة في: [مسار accounts.json]
- طريقة التجديد المحتملة: [token refresh endpoint؟ re-login؟]

🎯 المطلوب — 3 Layers بالترتيب:
1. Layer 0: تحقق من صلاحية الـ token الحالي (بدون login)
2. Layer 1: requests login (~سريع)
3. Layer 2: browser fallback (~بطيء، آخر حل)

⛔ القيود:
- Signature إلزامية: `def refresh(email: str) -> bool`
- لازم تحدث `accounts.json` + `last_updated` بعد التجديد
- Atomic write إلزامي
- مفيش hardcoded credentials
```

## Template القياسي:

```python
def refresh(email: str) -> bool:
    """يجدد credentials ويحدث accounts.json + last_updated"""
    accounts = load_accounts()
    acc = next((a for a in accounts if a["email"] == email), None)
    if not acc:
        return False

    # Layer 0: هل الـ token لسه شغال؟
    if _is_token_valid(acc):
        return True

    # Layer 1: requests re-login
    result = _requests_refresh(acc)
    if result:
        acc.update(result)
        acc["last_updated"] = datetime.now().isoformat()
        atomic_save(accounts)
        return True

    # Layer 2: browser fallback
    return _browser_fallback(acc, accounts)
```
