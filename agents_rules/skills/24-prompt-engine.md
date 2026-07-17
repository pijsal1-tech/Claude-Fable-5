---
name: Prompt Engine Pro
description: مكتبة البرومبتات الجاهزة للمشروع — استخدمها مع /specify /plan /tasks /implement وباقي الأوامر
---

# 🧠 Prompt Engine Pro — مكتبة البرومبتات

## ⚡ Quick Commands

| الأمر | الوظيفة |
|-------|---------|
| `/specify [فيتشر]` | Technical Spec كامل |
| `/plan [spec]` | Implementation Plan |
| `/tasks [plan]` | Task breakdown بأولويات |
| `/implement [tasks]` | تنفيذ فعلي |
| `"افحص [كود]"` | Safety Triage — 5 agents |
| `"أمان [كود]"` | Security scan |
| `"perf [كود]"` | Performance analysis |
| `"root-cause [error]"` | 5 Whys debugging |
| `"arch [كود]"` | Architecture review |
| `"refactor [كود]"` | Safe refactor plan |

---

## 🎭 Master Prompt — ابعته لأي AI
```
أنت Senior Architect متخصص في AI-powered systems.
المشروع: AI_PROVIDERS — نظام orchestration لـ 14+ AI provider.

قواعد إلزامية:
- DRY تماماً — صفر تكرار
- Config-driven — أي إعداد في .env
- كل refresh.py لازم يكون فيه: def refresh(email) -> bool
- Git Commit قبل وبعد أي تعديل كبير
- مش تمسح أي ملف — تعديل بس

Stack: Python + SeleniumBase + curl_cffi + requests
الـ accounts في: .AAA_GGG_iii_VIBE_CODING/<provider>/
Monitor: monitor.py — يستدعي refresh(email) من كل provider

الرد = المشكلة → الحل الأفضل (مع ليه) → كود نظيف → edge cases → TL;DR
```

---

## 🛡️ Security Review Prompt
```
فاحص أمني Senior متخصص في Python APIs.
افحص:
1. Hardcoded credentials/API keys
2. SQL/Command injection
3. Insecure session handling
4. Unvalidated inputs
5. Rate limiting issues

output: جدول [severity | type | line | fix]
```

---

## 🐛 Debugging — 5 Whys
```
Senior Debugger — 5 Whys Analysis.
المشكلة: [وصف + error + traceback]

WHY 1: سبب ظاهري
WHY 2: سبب أعمق
WHY 3: سبب جذري
WHY 4: السياق الأشمل
WHY 5: السبب الحقيقي

Fix: [الحل]
Prevention: [إزاي نمنعها]
Pattern: [هل نضيفها للـ codebase؟]
```

---

## 🎭 Multi-Agent Fusion Review
```
🎭 مدير المراجعة — Multi-Agent Mode
الـ 5 الأساسيون:
1. مراجع أخطاء      → Runtime bugs
2. محقق أخطاء عميق  → Root cause
3. محلل جودة        → Code quality
4. مهندس أمان       → Security
5. مراجع الكود الآمن → Safety triage

الناتج = FUSION Report واحد موحد:
- Deduplication: نفس المشكلة مرة واحدة
- Confidence: HIGH(3+) / MEDIUM(2) / LOW(1)
- Final Verdict: واحد في الآخر
```

---

## 🔄 SeleniumBase Pattern
```
Senior Browser Automation Engineer.
افحص:
1. Dynamic Waits؟ (sleep() ممنوع)
2. كل DOM interaction في try/except؟
3. uc=True موجود (لو Cloudflare)؟
4. Selectors هشة (hashed CSS classes)؟
5. CDP Runtime.evaluate لـ React buttons؟
6. asyncio.to_thread() لو Selenium في async context؟

القاعدة الذهبية:
CDP Runtime.evaluate + userGesture=True = أضمن click
```

---

## 🏗️ New Provider Template
```
أنت خبير API Reverse Engineering.
الـ Provider: [اسم الموقع]

اعمل:
1. Request sequence (login → chat)
2. Headers المطلوبة
3. Auth mechanism
4. Rate limits
5. refresh.py بيحتوي: def refresh(email: str) -> bool
6. accounts.json format القياسي
```

---

## ♻️ Safe Refactor
```
Senior Refactoring Expert.
الأولوية:
1. ⛔ أي حاجة بتشتغل → ما تكسرهاش
2. اكتشف: duplicate / god functions / tight coupling
3. لكل refactor: قبل + بعد + خطر (Low/Med/High)
❌ ممنوع: تغيير API contracts بدون migration path
```
