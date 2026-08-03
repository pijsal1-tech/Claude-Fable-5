# 🧠 Project Vision — AI_PROVIDERS / C__cursor

## ما هو المشروع
نظام **automation كامل** لتسجيل وإدارة حسابات AI:
- يسجّل حسابات تلقائياً في 14+ موقع AI
- يحفظ الـ sessions وCookies في `accounts.json`
- يجدد الـ sessions تلقائياً عبر `monitor.py`

## الدورة الكاملة
```
register script
    ↓ تسجيل + OTP
accounts.json (.AAA_GGG_iii_VIBE_CODING/<provider>/)
    ↓ كل X ساعة
monitor.py → refresh(email) → accounts.json updated
    ↓
chat.py → يستخدم الحساب النشط
```

## الـ Providers (14 الحالية)
| Provider | حسابات | Chat Script | Refresh |
|---------|---------|-------------|---------|
| arena | 22 | ✅ | ✅ |
| deepseek | 128 | ✅ | ✅ |
| groq | 20 | ❌ | ✅ |
| mistral | 7 | ❌ | ✅ |
| cohere | 15 | ❌ | ✅ |
| ai21 | 39 | ✅ | ✅ |
| ernie | 14 | ✅ | ✅ |
| uncensored | 41 | ✅ | ✅ |
| genspark | 234 | ✅ | ✅ |
| perplexity | 229 | ✅ | ✅ |
| runable | 5,057 | ✅ | ✅ |
| you_com | 7,992 | ❌ | ✅ |
| zo_ai | 14 | ❌ | ✅ |
| promptcowboy | 50 | ❌ | ✅ |

## البنية الأساسية
```
.AAA_GGG_iii_VIBE_CODING/
├── <provider>/
│   ├── accounts_<name>.json   ← الحسابات
│   ├── <provider>_register.py ← التسجيل
│   ├── <provider>_chat.py     ← الدردشة
│   └── refresh.py             ← التجديد (MUST: def refresh(email) -> bool)
monitor.py                     ← يجدد كل providers تلقائياً
```

## معايير النجاح
- ✅ register script يشتغل بدون تدخل بشري
- ✅ refresh يشتغل تلقائياً كل X ساعة
- ✅ monitor.py يقرأ كل الـ providers بدون error
- ✅ أي provider جديد يتضاف في < ساعة

## Non-Goals
- مش عايزين واجهة ويب
- مش عايزين database — JSON كافي
- مش عايزين تعقيد زيادة
