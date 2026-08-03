---
description: بروتوكول تحليل HAR و curl_cffi وتسلسل الـ Requests لأي مشروع AI Provider
globs: "**/*.py,**/*.har,**/*.json"
---
# 🌐 مهارة تحليل الـ HAR وتسلسل الـ Requests

> **المرجع الكامل:** `UNIVERSAL_PROVIDER_PROMPT.md` — اقرأه كاملاً قبل بناء أي Provider جديد.
> يحتوي على 67+ قاعدة حية + أمثلة كود + anti-patterns.

## 🎯 القاعدة الذهبية (لا تكسرها أبداً)
```
Requests أولاً → Hybrid لو في Cloudflare → Selenium آخر حل فقط
```

---

## 📋 بروتوكول الـ HAR — خطوتين إلزاميتين

### الخطوة 1️⃣ — التحليل (ممنوع الكود هنا!)
أرسل هذا البرومبت للـ AI لما يكون عندك HAR أو curl:

```
معيا ملف HAR/curl لعملية [اسم العملية].
🫷 المهمة الأولى: ممنوع كتابة أي سطر كود بايثون الآن.
أريدك أن تحلل الملف وتستخرج "خريطة التسلسل التنفيذي (Dependency Flow)":
- كل خطوة request وما الذي تخرجه للخطوة التالية
- أي cookies أو headers أو tokens من الخطوة 1 تحتاجها الخطوة 2
- أي قيم ديناميكية يجب استخراجها من كل response
اعرضها في شكل:
  Step 1 → [الـ Endpoint] → output: [token/cookie/header]
    ↓
  Step 2 → [الـ Endpoint] → يحتاج: [المدخل] → output: [...]
```

### الخطوة 2️⃣ — التنفيذ (بعد مراجعة الخريطة فقط)
بعد موافقتك على الخريطة، أرسل:

```
الخريطة صحيحة. الآن اكتب سكريبت Python بـ curl_cffi يطبق هذه الخريطة:
- استخدم Session واحد يحافظ على الكوكيز
- استخرج كل token ديناميكياً من كل response
- try/except لكل request مع logging واضح
- مفيش hardcoded values — كل شيء من response السابق
```

---

## ⚡ Checklist — أول ما تبدأ Provider جديد

قبل كتابة سطر كود واحد، أجب على هذه الأسئلة:

- [ ] ما هي طريقة الـ auth? (Descope? Firebase? OAuth? JWT? Magic Link?)
- [ ] أين يعيش الـ token? (body? cookies? localStorage? headers?)
- [ ] هل يوجد Cloudflare أو hCaptcha؟ (Hybrid مطلوب)
- [ ] ما هي طريقة التحقق؟ (OTP 6 أرقام؟ Magic Link؟ Email Link؟)
- [ ] ما هو الـ temp email المناسب؟ (Emailnator؟ Mail.tm؟ TempMail؟)
- [ ] هل response format هو JSON أم RSC (Next.js) أم HTML؟

---

## 🔗 Dynamic Token Chaining (النمط الأساسي)

```python
# كل response ممكن يحمل token للـ request التالي
resp1 = session.post("/step1", json={...})
token = resp1.json()["session_token"]          # ← دايماً ديناميك

resp2 = session.post("/step2",
    headers={"Authorization": f"Bearer {token}"},
    json={...}
)
cookie_needed = resp2.cookies.get("csrf_token")  # ← من الكوكيز

resp3 = session.post("/step3",
    headers={"x-csrf-token": cookie_needed},
    json={...}
)
```

---

## 🚫 Anti-Patterns الأكثر شيوعاً

| الخطأ | لماذا خطر | الصح |
|-------|----------|------|
| `time.sleep(3)` fixed | Fragile, بيتكسر | `sb.wait_for_element_visible(s, timeout=15)` |
| Token hardcoded | بيختلف كل session | استخرجه من الـ response |
| `except Exception: pass` | بيخبي Errors | `except Exception as e: log.error(e)` |
| Selenium من الأول | بطيء جداً | جرب requests أولاً |
| Multiple browser sessions | ذاكرة وبطء | Session واحد + WAF_REUSE_LIMIT |
