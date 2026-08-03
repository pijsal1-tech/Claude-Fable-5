---
description: خريطة مهارات الـ Provider - من فين تبدأ لكل مهمة
globs: "**/*.py"
---
# 🗺️ دليل Skills الـ Provider — ابدأ من هنا

## فلو العمل على أي Provider جديد:

```
1. ابدأ بـ  03-provider-checklist.md   ← أجب على الأسئلة الـ 7
        ↓
2. بناءً على الإجابة:
   - مفيش Cloudflare → 04-provider-requests.md
   - في Cloudflare   → 05-provider-hybrid.md
        ↓
3. راجع              06-live-rules.md       ← تطبق تلقائياً
        ↓
4. بعد التسجيل:      07-refresh-pattern.md  ← اكتب refresh.py
```

## فين كل ملف؟

| الملف | متى تستخدمه |
|-------|-------------|
| `03-provider-checklist.md` | **أول خطوة دايماً** — تحليل الـ Provider |
| `04-provider-requests.md` | Provider بدون حماية — Requests فقط |
| `05-provider-hybrid.md` | Provider فيه Cloudflare — Browser + Requests |
| `06-live-rules.md` | المرجع السريع — 67+ قاعدة مضغوطة |
| `07-refresh-pattern.md` | كتابة refresh.py — 3-Layer Pattern |
| `02-har-analysis.md` | تحليل HAR — خريطة الـ requests |

## الـ Reference الكامل:
> `UNIVERSAL_PROVIDER_PROMPT.md` — فيه كل التفاصيل والأمثلة الكاملة
