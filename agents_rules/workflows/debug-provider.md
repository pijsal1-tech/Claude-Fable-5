---
description: خطوات تشخيص لما provider يفشل — debug + analyze + fix
---

# /debug-provider — تشخيص مشاكل Provider

> لما أي provider يفشل → اتبع الخطوات دي بالترتيب

// turbo-all

## الخطوة 1 — تحديد نوع المشكلة

```
إيه اللي بيحصل بالظبط؟

[1] Registration فشل
    A) مش بيفتح الموقع (Cloudflare / timeout)
    B) مش بيلاقي element (selector اتغير)
    C) OTP مش بيوصل (email provider مشكلة)
    D) CAPTCHA مش بيتحل
    E) Error 4xx/5xx بعد submit

[2] Refresh فشل
    A) Cookies expired (401/403)
    B) Session مش بتتجدد
    C) Token refresh rejected

[3] Chat فشل
    A) مفيش رد (SSE timeout)
    B) رد مبتور / incomplete
    C) Rate limit (429)
    D) Account banned / suspended

[4] Monitor فشل
    A) Provider مش بيظهر في monitor
    B) Health check بيرجع false positive
    C) Balance مش بيتجاب صح
```

## الخطوة 2 — Quick Diagnosis

```bash
# 1. شوف الـ accounts file — في حسابات active؟
python -c "import json; d=json.load(open('accounts_{provider}.json')); print(f'Total: {len(d)}, Active: {sum(1 for a in d if a.get(\"status\")==\"active\")}')"

# 2. شوف آخر error في الـ log
type {provider}_*.log | findstr /i "error fail timeout"

# 3. اختبر الموقع يدوياً
python -c "from curl_cffi import requests; r=requests.get('https://{provider}.com', impersonate='chrome'); print(r.status_code)"

# 4. شوف selectors لسه شغالين
python debug_{provider}.py
```

## الخطوة 3 — الإصلاح حسب النوع

### Cloudflare / Anti-bot:
```python
# جرب curl_cffi بدل requests
from curl_cffi import requests as cffi_requests
r = cffi_requests.get(url, impersonate="chrome120")

# لو مش نافع → SeleniumBase uc=True
with SB(uc=True) as sb:
    sb.uc_open(url)
```

### Selector اتغير:
```python
# 1. افتح الموقع في browser → F12 → شوف الـ element
# 2. حدث الـ SELECTORS في أعلى الملف
# 3. لو CSS hashed → استخدم XPath أو text-based
#    مثال: "//button[contains(text(),'Sign')]"
```

### OTP مش بيوصل:
```bash
# جرب email provider تاني
python {provider}_register.py --provider tempnet
python {provider}_register.py --provider emailnator
python {provider}_register.py --provider mailtm
```

### 401/403 Session expired:
```bash
# شغل refresh
python refresh.py
# لو refresh كمان فشل → سجل حساب جديد
python {provider}_register.py --no-loop
```

## الخطوة 4 — بعد الإصلاح

```bash
# اختبر
python {provider}_register.py --no-loop --provider mailtm

# لو نجح → حدث السجل
# git add -A && git commit -m "fix: [Provider] [وصف الإصلاح]"
```
